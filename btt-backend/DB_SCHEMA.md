# Bike Theft Tracker DB Schema

This schema reflects the current Django models and migrations after:
- `reports.0003_theftreport_authority_last_action_at_and_more`
- `sightings.0003_sightingreport_auto_escalated_and_more`
- `notifications.0004_notification_metadata_notification_sighting_and_more`
- `users.0002_audit_log_immutability` — REVOKEs `UPDATE, DELETE` on `audit_logs`
  from the `bttadmin` role for forensic integrity (see `audit_logs` notes below)

For full reset/run instructions (services, DB flush, migrations, restart), see `..\RESET_RUNBOOK.md`.

## Core Tables

### `users`
- `id` (PK)
- `full_name`
- `cnic` (unique, nullable)
- `email` (unique)
- `phone` (nullable)
- `role` (`owner|authority|community|admin`)
- `is_verified`, `is_active`, `is_staff`, `is_superuser`
- `badge_number` (unique, nullable)
- `city` (nullable)
- `email_verification_token`, `email_verification_token_expires`
- `password_reset_token`, `password_reset_token_expires`
- `created_at`, `deleted_at`

### `bikes`
- `id` (PK)
- `owner_id` (FK -> `users.id`)
- `make`, `model`, `year`, `color`
- `registration_number`, `registration_city`
- `engine_number` (unique)
- `chassis_number` (unique)
- `photo_url`
- `created_at`, `deleted_at`

### `theft_reports`
- `id` (PK)
- `bike_id` (FK -> `bikes.id`)
- `reported_by_id` (FK -> `users.id`)
- `theft_date`, `theft_city`
- `theft_location` (PostGIS point, nullable)
- `theft_location_detail`, `fir_number`, `description`
- `status`
  - legacy: `stolen`, `under_investigation`
  - enhanced: `new_case`, `under_review`, `active_investigation`, `bike_located`, `pending_verification`, `recovered`, `closed`
- `owner_recovery_confirmed`
- `owner_recovery_confirmed_at`
- `owner_recovery_confirmed_by_id` (FK -> `users.id`, nullable)
- `authority_last_action_at`
- `stale_escalated_at` (nullable)
- `created_at`, `updated_at`, `deleted_at`

### `recovery_records`
- `id` (PK)
- `theft_report_id` (OneToOne FK -> `theft_reports.id`)
- `logged_by_id` (FK -> `users.id`)
- `fuzzy_match_score`
- `recovery_date`, `recovery_city`
- `recovery_location` (PostGIS point, nullable)
- `recovery_location_detail`
- `bike_condition` (`good|damaged|stripped|burnt`)
- `notes`
- `evidence_photos` (JSON array)
- `created_at`

### `sighting_reports`
- `id` (PK)
- `bike_id` (FK -> `bikes.id`, nullable, set on authority verification)
- `top_match_bike_id` (FK -> `bikes.id`, nullable)
- `raw_engine_number`, `raw_chassis_number`
- `fuzzy_match_score`
- `sighter_id` (FK -> `users.id`, nullable)
- `sighting_date`, `sighting_city`
- `sighting_location` (PostGIS point, nullable)
- `sighting_description`, `photo_url`
- `is_verified`
- `verified_by_id` (FK -> `users.id`, nullable)
- handshake/escalation fields:
  - `is_archived`
  - `owner_confirmation_status` (`pending|yes|no|not_sure`)
  - `owner_notified_at`
  - `owner_response_deadline`
  - `auto_escalated`
- `created_at`

### `notifications`
- `id` (PK)
- `user_id` (FK -> `users.id`)
- `report_id` (FK -> `theft_reports.id`, nullable)
- `sighting_id` (FK -> `sighting_reports.id`, nullable)
- `type`
  - `theft_reported`, `status_update`, `recovery`, `sighting_matched`
  - `sighting_owner_handshake`, `sighting_owner_response`
  - `community_closure`, `system`, `urgent`
- `message`
- `is_read`
- `delivery_channel` (`in_app|email|sms`)
- `metadata` (JSON)
- `created_at`

### `case_timeline`
- `id` (PK)
- `theft_report_id` (FK -> `theft_reports.id`)
- `actor_id` (FK -> `users.id`, nullable)
- `action`
- `metadata` (JSON)
- `created_at`

### `audit_logs`
- `id` (PK)
- `user_id` (FK -> `users.id`)
- `action`
- `table_affected`, `record_id`
- `old_value` (JSON), `new_value` (JSON)
- `ip_address`
- `created_at`
- **Append-only at the DB level**: migration `users.0002_audit_log_immutability`
  REVOKEs `UPDATE` and `DELETE` privileges on this table from the `bttadmin`
  role (the role used by the running app). The application layer already has
  no UPDATE/DELETE call sites — the migration removes the privilege so a
  compromised credential or hand-crafted SQL session cannot tamper with the
  trail. The `reverse_sql` GRANTs the privileges back, both wrapped in a
  `pg_roles` existence check so CI (which connects as a superuser, exempt
  from REVOKE) is unaffected.

## Main Relationships

- `users (1) -> (many) bikes`
- `bikes (1) -> (many) theft_reports`
- `theft_reports (1) -> (0..1) recovery_records`
- `theft_reports (1) -> (many) case_timeline`
- `bikes (1) -> (many) sighting_reports` (verified or top-match linkage)
- `users (1) -> (many) notifications`
- `theft_reports (1) -> (many) notifications`
- `sighting_reports (1) -> (many) notifications`

## Fresh-Start Commands

From `btt-backend`:

```powershell
& "D:\scripts\bike_theft_tracker\venv\Scripts\python.exe" manage.py reset_db --noinput --force
& "D:\scripts\bike_theft_tracker\venv\Scripts\python.exe" manage.py migrate
& "D:\scripts\bike_theft_tracker\venv\Scripts\python.exe" manage.py check
```
