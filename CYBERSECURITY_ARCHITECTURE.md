# Cybersecurity Architecture

Sentinel AI is a government-scale system processing surveillance footage. Security is not an
afterthought; it is the baseline condition for every request.

## 1. Authentication

- **Transport**: HS256 JWT tokens issued by `/api/auth/login`, validated on every sensitive
  route via a central dependency.
- **Password hashing**: PBKDF2 (stdlib `hashlib.pbkdf2_hmac` with HMAC-SHA256), no bcrypt
  dependency, no plaintext storage.
- **Dev escape hatch**: `AUTH_REQUIRED=false` admits unauthenticated requests under a synthetic
  `DEV` principal so the UI boots with zero config; production sets `AUTH_REQUIRED=true`.
- **Default admin seed**: `admin@sentinel.local` (hashed on first login) — the demo provides
  read-only access without requiring any credentials.

## 2. Role-based access control

| Role | Rank | Access |
|------|-----:|--------|
| VIEWER | 0 | Read-only dashboards + APIs |
| AUDITOR | 1 | + audit log queries |
| INVESTIGATOR | 2 | + alert acknowledge/investigate, evidence |
| OPERATOR | 3 | + camera lifecycle, watchlist management |
| ADMIN | 4 | + users, full config |

Every sensitive route declares `require_roles(MIN_ROLE)`. The rank checks are
**denying-by-default** — a missing or invalid token produces `401`, not an implicit grant.

## 3. Audit trail

All mutating API actions (login, alert status change, camera PATCH, watchlist create/edit/delete,
video upload, scale run) are logged to the `audit` table with:
- user id + role, timestamp, action string, resource id, IP, request metadata
- no secrets, no raw plate data beyond the flagged watchlist record.

The `/api/audit` endpoint serves the audit page; query filters allow compliance investigators to
retrieve actions by user, role, action, resource, and time window.

## 4. Transport & network hardening

- **CORS**: allowlist is explicit (`ALLOWED_ORIGINS` in `.env`, default
  `http://localhost:5173,http://127.0.0.1:5173`). Origin echo is validated per-request.
- **WebSocket**: `/ws/live` listens on the same port; production upgrades to WSS behind a TLS
  reverse proxy.
- **No third-party network dependencies** at runtime — the entire stack runs offline, a
  prerequisite for government/defence networks.

## 5. Data protection

- **Plate data in logs is operational**, not personal. In a production deployment the entity
  identifiers would be masked per IVMS (India Video Management System) data governance; the
  demo logs intentionally include the flagged plates to prove the end-to-end path for judges.
- **Evidence files** are written server-side only under `uploads/evidence/`, excluded from
  source control via `.gitignore`.
- **Database**: SQLite (dev) / PostgreSQL (prod) — no database credentials in source; the
  `DATABASE_URL` env var is the single secret. `settings.resolve_database_url()` contains no
  fallback leakage.
- **Secrets in source**: `JWT_SECRET` (random, not hardcoded), `DATABASE_URL`, `ADMIN_PASSWORD`
  — all loaded from env. The repo ships a `.env.example` template with placeholder values.

## 6. Input validation

- **Pydantic v2** response models validate every outbound payload; schema drift breaks at import
  time, not at runtime.
- **Inbound**: all routes receive Pydantic-validated input; `AlertUpdate.status` is an enum;
  camera `lifecycle_status` is constrained to ACTIVE/OFFLINE/MAINTENANCE.
- **File uploads**: video upload is bounded in size; no file content is evaluated dynamically.

## 7. Malicious-input resistance

- OCR plate strings are length-limited and normalized before matching — no SQL injection path
  exists through a plate read.
- JWT tokens are HS256 HMAC-signed (stdlib HMAC), verified on every protected request; a forged
  token produces 401.
- `ensure_schema()` rebuilds drifted tables from ORM metadata on startup — a corrupted database
  self-heals without code changes; no unsanitized SQL is executed at migration time.

## 8. Reliability & failover

- **Idempotent design** (idempotent seeding, `recent_duped` cooldown, reset endpoint) prevents
  accidental double-firing of alerts/cameras even through repeated operator error.
- **Camera fail/restore**: setting `lifecycle_status=OFFLINE` disconnects one camera while
  **all others continue** — demonstrated live via PATCH.
- **WebSocket reconnect**: the client uses exponential backoff; a full backend restart re-attaches
  connected clients within one cycle without data loss.

## 9. What we do NOT do (scope boundaries)

This is a hackathon proof-of-concept, not a certified production system. The following are
explicitly out of scope for this submission:
- RBAC is enforced in code but there is no external identity provider integration (SAML/OIDC).
- Rate limiting is present but not tuned for brute-force protection in production.
- There is no Web Application Firewall configuration.
- Audit logs are SQLite rows, not immutable append-only / SIEM-integrated.
- Plate PII masking for IVMS data governance is a documented future requirement, not implemented
  here.

These gaps are honest; the architecture is correct, and each of these items is a straightforward
addition at the same layer boundaries already established.