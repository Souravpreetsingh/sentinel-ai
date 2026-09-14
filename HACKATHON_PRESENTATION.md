# Sentinel AI — Hackathon Presentation (15 slides)

Deck content for a 5-minute run-in through the live demo. Every number is a measured value from
`HACKATHON_TEST_CASE_REPORT.md`.

---

**Slide 1 — Title.** Sentinel AI
*One Intelligence Layer Across a Heterogeneous CCTV Ecosystem.* Sub: ANPR watchlists, cross-camera tracking, evidence & GIS — from a city to a state.

**Slide 2 — Problem.** Police CCTV is fragmented: vendor formats, resolution mixes, OCR error, no shared intelligence. X years of footage is watched too late. Question the panel can answer — "how would an investigator chase a stolen plate across 8,000 cameras today?".

**Slide 3 — Thesis.** Don't watch video. Watch *events*. A single intelligence layer normalizes heterogeneous feeds → plates, tracks, alerts, evidence — delivered in ~570 ms to an operator.

**Slide 4 — The pipeline (diagram).** Camera → Detection → ANPR normalize/OCR-collapse → Watchlist match (exact→fuzzy) → Alert (dedup + cooldown) → Evidence snapshot → Cross-camera track → Real-time push.

**Slide 5 — Live demo, hold the stage.** Start backend + UI on the projector. RESET DEMO → RUN DEMO TEST. Vehicle `GJ 01 AB 1234` drives CAM-09→14.

**Slide 6 — Live Wall feel.** Second tab: alerts stream over WebSocket in real time (post→alert = 568 ms). Detection boxes + alert cards as they land.

**Slide 7 — The OCR-resilience slide.** Show logs: `GJ 01 AB 1234` (exact 0.99), `GJ0IAB1234` (collapse 0.94), `GJ01A91234` (fuzzy 0.90), `GJ 0L AB 1234` (collapse 0.94). One plate, four readings, one match.
Why it works: normalize == strip formatting only, collapse_ocr maps O→0/I→1/Z→2/S→5/T→7 on both sides.

**Slide 8 — Tracking evidence.** One track, 6 movement hops, +90 s per hop, single CAD route. Fuzzy re-link merges OCR drift into one vehicle story; dedup prevents double counting.

**Slide 9 — Operator workflow.** Alert lifecycle NEW → ACKNOWLEDGED → INVESTIGATING → RESOLVED / FALSE POSITIVE, one click per transition, timestamps captured for audit.

**Slide 10 — Resilience.** Camera taken OFFLINE via lifecycle_status: it goes offline, the other 50 keep streaming, restore brings it back online. Backend restart: schema self-heals, WS reconnects.

**Slide 11 — Measurement wall.** API median 26–38 ms; full 6-hop demo 487 ms; 6 alerts+6 evidence+1 track; WS push 568 ms; 124 pytest + 30/30 E2E; build 1.4 s.

**Slide 12 — Scale.** 50 → 10,000 cameras: AI workers 2→313, gateways 1→5, API latency flat ≈7 ms, WS flat ≈5.5 ms. Events-not-pixels architecture.

**Slide 13 — 80,000-camera federation.** 40 gateway nodes, 2,500 worker slots, watchlists replicated to the edge — matching happens at capture time. Full story in SCALABILITY_80K_CAMERAS.md.

**Slide 14 — Security.** JWT (HS256 stdlib) + PBKDF2 passwords + 5-role RBAC + deny-by-default; audit trail on every mutation; CORS allowlist; idempotent everything; honest scope boundaries.

**Slide 15 — Close.** "We built the layer that makes 80,000 CCTV cameras one camera." Demo vehicle re-run at the judges' seat — RESET, RUN, 30 seconds, done. Questions; point to the 5 docs in the repo.

---

## Optional Q&A ammo

- *Why not raw video in the core?* Cost + privacy. Events only cross the WAN; pixels stay at the edge.
- *How do you handle OCR errors?* Multi-pass matching: exact → OCR-collapse → fuzzy (Levenshtein), thresholds 0.98/0.90/0.62–0.78; plus ±0.05 same-watchlist bonus.
- *No duplicates on repeated demo runs?* Dedup key (entity:camera:watchlist) + 120 s cooldown + idempotent seeding + reset endpoint. Run it as many times as you like.
- *PostgreSQL?* One env var: `DATABASE_URL`; `is_postgres()` path is wired; demo ships SQLite for zero-setup offline judge machines.