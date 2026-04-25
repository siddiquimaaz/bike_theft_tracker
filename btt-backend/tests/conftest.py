"""
tests/conftest.py
Shared pytest fixtures — user factories, authenticated API clients, sample bikes.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


# ══════════════════════════════════════════════════════════════════════════════
# PostgreSQL session-leak prevention
# ══════════════════════════════════════════════════════════════════════════════
#
# Symptom:
#   OperationalError: database "test_bikethefttracker" is being accessed by
#   other users  DETAIL: There are N other sessions using the database.
#
# Root cause:
#   Views dispatch notifications via threading.Thread(daemon=True).  Each daemon
#   thread opens its own psycopg connection through Django's thread-local
#   `django.db.connection`.  Daemon threads are never explicitly joined, so
#   those connections outlive the test.  When pytest-django tries to run
#   destroy_test_db() → DROP DATABASE at session end, PostgreSQL refuses because
#   those sessions are still present in pg_stat_activity.
#
# Fix layer 1 — CONN_MAX_AGE=0  (module-level, runs before any connection)
# ─────────────────────────────────────────────────────────────────────────────
# Django maintains a per-thread connection pool.  With CONN_MAX_AGE != 0
# (the default can be None = unlimited), connections are reused across
# "requests" and never voluntarily closed by Django.  Setting it to 0 tells
# Django to close the connection at the end of every request/response cycle.
# Applied here at module-load time so it is in effect before the very first
# CREATE DATABASE call.
from django.conf import settings as _django_settings

for _db_alias in list(_django_settings.DATABASES):
    _django_settings.DATABASES[_db_alias]["CONN_MAX_AGE"] = 0

del _db_alias, _django_settings


# ─── Fix layer 2 — Synchronous thread executor  (function-scoped, autouse) ───
#
# WHY THIS IS THE ROOT-CAUSE FIX
# Each threading.Thread opens a brand-new thread-local psycopg session.
# Making threads synchronous means the "thread" target runs in the *same*
# OS thread as the test, therefore it reuses the test thread's existing
# django.db.connection — the one pytest-django has already wrapped in a
# SAVEPOINT.  No new psycopg session is created, nothing leaks.
#
# SECONDARY BENEFIT
# Notification assertions become deterministic: no time.sleep() needed
# because the target has completed before start() returns.
#
# SAFETY
# monkeypatch is function-scoped, so threading.Thread is restored automatically
# after every single test — no manual cleanup required, no cross-test pollution.

@pytest.fixture(autouse=True)
def _sync_background_threads(monkeypatch):
    """Replace threading.Thread with a synchronous in-process executor."""
    import threading

    class _SyncThread:
        """
        Drop-in replacement for threading.Thread.

        start() runs the target callable immediately in the calling thread
        instead of spawning a new OS thread.  join() is a no-op because
        execution has already completed.
        """

        def __init__(
            self,
            target=None,
            args=(),
            kwargs=None,
            *,
            daemon=None,
            group=None,
            name=None,
        ):
            self._target = target
            self._args = args
            self._kwargs = kwargs or {}

        def start(self):
            if self._target:
                self._target(*self._args, **self._kwargs)

        def join(self, timeout=None):
            pass  # Already ran synchronously in start().

        # Provide daemon attribute so code that reads/sets it doesn't break.
        @property
        def daemon(self):
            return False

        @daemon.setter
        def daemon(self, value):
            pass  # No-op — there is no real thread to configure.

    monkeypatch.setattr(threading, "Thread", _SyncThread)


# ─── Fix layer 3 — Session-end connection flush  (session-scoped, autouse) ───
#
# Belt-and-suspenders: close every Django connection wrapper immediately before
# pytest-django calls destroy_test_db().
#
# WHY THE ORDERING IS GUARANTEED
# This fixture explicitly depends on `django_db_setup` (pytest-django's
# session-scoped fixture that owns create_test_db / destroy_test_db).
# pytest finalises fixtures in *reverse dependency order*:
#
#   setup order:   django_db_setup  →  _close_db_connections_before_drop
#   teardown order: _close_db_connections_before_drop  →  django_db_setup
#
# Our `yield` continuation (connections.close_all) therefore always runs
# BEFORE django_db_setup tears down and issues DROP DATABASE.
#
# This catches anything that slipped past layer 2 — management commands,
# third-party signal handlers, or any direct use of django.db.connection
# outside of a threading.Thread call.

@pytest.fixture(scope="session", autouse=True)
def _close_db_connections_before_drop(django_db_setup):
    """Close all Django DB wrappers before destroy_test_db() is called."""
    yield
    from django.db import connections

    for conn in connections.all():
        conn.close()


# ─── User Fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def api_client():
    return APIClient()


def _make_user(role, email, extra=None):
    data = dict(
        full_name=f"Test {role.title()}",
        email=email,
        role=role,
        is_verified=True,
        is_active=True,
    )
    if extra:
        data.update(extra)
    user = User.objects.create_user(password="Test@12345", **data)
    return user


@pytest.fixture
def owner_user(db):
    return _make_user("owner", "owner@test.btt", {"cnic": "4200011111110"})


@pytest.fixture
def owner_user_2(db):
    return _make_user("owner", "owner2@test.btt", {"cnic": "4200011111112"})


@pytest.fixture
def authority_user(db):
    return _make_user(
        "authority", "authority@test.btt",
        {"badge_number": "TEST-001", "city": "Karachi", "cnic": "4200011111113"},
    )


@pytest.fixture
def authority_user_lahore(db):
    return _make_user(
        "authority", "authority.lahore@test.btt",
        {"badge_number": "TEST-002", "city": "Lahore", "cnic": "4200011111114"},
    )


@pytest.fixture
def community_user(db):
    return _make_user("community", "community@test.btt")


@pytest.fixture
def admin_user(db):
    return _make_user("admin", "admin@test.btt")


# ─── Authenticated Clients ────────────────────────────────────────────────────

def _auth_client(user):
    from rest_framework_simplejwt.tokens import RefreshToken
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client


@pytest.fixture
def owner_client(owner_user):
    return _auth_client(owner_user)


@pytest.fixture
def authority_client(authority_user):
    return _auth_client(authority_user)


@pytest.fixture
def authority_client_lahore(authority_user_lahore):
    return _auth_client(authority_user_lahore)


@pytest.fixture
def community_client(community_user):
    return _auth_client(community_user)


@pytest.fixture
def admin_client(admin_user):
    return _auth_client(admin_user)


# ─── Bike + Report Fixtures ───────────────────────────────────────────────────

@pytest.fixture
def sample_bike(db, owner_user):
    from apps.bikes.models import Bike
    return Bike.objects.create(
        owner=owner_user,
        make="Honda",
        model="CG 125",
        year=2022,
        color="Black",
        engine_number="HND22A1234567",
        chassis_number="MRHGC1250NY123456",
        registration_city="Karachi",
    )


@pytest.fixture
def sample_report(db, sample_bike, owner_user):
    from apps.reports.models import TheftReport
    from datetime import date
    return TheftReport.objects.create(
        bike=sample_bike,
        reported_by=owner_user,
        theft_date=date.today(),
        theft_city="Karachi",
        status="new_case",
    )


@pytest.fixture
def recovered_report(db, sample_report, authority_user):
    from apps.reports.models import RecoveryRecord
    from datetime import date
    recovery = RecoveryRecord.objects.create(
        theft_report=sample_report,
        logged_by=authority_user,
        recovery_date=date.today(),
        recovery_city="Karachi",
        bike_condition="good",
    )
    sample_report.status = "recovered"
    sample_report.save(update_fields=["status"])
    return sample_report
