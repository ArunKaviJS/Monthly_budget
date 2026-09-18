"""
intent_engine.py — Deterministic NLP pipeline for expense classification.

NO AI / LLM / ML.  Uses only:
  • normalisation + regex
  • keyword dictionary lookup
  • difflib.SequenceMatcher for fuzzy matching
  • learned keywords from SQLite

All functions are pure (except load_learned_keywords which reads the DB).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
from datetime import date, timedelta, datetime
from typing import Dict, List, Optional, Tuple

from .intent_config import (
    INTENTS,
    PRIORITY_ORDER,
    CONFIDENCE_THRESHOLD,
    TIE_MARGIN,
    EXACT_KEYWORD_WEIGHT,
    PHRASE_WEIGHT,
    FUZZY_WEIGHT,
    LEARNED_KEYWORD_WEIGHT,
    FUZZY_MIN_RATIO,
    STOPWORDS,
    AMOUNT_PATTERNS_FOR_CLEANUP,
)


# ═══════════════════════════════════════════════
# Data classes
# ═══════════════════════════════════════════════
@dataclass
class IntentResult:
    intent: str
    confidence: float
    matched_keywords: List[str] = field(default_factory=list)
    reason: str = ""


@dataclass
class ParseResult:
    amount: Decimal
    intent: str
    confidence: float
    description: str
    spent_on: date
    matched_keywords: List[str] = field(default_factory=list)
    reason: str = ""


# ═══════════════════════════════════════════════
# 1. NORMALIZE
# ═══════════════════════════════════════════════
_SHORTHAND = [
    # ₹ symbol
    (r"₹\s*", "rs "),
    # "/-" suffix  e.g. "250/-"
    (r"(\d)\s*/\s*-", r"\1 "),
    # "inr" prefix/suffix
    (r"\binr\s*", "rs "),
    # "rupees" -> "rs"
    (r"\brupees?\b", "rs"),
]


def normalize(text: str) -> str:
    """Lowercase, strip punctuation (keep decimal points in numbers),
    collapse whitespace, expand shorthand."""
    t = text.lower().strip()

    # Expand shorthand
    for pattern, repl in _SHORTHAND:
        t = re.sub(pattern, repl, t)

    # Handle "k" multiplier BEFORE stripping punctuation
    # "1.5k" -> "1500", "2k" -> "2000"
    def _expand_k(m: re.Match) -> str:
        num = float(m.group(1))
        return str(int(num * 1000))

    t = re.sub(r"(\d+(?:\.\d+)?)\s*k\b", _expand_k, t)

    # Strip punctuation except decimal points inside numbers
    # First protect decimal numbers: "3.5" -> "3__DOT__5"
    t = re.sub(r"(\d)\.(\d)", r"\1__DOT__\2", t)
    # Remove remaining punctuation
    t = re.sub(r"[^\w\s]", " ", t)
    # Restore decimal points
    t = t.replace("__DOT__", ".")

    # Collapse whitespace
    t = re.sub(r"\s+", " ", t).strip()

    return t


# ═══════════════════════════════════════════════
# 2. EXTRACT AMOUNT
# ═══════════════════════════════════════════════
_AMOUNT_PATTERNS = [
    # "rs 250", "rs. 250", "rs250"
    r"\brs\.?\s*(\d+(?:\.\d+)?)\b",
    # "250 rs", "250rs"
    r"\b(\d+(?:\.\d+)?)\s*rs\.?\b",
    # Plain number (last resort)
    r"\b(\d+(?:\.\d+)?)\b",
]


def extract_amount(text: str) -> Tuple[Optional[Decimal], str]:
    """Extract the monetary amount from normalised text.

    Returns (amount, leftover_text_with_amount_removed).
    Returns (None, text) if no amount found.
    """
    normalized = text

    for pattern in _AMOUNT_PATTERNS:
        m = re.search(pattern, normalized)
        if m:
            try:
                amount = Decimal(m.group(1))
                if amount <= 0:
                    continue
                # Remove the entire match from text
                leftover = normalized[:m.start()] + normalized[m.end():]
                # Clean up "rs" remnants
                leftover = re.sub(r"\brs\.?\b", "", leftover)
                leftover = re.sub(r"\s+", " ", leftover).strip()
                return amount, leftover
            except (InvalidOperation, ValueError):
                continue

    return None, normalized


# ═══════════════════════════════════════════════
# 3. EXTRACT DATE
# ═══════════════════════════════════════════════
_DATE_KEYWORDS = {
    "today": 0,
    "yesterday": -1,
    "ystd": -1,
    "ytd": -1,
    "day before yesterday": -2,
    "day before": -2,
}

_DATE_PATTERN = re.compile(
    r"\b(\d{1,2})[/\-](\d{1,2})(?:[/\-](\d{2,4}))?\b"
)


def _get_today() -> date:
    """Get today's date in Asia/Kolkata timezone.
    We avoid pytz dependency — use a fixed UTC+5:30 offset."""
    from datetime import timezone
    ist = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist).date()


def extract_date(text: str) -> Tuple[date, str]:
    """Extract date from text. Returns (date, leftover_text).
    Default = today (IST)."""
    lower = text.lower()

    # Check keyword dates (longest first to match "day before yesterday")
    for kw in sorted(_DATE_KEYWORDS, key=len, reverse=True):
        if kw in lower:
            d = _get_today() + timedelta(days=_DATE_KEYWORDS[kw])
            leftover = re.sub(re.escape(kw), "", lower, count=1)
            leftover = re.sub(r"\s+", " ", leftover).strip()
            return d, leftover

    # Check date patterns like "1/9", "01-09-2026"
    m = _DATE_PATTERN.search(lower)
    if m:
        day = int(m.group(1))
        month = int(m.group(2))
        year_str = m.group(3)
        today = _get_today()
        if year_str:
            year = int(year_str)
            if year < 100:
                year += 2000
        else:
            year = today.year

        try:
            d = date(year, month, day)
        except ValueError:
            # Try swapping day/month (Indian format ambiguity)
            try:
                d = date(year, day, month)
            except ValueError:
                return today, text

        leftover = text[:m.start()] + text[m.end():]
        leftover = re.sub(r"\s+", " ", leftover).strip()
        return d, leftover

    return _get_today(), text


# ═══════════════════════════════════════════════
# 4. CLASSIFY
# ═══════════════════════════════════════════════
def _fuzzy_score(word: str, keyword: str) -> float:
    """Return SequenceMatcher ratio if >= threshold, else 0."""
    if len(word) < 3 or len(keyword) < 3:
        return 0.0
    ratio = SequenceMatcher(None, word, keyword).ratio()
    return ratio if ratio >= FUZZY_MIN_RATIO else 0.0


def classify(
    text: str,
    learned_keywords: Optional[Dict[str, str]] = None,
) -> IntentResult:
    """Score every intent and return the best match.

    Args:
        text: normalised text with amount already removed.
        learned_keywords: dict of {keyword: intent} from the DB.

    Returns:
        IntentResult with intent, confidence, matched_keywords, reason.
    """
    if not text.strip():
        return IntentResult(
            intent="others",
            confidence=0.0,
            matched_keywords=[],
            reason="Empty text after amount removal",
        )

    words = text.lower().split()
    scores: Dict[str, float] = {intent: 0.0 for intent in INTENTS}
    matches: Dict[str, List[str]] = {intent: [] for intent in INTENTS}

    # ── Learned keywords (weight 2.0) — checked FIRST ──
    if learned_keywords:
        for word in words:
            if word in learned_keywords:
                intent = learned_keywords[word]
                if intent in scores:
                    scores[intent] += LEARNED_KEYWORD_WEIGHT
                    matches[intent].append(f"learned:{word}")

    # ── Phrase matching (weight 1.5) — phrases beat single words ──
    for intent_name, meta in INTENTS.items():
        if intent_name == "others":
            continue
        for phrase in meta.phrases:
            if phrase in text.lower():
                scores[intent_name] += PHRASE_WEIGHT
                matches[intent_name].append(f"phrase:{phrase}")

    # ── Exact keyword matching (weight 1.0) ──
    for word in words:
        for intent_name, meta in INTENTS.items():
            if intent_name == "others":
                continue
            if word in meta.keywords:
                scores[intent_name] += EXACT_KEYWORD_WEIGHT
                matches[intent_name].append(f"exact:{word}")

    # ── Fuzzy matching (weight 0.6) — only if no exact hit for this word ──
    for word in words:
        if word in STOPWORDS or len(word) < 3:
            continue
        # Skip if this word already matched something exactly
        already_matched = False
        for intent_name, meta in INTENTS.items():
            if word in meta.keywords:
                already_matched = True
                break
        if already_matched:
            continue

        best_fuzzy_intent = None
        best_fuzzy_score = 0.0
        best_fuzzy_kw = ""
        for intent_name, meta in INTENTS.items():
            if intent_name == "others":
                continue
            for kw in meta.keywords:
                score = _fuzzy_score(word, kw)
                if score > best_fuzzy_score:
                    best_fuzzy_score = score
                    best_fuzzy_intent = intent_name
                    best_fuzzy_kw = kw

        if best_fuzzy_intent and best_fuzzy_score >= FUZZY_MIN_RATIO:
            scores[best_fuzzy_intent] += FUZZY_WEIGHT
            matches[best_fuzzy_intent].append(
                f"fuzzy:{word}~{best_fuzzy_kw}({best_fuzzy_score:.2f})"
            )

    # ── Normalise scores to 0..1 ──
    max_score = max(scores.values()) if scores else 0.0
    if max_score <= 0:
        return IntentResult(
            intent="others",
            confidence=0.0,
            matched_keywords=[],
            reason="No keyword matches found in any intent",
        )

    confidences = {
        intent: score / max_score for intent, score in scores.items()
    }

    # ── Sort by confidence, then by priority order on ties ──
    def sort_key(item: Tuple[str, float]) -> Tuple[float, int]:
        intent, conf = item
        # Lower priority index = higher priority = should come first
        try:
            priority = PRIORITY_ORDER.index(intent)
        except ValueError:
            priority = len(PRIORITY_ORDER)  # "others" goes last
        return (-conf, priority)

    ranked = sorted(confidences.items(), key=sort_key)
    top_intent, top_conf = ranked[0]

    # ── Check confidence threshold ──
    if scores[top_intent] < CONFIDENCE_THRESHOLD:
        return IntentResult(
            intent="others",
            confidence=top_conf,
            matched_keywords=matches.get(top_intent, []),
            reason=f"Top score {scores[top_intent]:.2f} below threshold {CONFIDENCE_THRESHOLD}",
        )

    # ── Check for ties within margin ──
    if len(ranked) >= 2:
        second_intent, second_conf = ranked[1]
        if top_conf - second_conf <= TIE_MARGIN and second_conf > 0:
            return IntentResult(
                intent="others",
                confidence=top_conf,
                matched_keywords=matches.get(top_intent, []),
                reason=(
                    f"Tie between '{top_intent}' ({top_conf:.2f}) and "
                    f"'{second_intent}' ({second_conf:.2f}), margin {TIE_MARGIN}"
                ),
            )

    return IntentResult(
        intent=top_intent,
        confidence=top_conf,
        matched_keywords=matches.get(top_intent, []),
        reason=f"Best match: {top_intent} (raw score {scores[top_intent]:.2f})",
    )


# ═══════════════════════════════════════════════
# 5. BUILD DESCRIPTION
# ═══════════════════════════════════════════════
def build_description(original_text: str, amount: Optional[Decimal] = None) -> str:
    """Build the user-facing description from the original text.

    Removes amount tokens but preserves the user's own words.
    First letter capitalised. Never returns a generic label.
    """
    desc = original_text.strip()

    # Remove amount-related tokens using patterns
    for pattern in AMOUNT_PATTERNS_FOR_CLEANUP:
        desc = re.sub(pattern, " ", desc, flags=re.IGNORECASE)

    # Remove shorthand tokens
    desc = re.sub(r"\brs\.?\b", " ", desc, flags=re.IGNORECASE)
    desc = re.sub(r"₹", " ", desc)
    desc = re.sub(r"/\s*-", " ", desc)
    desc = re.sub(r"\binr\b", " ", desc, flags=re.IGNORECASE)
    desc = re.sub(r"\brupees?\b", " ", desc, flags=re.IGNORECASE)

    # Remove date-related tokens
    for kw in ["today", "yesterday", "ystd", "ytd"]:
        desc = re.sub(rf"\b{kw}\b", " ", desc, flags=re.IGNORECASE)
    # Remove date patterns like 1/9, 01-09-2026
    desc = re.sub(r"\b\d{1,2}[/\-]\d{1,2}(?:[/\-]\d{2,4})?\b", " ", desc)

    # Collapse whitespace and trim
    desc = re.sub(r"\s+", " ", desc).strip()

    # Remove leading/trailing common filler
    desc = re.sub(r"^(and|for|on|at|in|the|a|an)\s+", "", desc, flags=re.IGNORECASE)
    desc = re.sub(r"\s+(and|for|on|at|in|the|a|an)$", "", desc, flags=re.IGNORECASE)

    # Capitalise first letter
    if desc:
        desc = desc[0].upper() + desc[1:]

    return desc


# ═══════════════════════════════════════════════
# FULL PARSE PIPELINE
# ═══════════════════════════════════════════════
def parse_expense(
    raw_text: str,
    learned_keywords: Optional[Dict[str, str]] = None,
) -> ParseResult:
    """Full pipeline: normalize -> extract_amount -> extract_date -> classify
    -> build_description.

    Raises ValueError if no amount found.
    """
    # Step 1: Normalize
    normalized = normalize(raw_text)

    # Step 2: Extract amount
    amount, leftover = extract_amount(normalized)
    if amount is None:
        raise ValueError("No amount found. Please include how much you spent (e.g. 'tea 20').")

    # Step 3: Extract date
    spent_on, leftover = extract_date(leftover)

    # Step 4: Classify
    result = classify(leftover, learned_keywords=learned_keywords)

    # Step 5: Build description from ORIGINAL text
    description = build_description(raw_text, amount)

    # Validate: for purchase and others, description must not be empty
    if result.intent in ("purchase", "others") and not description:
        raise ValueError(
            "Please add a description of what you spent on "
            "(e.g. 'bought phone charger 399')."
        )

    return ParseResult(
        amount=amount,
        intent=result.intent,
        confidence=result.confidence,
        description=description,
        spent_on=spent_on,
        matched_keywords=result.matched_keywords,
        reason=result.reason,
    )


# ═══════════════════════════════════════════════
# LEARNING HELPERS
# ═══════════════════════════════════════════════
def extract_learnable_tokens(description: str) -> List[str]:
    """Extract meaningful tokens from a description for learning.
    Removes stopwords and very short tokens."""
    words = re.sub(r"[^\w\s]", " ", description.lower()).split()
    tokens = []
    for w in words:
        if w in STOPWORDS:
            continue
        if len(w) < 2:
            continue
        # Skip pure numbers
        if re.match(r"^\d+$", w):
            continue
        tokens.append(w)
    return tokens
