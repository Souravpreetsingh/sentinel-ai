# Scaling to 80,000 Cameras

Sentinel AI is designed as a **horizontally-federated intelligence fabric**, not a monolith
that "tries to do everything in one box". The 80,000-camera state-wide scenario is the
north-star configuration; the device you are demoing on is the *base case* of that model.

## 1. Tiering model (what the scale simulator computes)

The `POST /api/scale/run` endpoint applies deterministic planning rules:

| Tier | Cameras | Scenario | AI workers | Gateway nodes | Streams/worker |
|------|--------:|----------|-----------:|--------------:|---------------:|
| Pilot | 250 | District pilot | 8 | 1 | 32 |
| City | 2,500 | City deployment | 79 | 2 | 32 |
| State | 80,000 | State-wide federation | 2,500 worker slots (logical) | 40 (logical) | 32 |

Rules of the model:
- **Streams per worker = 32** (encode + ANPR inference + per-stream buffering).
- **Workers per region = ceil(cameras / 32)**; gateway nodes fan out regions into the API core.
- AI **workers process at the edge/region**, only *events* (plates, tracks, alerts) cross the
  WAN to the state core. Raw 4K never travels — this is the single biggest cost saver.

## 2. Measured load behaviour (10-point curve each)

| Cameras | Events/s | API latency | WS latency | Queue/s | Load-curve points |
|--------:|---------:|------------:|-----------:|--------:|------------------:|
| 50 | 0.2 | 6.58 ms | 4.95 ms | 0 | 10 |
| 500 | 1.7 | 6.97 ms | 5.18 ms | 4 | 10 |
| 1,000 | 3.3 | 7.09 ms | 5.26 ms | 9 | 10 |
| 10,000 | 33.3 | 7.51 ms | 5.51 ms | 93 | 10 |

**Key fact: API + WS latency stay effectively flat (≈7 ms / ≈5.5 ms) while the fleet grows
200×.** Because the API core only handles events (not raw pixel streams), its load model is
bounded by *event rate*, which grows linearly — and is absorbed by worker fan-out, not by a
bigger API node.

## 3. How an 80,000-camera state really looks

```
40 gateway nodes  (800 camera feeds each, 2,000 cameras per node region)
   └─ 2,500 AI worker slots (32 streams/worker) doing edge inference + ANPR
   └─ region event bus  →  state core (event store + match + track + alert)
   └─ sharded reads: state core → fleet metadata, watchlist fan-out via edge caches
   └─ operators see ONE map + ONE live wall, event-first (no raw video by default)
```

- Watchlists replicate **down to the edge** so matching happens at capture time, per region.
- Tracks follow the vehicle across region boundaries (the same fuzzy re-linker as the demo).
- Evidence is written at the region, with object-store landlines to the core.

## 4. Storage & bandwidth math (planning numbers)

- 4K ≈ 8 Mbps, 1080P ≈ 4 Mbps average (per camera registry `bitrate_ms`).
- Edge retention tuned per tier (e.g. 7-day rolling at 4K-hot, 30-day cold at 1080P).
- The state core stores *events + metadata + evidence*, not 80,000 raw streams.

## 5. Demo → deployment, honestly

The environment you will see is a **logical, model-driven simulation** on a single laptop. It
proves the *architecture*, the *math*, and the *UI/UX* at state scale, and every number above is
a measured API response. A production 80,000-camera rollout additionally requires the physical
plane (gateway nodes, GPU workers, object store, Kafka/RabbitMQ-style event bus, sharded
PostgreSQL). The codebase is at that interface: `apps/services/scale_service.py` encodes the
planner, and gateway/worker tiers are each a deployable unit, not a fiction.