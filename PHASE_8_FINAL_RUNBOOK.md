# Sentinel AI — Phase 8 Final Runbook (Submission)

Exact, copy-paste commands for a complete clean boot through a full demonstration. This is the
freeze-state runbook for hackathon evaluation.

## 0. Pre-flight

- Windows machine with Python 3.12+ and Node 20+.
- Backend requirements already installed: `backend\.venv` (see README "Local Setup").
- Ports free: `8000` (backend), `5173` (frontend).

## 1. Start backend

```powershell
cd "D:\cctv ai\sentinel-ai\backend"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**Verify** (wait ~5 s for boot + seed):

```
Open http://127.0.0.1:8000/docs   -> should render OpenAPI
```

## 2. Start frontend

```powershell
cd "D:\cctv ai\sentinel-ai"
npm run dev
```

**Verify:** `http://localhost:5173` renders the Sentinel AI UI.

## 3. Login

Dev build ships `AUTH_REQUIRED=false` (read-only access works without login). For full access:

- Email: `admin@sentinel.local`
- Password: `admin12345`
- (Local demo credentials only; never production.)

## 4. Reset demo

In **Command Center**, click **RESET DEMO** (or run):

```powershell
Invoke-RestMethod -Method Post "http://127.0.0.1:8000/api/demo/reset"
```

Response must show `readiness: cameras=52, route_cameras_ready=true, watchlist_ready=true`.

## 5. Run demo

Click **RUN DEMO TEST** (or):

```powershell
Invoke-RestMethod -Method Post "http://127.0.0.1:8000/api/demo/run-test"
```

Expected: `6 alerts`, `1 track`, `6 evidence` — idempotent (re-run creates 0 new).

## 6–13. Walkthrough (in order)

| Step | Where | What to show |
|------|-------|--------------|
| 6  | Command Center | KPI tiles, feed grid, DEMO SIMULATION badge |
| 7  | **Alerts** | 6 `ALR-900x`; run ACK → INVESTIGATE → RESOLVE (persists on refresh) |
| 8  | **Evidence** | 6 demo ANPR snapshots (Evidence list also shows pre-seeded historical evidence); download one (`/api/evidence/{id}/file`) |
| 9  | **Tracking** | single `TRK-…`, hop_count 5, 6 movement events; open movement history |
| 10 | **GIS Map** | 52 cameras + route CAM-09 → CAM-14, ordered, timestamps increasing |
| 11 | **Search** | query `GJ01AB1234` — alerts, tracks, evidence facets |
| 12 | **Analytics** | backend-derived counts; reset→run changes values (no stale data) |
| 13 | **System Health** | real values: 11× 4K + 28× 1080P streams, storage, WS clients, overall |

**OCR resilience (bonus):** console logs show `GJ0IAB1234`, `GJ01A91234`, `GJ 0L AB 1234`
all resolving to `GJ01AB1234` (backend log: `backend\uploads\uvicorn.out.log`).

## 14. Repeat the demo (safety demo)

```powershell
Invoke-RestMethod -Method Post "http://127.0.0.1:8000/api/demo/reset"
Invoke-RestMethod -Method Post "http://127.0.0.1:8000/api/demo/run-test"
```

Run this loop as many times as needed — always 6 alerts / 1 track / 6 evidence / **zero
duplicates** (verified 10 consecutive cycles).

## 15. Camera Fullscreen

1. **Live Cameras** → click any camera to open its single-camera view.
2. Click **Fullscreen** (bottom control bar) — the camera fills the entire browser viewport
   (identity badge, LIVE status, FPS, AI overlays and controls stay visible).
3. Press **Esc** or click the **Exit fullscreen** icon in the bottom control bar to return
   to the normal view.

Also available on the **Command Center → CAMERA FEED MATRIX** cards (fullscreen icon in the
card footer).

**Browser compatibility:** uses the native **Fullscreen API**
(`Element.requestFullscreen` / `document.exitFullscreen`, `fullscreenchange` handled) with
feature detection for Chrome, Edge, Firefox and Safari. If the native API is unavailable or
the request is rejected, it degrades gracefully to an in-app fullscreen overlay instead of
crashing — and `Esc`/Exit still restore the normal view.

## 16. Troubleshooting

| Symptom | Fix |
|---------|-----|
| `127.0.0.1:8000` refused | Start backend (Step 1). Check `backend\uploads\uvicorn.err.log`. |
| Blank `localhost:5173` | Start frontend (Step 2). Check `vite.out.log` at repo root. |
| CORS errors in console | Ensure `ALLOWED_ORIGINS` includes `http://localhost:5173`; restart backend. |
| Demo shows 0 alerts | Port conflict → check any other process on 8000; restart; **RESET → RUN**. |
| `sqlite3.IntegrityError` at boot | Old corrupt DB: delete `backend\sentinel.db`; restart (seeds recreate cleanly). |
| WS events stop | Backend restart resets WS; FE auto-reconnects (backoff). Hard-refresh page. |
| Analytics/health show zeros | Restart backend (health/storage values are measured live at call time). |

## 17. Backup plan (if the live demo misbehaves)

1. **Reset demo** → `POST /api/demo/reset`
2. **Restart backend** (Step 1) → verify `/docs`
3. **Restart frontend** (Step 2) → verify `localhost:5173`
4. **Run smoke test**:

```powershell
cd "D:\cctv ai\sentinel-ai\backend"
$env:PYTHONPATH="D:\cctv ai\sentinel-ai\backend"
.\.venv\Scripts\python.exe "C:\Users\SOURAV~1\AppData\Local\Temp\opencode\smoke_phase6.py"  # 30/30
```

5. **Re-run demo** → RESET DEMO → RUN DEMO TEST → verify 6 alerts / 1 track / 6 evidence.

No fake screenshots — the demo is always re-runnable live.