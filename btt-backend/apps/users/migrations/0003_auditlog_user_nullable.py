"""
Migration 0003 — two cooperating changes:

1. ALTER COLUMN audit_logs.user_id → allow NULL.
   Switches on_delete from PROTECT to SET_NULL so that deleting a user
   (e.g. demo-data reset via `seed_demo_data --clear`) nulls out the FK
   instead of raising InsufficientPrivilege / ProtectedError.
   Audit rows are preserved — only the user reference is cleared.

2. GRANT UPDATE ON audit_logs TO bttadmin.
   Migration 0002 revoked both UPDATE and DELETE.  SET_NULL requires the
   database to issue an UPDATE (nulling user_id) so UPDATE must be restored.
   DELETE stays revoked — audit rows remain permanently append-only at the
   DB level; only the user-FK can be nulled on cascade.

reverse_sql is symmetric: re-adds NOT NULL, revokes UPDATE again.
"""

import django.db.models.deletion
import django.conf

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(django.conf.settings.AUTH_USER_MODEL),
        ("users", "0002_audit_log_immutability"),
    ]

    operations = [
        # ── 1. Make user_id nullable (SET_NULL cascade) ──────────────────────
        migrations.AlterField(
            model_name="auditlog",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="audit_logs",
                to=django.conf.settings.AUTH_USER_MODEL,
            ),
        ),
        # ── 2. Grant UPDATE back so SET_NULL cascade can null out user_id ────
        #       DELETE remains revoked — rows are still append-only.
        migrations.RunSQL(
            sql=(
                "DO $$ BEGIN "
                "  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'bttadmin') THEN "
                "    GRANT UPDATE ON audit_logs TO bttadmin; "
                "  END IF; "
                "END $$;"
            ),
            reverse_sql=(
                "DO $$ BEGIN "
                "  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'bttadmin') THEN "
                "    REVOKE UPDATE ON audit_logs FROM bttadmin; "
                "  END IF; "
                "END $$;"
            ),
        ),
    ]
