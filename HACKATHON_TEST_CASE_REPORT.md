# Hackathon Test Case & Measurement Report

All results below were recorded **live against the running local stack** on this machine
(backup date 2026-09-15) — no numbers are fabricated. Reproduce any measurement with the
command shown.

## 1. Automated test status

| Suite | Result | Notes |
|-------|--------|-------|
| Backend pytest (`backend` → `python -m pytest -q`) | **124 passed** | 118 Phase-6 + 6 Phase-7 tests |
| Phase 7 additions | 6 passed | demo reset, alert workflow, system health bandwidth, analytics schema |
| E2E smoke (`…/Temp/opencode/smoke_phase6.py`) | **30/30 passed** | cameras, demo, track hops=5, 6 movements, scale, GIS, incidents |
| Frontend build (`npm run build`) | **pass** | 46 modules, `index-tJfXtekd.js` 445.94 kB (gzip 116.73 kB), 1.43 s |
| Frontend lint (`npm run lint` / oxlint) | 0 errors, warnings only | pre-existing style warnings |

## 2. Live functional checks

| Check | Result |
|-------|--------|
| `/api/analytics/overview` with `Origin: http://localhost:5173` | **200** + `Access-Control-Allow-Origin` echoes origin (schema fix verified) |
| `/api/analytics/events`, `/traffic`, `/cameras` | **200** + ACAO header |
| `/api/system/health` bandwidth mix | `streams1080p: 28`, `streams4k: 11`, cameras 52, `overall: 98` |
| `/api/demo/reset` | cleared 12 alerts / 2 tracks / 12 movements / 24 detections / 12 evidence / 6 files; readiness 52 cams + route + watchlist `true` |
| `/api/demo/run-test` (after reset) | 6 hops → 6 alerts, 6 evidence, 1 track, +90 s timeline |
| `/api/demo/run-test` (again) | **0 new artifacts** (idempotent) |
| Camera lifecycle fail/restore | `PATCH CAM-12 {"lifecycle_status":"OFFLINE"}` → `offline`; `{"lifecycle_status":"ACTIVE"}` → `online`; CAM-37 (seed-offline) + others unaffected |

## 3. API latency (real, median of 5 requests each)

| Endpoint | Median | Min | Max |
|----------|--------|-----|-----|
| `/api/cameras?limit=100` | 29.19 ms | 16.34 | 34.31 |
| `/api/alerts?limit=100` | 25.79 ms | 9.60 | 36.99 |
| `/api/search?query=GJ01AB1234&limit=50` | 34.65 ms | 32.88 | 44.36 |
| `/api/analytics/overview` | 37.65 ms | 35.54 | 43.03 |
| `/api/gis/route/GJ01AB1234` | 29.28 ms | 9.01 | 39.79 |
| `/api/evidence?limit=50` | 30.00 ms | 19.86 | 32.41 |
| `/api/watchlists?limit=20` | 30.72 ms | 21.19 | 39.15 |
| `/api/incidents?limit=20` | 33.88 ms | 18.66 | 38.91 |

Single-machine dev figures; sub-40 ms across the dashboard.

## 4. End-to-end demo pipeline (single run, fresh reset)

- Full 6-hop run: **486.8 ms** (`POST /api/demo/run-test`)
- Artifacts: 6 detections, **6 alerts** (`ALR-9001…9006`), 1 cross-camera track `TRK-F1CEB871C5`,
  6 evidence snapshots; hop timestamps spaced +90 s to model real travel.
- OCR-resilient matches shown in logs: `GJ 01 AB 1234` (exact 0.99) · `GJ0IAB1234`
  (OCR-collapse 0.94) · `GJ01A91234` (fuzzy 0.90) · `GJ 0L AB 1234` (OCR-collapse 0.94).

## 5. Real-time (WebSocket) push

| Metric | Value |
|--------|-------|
| WS subscribe → demo POST | 63.4 ms |
| demo POST → first `alert.created` over WS | **568.4 ms** |
| Events received in window | 13 (1 system_status, 6 detection, 6 alert.created) |
| Client model | Auto-reconnecting (exponential backoff), verified by backend restart |

## 6. Scale simulator (logical model, real API)

`POST /api/scale/run` + `GET /api/scale/load-curve` (10-point curve each):

| Cameras | Scenario | AI workers | Gateways | Events/s | API latency | WS latency | Queue/s |
|---------|----------|-----------:|---------:|---------:|------------:|-----------:|--------:|
| 50 | District pilot | 2 | 1 | 0.2 | 6.58 ms | 4.95 ms | 0 |
| 500 | City deployment | 16 | 1 | 1.7 | 6.97 ms | 5.18 ms | 4 |
| 1,000 | City deployment | 32 | 1 | 3.3 | 7.09 ms | 5.26 ms | 9 |
| 10,000 | State-wide federation | 313 | 5 | 33.3 | 7.51 ms | 5.51 ms | 93 |

Latency stays flat as the fleet grows — the design scales out workers/gateways, not the API.

## 7. Camera & resilience evidence

- 52 cameras on the map; 2 offline at measurement time: `CAM-12` (deliberate fail/restore flip)
  and `CAM-37` (seed fixture). All other segments kept streaming.
- Backend restart mid-session: schema reconciled, data persisted, WS clients re-attached.

## 8. Reproduce

```powershell
cd "D:\cctv ai\sentinel-ai\backend"
.\.venv\Scripts\python.exe -m pytest -q                    # 124 passed
cd "D:\cctv ai\sentinel-ai"
npm run build                                              # pass
$env:PYTHONPATH="D:\cctv ai\sentinel-ai\backend"
python "C:\Users\SOURAV~1\AppData\Local\Temp\opencode\smoke_phase6.py"   # 30/30
python "C:\Users\SOURAV~1\AppData\Local\Temp\opencode\measure_phase7.py" # live metrics above
```