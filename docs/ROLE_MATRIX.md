# Role Matrix: Current vs Target

This document defines what each role should be able to do in the Bike Theft Tracker system and serves as the reference for backend RBAC and frontend route exposure.

Operational reset/start procedures are documented in `RESET_RUNBOOK.md`.

## Roles

- `admin`: governance, oversight, user management
- `authority`: operational investigation and verification
- `owner`: self-service for own bikes/cases
- `community`: public reporting and own submission tracking

## Capability matrix

| Capability | Admin | Authority | Owner | Community |
|---|---:|---:|---:|---:|
| Login/logout/password reset | Yes | Yes | Yes | Yes |
| Register account | No (created by system) | No (created by admin) | Yes | Yes |
| Manage users / authority creation | Yes | No | No | No |
| Access analytics / audit logs | Yes | No | No | No |
| Trigger ML reanalysis | Yes | No | No | No |
| View ML hotspots + corridors + radius | Yes | Yes (city-scoped) | No | No |
| Fuzzy engine/chassis search | No | Yes | No | No |
| View trend analytics | Yes | No | No | No |
| View recovery zones | Yes | No | No | No |
| Manage own bikes | No | No | Yes | No |
| Report Stolen button on bike card | No | No | Yes | No |
| File theft report | No | No | Yes (own bike only) | No |
| View theft reports list/detail | Yes (all) | Yes (city scoped) | Yes (own only) | No |
| Update theft status | Yes (optional policy override) | Yes | No | No |
| Log/amend recovery | No (policy: authority-owned workflow) | Yes | No | No |
| Submit sightings | Yes | Yes | Yes | Yes |
| View sightings queue | Yes (unverified) | Yes (unverified) | Own only | Own only |
| Verify sightings | Yes | Yes | No | No |
| Receive THEFT_REPORTED alert | — | ✅ same city only | ✅ own report | — |
| Receive community theft awareness alert | — | — | — | ✅ same city only, no PII |
| Notifications (in-app) | Yes | Yes | Yes | Yes |

## Policy notes

- Community users must not access full theft case data.
- Owner and community sighting detail access must be object-scoped to their own submissions.
- Authority receives in-app `THEFT_REPORTED` alerts for newly filed cases **in their city**.
- Community receives a `SYSTEM` notification when a bike is stolen in their city — no owner PII (email/phone/CNIC) is included.
- ML endpoints `recovery-radius` and `corridors` are city-scoped for authority users (pass `?city=` param).
- The "Report Stolen" button on the BikeCard is only shown for non-stolen bikes, opening a pre-filled ReportForm modal.
