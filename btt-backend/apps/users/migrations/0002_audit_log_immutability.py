# Enforces append-only immutability at DB level for forensic integrity.
# Documented in Section 14 as a hardening step - now applied (Section 13).
#
# The audit_logs table is INSERT-only at the application layer (no UPDATE
# or DELETE call sites in `apps/`). This migration removes the privileges
# that would otherwise let a compromised credential or a hand-crafted SQL
# session tamper with the trail. The reverse SQL restores them so a
# rollback never leaves the role in a partially-revoked state.
#
# NOTE: the GRANT/REVOKE target uses the role from settings.DATABASES.
# In local dev that role is `bttadmin`; in CI the test runner connects
# as the database superuser which is exempt from REVOKE, so the test
# suite is unaffected.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "DO $$ BEGIN "
                "  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'bttadmin') THEN "
                "    REVOKE UPDATE, DELETE ON audit_logs FROM bttadmin; "
                "  END IF; "
                "END $$;"
            ),
            reverse_sql=(
                "DO $$ BEGIN "
                "  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'bttadmin') THEN "
                "    GRANT UPDATE, DELETE ON audit_logs TO bttadmin; "
                "  END IF; "
                "END $$;"
            ),
        ),
    ]
