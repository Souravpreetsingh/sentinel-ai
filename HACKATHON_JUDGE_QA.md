# HACKATHON JUDGE Q&A

Concise, implementation-true answers. Every claim below reflects what is **actually built and
measured** in this repository or is explicitly marked as **architectural roadmap**. Nothing is
fabricated.

---

## 1. Why not replace all existing VMS systems?

Rip-and-replace is slow, expensive and politically painful. Every agency already owns cameras,
VMS and operators. This platform connects to that infrastructure (RTSP/ONVIF/region VMS) and
adds one intelligence layer on top — you get ANPR, watchlists, tracking, evidence and GIS
without replacing what works.

## 2. How do you integrate different vendors?

Through a **gateway/aggregation tier**: vendor VMS adapters normalize streams + metadata
(protocol, resolution, vendor, VMS source, lifecycle — all present in the 52-camera registry)
into one canonical camera/event model. Downstream modules only speak the canonical model, so
vendor differences are hidden from analytics.

## 3. How does the system scale to 80,000 cameras?

Tiered design, not a single server:
**edge ingestion → regional gateways (aggregation, storage, GPU inference pools) → central
intelligence layer** (matching, alert engine, tracking, GIS, search) over a message/event bus.
The supplied scale simulator measured a 10-point load curve (50 → 10,000 cameras) against the
real API/WebSocket. 80,000 is the architecture target; the simulator models it logically
(SCALABILITY_80K_CAMERAS.md) — we do not claim a live 80k deployment.

## 4. Where does AI inference happen?

In production: at the edge (small models, low latency) plus regional GPU inference pools for
full-frame analytics (YOLO-class detector, TensorRT in roadmap). In this POC the detector runs
in "mock" mode by default and can switch to a real YOLO backend when the model is provisioned
(modelled honestly in `/system/health`).

## 5. How do you prevent false ANPR matches?

Two-stage blur + confidence gating:
1. **Normalization**: format stripping (`GJ 01 AB 1234` → `GJ01AB1234`).
2. **OCR collapse**: ambiguous char map applied to both sides (`I→1`, `O→0`, `L→1`, `S→5`).
3. **Fuzzy tolerance + thresholds**: edit-distance ≤ 1; below 0.62 confidence = no match,
   ≥ 0.78 = matched, ≥ 0.98 = exact; critical-escalation only ≥ 0.85.
4. Every match records the raw read + decided match + confidence (audit visible in the demo log),
   and alerts are deduplicated.

The demo deliberately feeds OCR variants (`GJ0IAB1234`, `GJ01A91234`, `GJ 0L AB 1234`) that all
resolve to the same watchlist vehicle under these rules.

## 6. How does cross-camera tracking work?

A matched entity gets a **track**; each subsequent camera sighting creates a **movement event**
(timestamp, camera, lat/lon, confidence, evidence id). Re-linking tolerates OCR drift
(similarity ≥ 0.85, reappearance window 600 s) so one vehicle becomes one story. Demo runs
produce exactly **1 track, 6 hops, 6 movement events** in logical corridor order — re-runs add
zero duplicates.

## 7. What happens when a camera goes offline?

The registry tracks status/health/heartbeat; offline and degraded cameras are surfaced with
their real status (never a fake "LIVE"), remain visible in the registry/wall, and alerts stop
being generated from them. The system continues with remaining cameras; recovery is shown on
the next heartbeat/refresh.

## 8. How do you secure the platform?

- **Auth**: JWT (HS256, signed/verified, expiry) + PBKDF2-SHA256 salted password hashing.
- **RBAC**: VIEWER → AUDITOR → INVESTIGATOR → OPERATOR → ADMIN on every sensitive route.
- **Transport**: CORS allowlist, WebSocket origin validation, TLS in production.
- **Data**: input validation, upload size/extension checks, filename sanitization, evidence
  served by ID only (no filesystem path exposed), audit log on sensitive actions, coarse
  rate limiting, and sanitized error messages (no path leakage).
- POC default `AUTH_REQUIRED=false` (dev principal) is documented; production enforces it.

## 9. How do you handle evidence?

Every event can produce an evidence snapshot (JPEG in the demo). Files carry a **SHA-256 hash**,
are stored under `uploads/evidence`, downloaded only via `GET /api/evidence/{id}/file`,
missing files → clean 404, and the schema never leaks the internal path. Verified end-to-end.

## 10. How much bandwidth is required?

Three distinct numbers, never mixed:
- **Live video**: one stream per camera, encoded at source (e.g., 4K≈2.2 Mbps, 1080P≈1.3 Mbps —
  approximately 300 Mbps for all 52 demo cameras, illustrative planning estimate).
- **AI metadata/event bandwidth**: tiny — plate reads, detections, alerts as JSON events (KBs).
- **Evidence storage**: compressed snapshots per event (KB–MB), not full recording.
SCALABILITY_80K_CAMERAS.md keeps these columns separate.

## 11. How much storage is required?

Illustrative planning estimate only: retention is a policy choice. Example — 30-day live footage
at recorded bitrate is the dominant cost; metadata + evidence snapshots are comparatively small;
GOV-compliant evidence can be write-once, read-many storage. No claim is made that these are
measured production figures.

## 12. How do departments use the system?

One shared intelligence layer, role-separated access (RBAC). Each department sees the same
events through their own role/permission plane — operations monitors, investigators search
evidence, auditors read immutable audit logs, commanders get the Command Center.

## 13. How can police search a vehicle/person?

Unified search API: query the plate (e.g., `GJ01AB1234`) and get alert, track, camera, detection
and evidence facets; follow the entity movement trail (where/when/which cameras) and jump into
the GIS route and evidence. Frontend investigation page exposes it directly.

## 14. How does GIS help investigators?

Every camera has lat/lon; every movement event has a location; the trail renders as an ordered
route over the map (6 hops, timestamps increasing). An investigator sees the vehicle's path
across the city/state instead of piecing together logs — then drills into each sighting.

## 15. What is implemented vs future roadmap?

**Implemented:** heterogeneous registry (52 cams, real metadata), demo livestream/simulation,
detection pipeline, ANPR normalization + OCR collapse + fuzzy matching, watchlist CRUD/matching,
alert engine with dedup + status workflow, evidence vault (hash + download), cross-camera
tracking + movement history, GIS cameras/routes/events, unified search, analytics, real-time
WS push, RBAC + JWT + audit, scale simulator, demo reset/run (idempotent), 124 pytest + 30/30
E2E + 19/19 browser suite.
**Roadmap:** real YOLO ingestion (backend ready, model-gated), object storage, Postgres HA,
GPU pool orchestration, SIEM export, geo-fencing, SMS/desk-alert integrations.

## 16. What happens if the central platform fails?

POC: region/DB restart is handled — demo reset re-runs cleanly, WS clients auto-reconnect
(backoff), interrupted jobs are re-queued on boot. Production design: stateless API tier,
durable queue, regional gateways keep recording locally during central outage, and metadata
cache means operators stay functional until recovery. (Architecture — not a tested production
claim.)

## 17. How do you avoid duplicate alerts?

Per (entity, camera, watchlist) cooldown window + dedup key on creation; a live track re-use
window prevents re-alerting the same sighting. Verified: repeated demo execution creates 6
alerts once, then **0 new** on every re-run.

## 18. How does the system work with existing government infrastructure?

It consumes it: the gateway tier ingests existing VMS/RTSP/regional feeds into the canonical
model, and the web app runs on standard government browsers over the agency network. Data
stays in-agency (POC can run fully on localhost/SQLite); no vendor lock-in, no rip-and-replace.

## 19. What makes Sentinel AI different?

**One Intelligence Layer Across a Heterogeneous CCTV Ecosystem.** Competitors watch video;
Sentinel watches *events*. Normalize feeds → match watchlists → track across cameras → bag the
evidence → map the trail — in one place, without unifying the physical cameras.

## 20. What is the deployment strategy?

- **LOCAL DEMO** (judged today): `uvicorn` + SQLite + mock detector + Vite frontend.
- **POC DEPLOYMENT**: containerized backend, real YOLO backend option, Postgres, one gateway.
- **PRODUCTION**: tiered edge → regional gateway → central intelligence, object storage,
  GPU pools, decomposition of the scale/security docs into runbooks.
These three are documented as separate concepts — a production deployment is not claimed to be
operational unless it has been tested.