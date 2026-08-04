"""
apps/ml/fuzzy_match.py
Fuzzy engine/chassis number matching using rapidfuzz WRatio scorer.

Designed for recovering bikes whose numbers may be:
  - Scratched or partially obscured
  - Modified by criminals (digit substitutions)
  - Entered with typos by the reporting officer

Score thresholds (calibrated on alphanumeric codes):
  > 85  → HIGH confidence — likely the same bike
  70–85 → MEDIUM confidence — possible match, verify manually
  < 70  → LOW confidence — unlikely match

Usage:
    from apps.ml.fuzzy_match import find_fuzzy_matches
    results = find_fuzzy_matches("PK-CG-98X32", field="engine_number", limit=5)
"""
import logging
from typing import Literal

logger = logging.getLogger(__name__)


def _confidence_label(score: float) -> str:
    from django.conf import settings
    high = getattr(settings, "ML_FUZZY_HIGH_THRESHOLD", 85)
    medium = getattr(settings, "ML_FUZZY_MEDIUM_THRESHOLD", 70)
    if score >= high:
        return "HIGH"
    if score >= medium:
        return "MEDIUM"
    return "LOW"


def find_fuzzy_matches(
    query_number: str,
    field: Literal["engine_number", "chassis_number"] = "engine_number",
    limit: int = 5,
) -> list[dict]:
    """
    Run WRatio fuzzy matching against all currently stolen/under-investigation bikes.

    Args:
        query_number: Recovered engine or chassis number (may be damaged/partial)
        field: Which identifier to match against — 'engine_number' or 'chassis_number'
        limit: Max number of results to return

    Returns:
        List of dicts sorted by score descending:
        [
          {
            'bike_id': '42',
            'matched_number': 'PK-CG-98X32',
            'score': 91.3,
            'confidence': 'HIGH',
            'bike_details': { make, model, year, color, owner_contact }
          },
          ...
        ]
    """
    if field not in ("engine_number", "chassis_number"):
        raise ValueError(f"Invalid field: {field}. Must be 'engine_number' or 'chassis_number'")

    try:
        from rapidfuzz import process, fuzz
    except ImportError:
        logger.error("rapidfuzz not installed. Run: pip install rapidfuzz")
        return []

    from apps.reports.models import TheftReport

    # Fetch every bike with an ACTIVE theft report — i.e. any status except
    # recovered/closed.  Shared with Bike.is_stolen via TheftReport.ACTIVE_STATUSES;
    # were the two to drift, sightings would silently fail to match against
    # cases that have already progressed beyond NEW_CASE.
    stolen_reports = (
        TheftReport.objects.filter(
            status__in=TheftReport.ACTIVE_STATUSES,
            deleted_at__isnull=True,
        )
        .select_related("bike", "bike__owner")
    )

    if not stolen_reports.exists():
        logger.info("Fuzzy match: no stolen bikes in database")
        return []

    # Build {bike_id_str: identifier_value} dict for rapidfuzz
    candidates: dict[str, str] = {}
    bike_report_map: dict[str, TheftReport] = {}

    for report in stolen_reports:
        bike = report.bike
        identifier = getattr(bike, field, None)
        if identifier:
            key = str(bike.id)
            candidates[key] = identifier.upper()
            bike_report_map[key] = report

    if not candidates:
        return []

    normalized_query = query_number.upper().strip()

    # WRatio handles substitutions, deletions, transpositions — best for alphanumeric codes
    raw_results = process.extract(
        normalized_query,
        candidates,
        scorer=fuzz.WRatio,
        limit=limit,
    )

    results = []
    for matched_value, score, bike_id_key in raw_results:
        report = bike_report_map.get(bike_id_key)
        if not report:
            continue
        bike = report.bike
        owner = bike.owner

        results.append({
            "bike_id": bike_id_key,
            "matched_number": matched_value,
            "score": round(score, 2),
            "confidence": _confidence_label(score),
            "bike_details": {
                "make": bike.make,
                "model": bike.model,
                "year": bike.year,
                "color": bike.color,
                "engine_number": bike.engine_number,
                "chassis_number": bike.chassis_number,
                "registration_number": bike.registration_number,
                "photo_url": bike.photo_url,
                "theft_report_id": report.id,
                "theft_reference": report.reference_number,
                "theft_city": report.theft_city,
                "theft_date": str(report.theft_date),
            },
            "owner_contact": {
                "name": owner.full_name,
                "phone": owner.phone,
                "city": owner.city,
            },
        })

    logger.info(
        "Fuzzy match on %s='%s': %d candidates, top score=%.1f",
        field, normalized_query, len(candidates),
        results[0]["score"] if results else 0,
    )
    return results
