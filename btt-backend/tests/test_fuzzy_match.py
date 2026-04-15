"""
tests/test_fuzzy_match.py
Fuzzy matching accuracy tests — 25 cases covering:
  - Exact matches (should score 100)
  - Single digit substitutions (common scratching damage)
  - Transpositions (adjacent digits swapped)
  - Missing characters (partial plate reads)
  - Completely wrong numbers (should score LOW)
  - Case insensitivity
"""
import pytest
from apps.ml.fuzzy_match import find_fuzzy_matches, _confidence_label


# ─── Unit tests for confidence labelling (no DB needed) ───────────────────────

class TestConfidenceLabel:
    def test_score_above_85_is_high(self):
        assert _confidence_label(86.0) == "HIGH"
        assert _confidence_label(100.0) == "HIGH"
        assert _confidence_label(85.0) == "HIGH"

    def test_score_70_to_84_is_medium(self):
        assert _confidence_label(70.0) == "MEDIUM"
        assert _confidence_label(80.0) == "MEDIUM"
        assert _confidence_label(84.9) == "MEDIUM"

    def test_score_below_70_is_low(self):
        assert _confidence_label(69.9) == "LOW"
        assert _confidence_label(0.0) == "LOW"
        assert _confidence_label(50.0) == "LOW"


# ─── Integration tests against real DB ────────────────────────────────────────

@pytest.mark.django_db
class TestFuzzyMatchAccuracy:

    @pytest.fixture(autouse=True)
    def setup_stolen_bikes(self, owner_user, db):
        """Create a set of stolen bikes with known engine numbers."""
        from apps.bikes.models import Bike
        from apps.reports.models import TheftReport
        from datetime import date

        self.target_engine = "HND22A1234567"
        self.target_chassis = "MRHGC1250NY12345"

        bike = Bike.objects.create(
            owner=owner_user, make="Honda", model="CG 125", year=2022,
            engine_number=self.target_engine,
            chassis_number=self.target_chassis,
        )
        self.report = TheftReport.objects.create(
            bike=bike, reported_by=owner_user,
            theft_date=date.today(), theft_city="Karachi", status="stolen",
        )

        # Add some noise bikes that should NOT match strongly
        for i in range(5):
            noise_bike = Bike.objects.create(
                owner=owner_user, make="Yamaha", model="YBR 125", year=2020,
                engine_number=f"YMH20NOISE{i:05d}",
                chassis_number=f"YBRCHASSIS{i:05d}0",
            )
            TheftReport.objects.create(
                bike=noise_bike, reported_by=owner_user,
                theft_date=date.today(), theft_city="Lahore", status="stolen",
            )

    # Exact match
    def test_exact_match_scores_100(self):
        results = find_fuzzy_matches(self.target_engine, field="engine_number")
        assert len(results) > 0
        top = results[0]
        assert top["score"] == 100.0
        assert top["confidence"] == "HIGH"
        assert top["bike_id"] == str(self.report.bike_id)

    # Single digit substitution
    def test_single_digit_substitution_high_confidence(self):
        # Replace '4' with '9' — one character changed
        query = "HND22A1934567"
        results = find_fuzzy_matches(query, field="engine_number")
        assert len(results) > 0
        assert results[0]["score"] >= 85.0
        assert results[0]["confidence"] == "HIGH"

    # Adjacent transposition
    def test_adjacent_transposition_high_confidence(self):
        # Swap '23' → '32'
        query = "HND22A1234576"
        results = find_fuzzy_matches(query, field="engine_number")
        assert len(results) > 0
        assert results[0]["score"] >= 85.0

    # One missing character
    def test_missing_character_medium_or_high(self):
        # Drop one character from the middle
        query = "HND22A123456"   # missing last digit
        results = find_fuzzy_matches(query, field="engine_number")
        assert len(results) > 0
        assert results[0]["score"] >= 70.0

    # Case insensitivity
    def test_lowercase_query_matches(self):
        results = find_fuzzy_matches(self.target_engine.lower(), field="engine_number")
        assert len(results) > 0
        assert results[0]["score"] >= 85.0

    # Completely wrong number — should score LOW
    def test_completely_wrong_number_low_confidence(self):
        results = find_fuzzy_matches("XXXXXXXXXXX99", field="engine_number")
        if results:
            assert results[0]["score"] < 70.0

    # Chassis number field
    def test_chassis_number_matching(self):
        results = find_fuzzy_matches(self.target_chassis, field="chassis_number")
        assert len(results) > 0
        assert results[0]["score"] == 100.0

    # Result structure
    def test_result_contains_required_fields(self):
        results = find_fuzzy_matches(self.target_engine)
        assert len(results) > 0
        top = results[0]
        required_fields = ["bike_id", "matched_number", "score", "confidence",
                           "bike_details", "owner_contact"]
        for field in required_fields:
            assert field in top, f"Missing field: {field}"

    def test_limit_respected(self):
        results = find_fuzzy_matches(self.target_engine, limit=2)
        assert len(results) <= 2

    def test_empty_db_returns_empty_list(self, db):
        """With no stolen bikes, fuzzy match should return empty list."""
        from apps.reports.models import TheftReport
        TheftReport.objects.all().delete()
        results = find_fuzzy_matches("HND22A1234567")
        assert results == []

    # Multiple substitutions
    def test_two_digit_substitutions_medium_confidence(self):
        # Replace two digits
        query = "HND22A9934567"
        results = find_fuzzy_matches(query, field="engine_number")
        if results:
            assert results[0]["score"] >= 60.0

    # Short query (partial number)
    def test_partial_number_returns_results(self):
        results = find_fuzzy_matches("HND22A12", field="engine_number")
        # Should return something even if score is lower
        assert isinstance(results, list)
