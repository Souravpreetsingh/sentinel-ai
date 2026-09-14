"""Watchlist matching engine.

Decisions returned by :func:`match_plate` follow the Phase 6 contract:

* ``matched``          — high-confidence match (>= ``watchlist_probable_threshold``)
* ``probable match``   — plausible match below the high-confidence bar
* ``no match``         — below ``watchlist_min_confidence`` / no candidate

Every result is scored even when no watchlist entry matches, so downstream
consumers always see an explicit confidence value. Critical alerts are never
generated from an obviously low-confidence match — the engine simply does not
emit ``matched`` at those confidence levels.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.config import Settings, get_settings
from app.services.plates import collapse_ocr, normalize_plate


@dataclass(slots=True)
class MatchResult:
    decided: str  # "matched" | "probable match" | "no match"
    match_type: str  # "exact" | "fuzzy" | "probable" | "no_match"
    confidence: float  # 0..1
    watchlist_id: str | None = None
    candidate: dict[str, Any] | None = None
    normalized_plate: str = ""
    scrutineering: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "decided": self.decided,
            "match_type": self.match_type,
            "confidence": round(self.confidence, 4),
            "watchlist_id": self.watchlist_id,
            "normalized_plate": self.normalized_plate,
            "scrutineering": self.scrutineering,
        }


def _edits(a: str, b: str) -> int:
    """Iterative Levenshtein distance (stdlib-only)."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(
                prev[j] + 1,          # deletion
                cur[j - 1] + 1,       # insertion
                prev[j - 1] + (0 if ca == cb else 1),
            ))
        prev = cur
    return prev[-1]


def rails(v: list[tuple[str, str]]) -> list[str]:
    return [f"{a}->{b}" for a, b in v]


def match_plate(
    raw_plate: str,
    watchlist: list[dict[str, Any]],
    settings: Settings | None = None,
) -> MatchResult:
    """Match an ANPR read against a list of watchlist entity dicts.

    Each watchlist dict must expose ``id``, ``plate_normalized`` (already
    normalised at write time) and optionally ``priority``.
    """
    settings = settings or get_settings()
    norm = normalize_plate(raw_plate)
    if not norm:
        return MatchResult(decided="no match", match_type="no_match", confidence=0.0)

    best: tuple[float, dict[str, Any] | None, str] = (0.0, None, "no_match")
    scrutineering: list[str] = []

    for entity in watchlist:
        ref = entity.get("plate_normalized") or normalize_plate(entity.get("vehicle_registration"))
        if not ref:
            continue
        # Exact on clean-normalised keys.
        if norm == ref:
            conf = max(settings.watchlist_exact_threshold, 0.99)
            if conf > best[0]:
                best = (conf, entity, "exact")
            scrutineering.append(f"{ref}: exact match")
            continue
        # OCR-permissive exact: collapse ambiguity on both sides identically.
        if collapse_ocr(norm) == collapse_ocr(ref):
            conf = min(0.98, max(settings.watchlist_probable_threshold, 0.94))
            if conf > best[0]:
                best = (conf, entity, "exact")
            scrutineering.append(f"{ref}: exact match after OCR collapse")
            continue

        # Fuzzy: tolerate a small number of edits relative to plate length.
        distance = _edits(norm, ref)
        max_len = max(len(norm), len(ref), 1)
        similarity = 1.0 - (distance / max_len)
        if similarity >= (1.0 - settings.watchlist_fuzzy_tolerance / max_len) and similarity > 0.6:
            conf = min(0.96, 0.72 + similarity * 0.2)
            if conf > best[0]:
                best = (conf, entity, "fuzzy")
            scrutineering.append(f"{ref}: fuzzy similarity={similarity:.2f}")

    confidence, entity, match_type = best
    if entity is None:
        return MatchResult(
            decided="no match",
            match_type="no_match",
            confidence=round(confidence, 4),
            normalized_plate=norm,
            scrutineering=scrutineering or [f"no candidate beyond {settings.watchlist_min_confidence}"],
        )

    if confidence >= settings.watchlist_probable_threshold:
        decided = "matched"
    elif confidence >= settings.watchlist_min_confidence:
        decided = "probable match"
    else:
        decided = "no match"
        match_type = "no_match"

    return MatchResult(
        decided=decided,
        match_type=match_type,
        confidence=round(confidence, 4),
        watchlist_id=entity.get("id"),
        candidate=entity,
        normalized_plate=norm,
        scrutineering=scrutineering,
    )