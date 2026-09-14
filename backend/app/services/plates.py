"""Number-plate normalisation for reliable ANPR watchlist matching.

Normalisation collapses the common real-world variations that otherwise cause
false negatives:

* whitespace / hyphens / dots     ``GJ 01 AB 1234``
* casing                          ``gj01ab1234``
* OCR confusions                  ``O``->``0``, ``I``->``1``, ``Z``->``2`` etc.
* regional formatting             ``GJ-01-AB-1234``
"""

from __future__ import annotations

import re

# OCR character confusion pairs applied consistently to *both* the watchlist
# registration and the ANPR read so that imperfect OCR still matches a plate.
# Only truly visually-similar digit/letter pairs are collapsed. Letters in
# their natural positions (like 'G' in a state code) must survive.
_OCR_MAP = {
    "O": "0",
    "Q": "0",
    "I": "1",
    "L": "1",
    "Z": "2",
    "S": "5",
    "T": "7",
}

_STRIP_RE = re.compile(r"[^A-Z0-9]")


def normalize_plate(raw: str | None) -> str:
    """Return the canonical plate key (formatting stripped, no OCR collapsing).

    ``GJ 01 AB 1234``, ``gj-01-ab-1234`` and ``GJ.01.AB.1234`` all normalise to
    ``GJ01AB1234``. A reference plate stored on the watchlist is always kept in
    this clean form; OCR ambiguity is handled at match time by
    :func:`collapse_ocr`, applied to *both* sides consistently.
    """
    if not raw:
        return ""
    text = str(raw).upper().strip()
    text = _STRIP_RE.sub("", text)
    return text if text else ""


def collapse_ocr(plate: str) -> str:
    """Apply the OCR confusion map to a normalised plate for matching."""
    return "".join(_OCR_MAP.get(ch, ch) for ch in str(plate or "").upper())


def is_valid_plate(plate: str) -> bool:
    """Heuristic sanity check: normalised plates are 3–14 alphanumerics."""
    norm = normalize_plate(plate)
    return 3 <= len(norm) <= 14