"""Numerical, monetary, quantity, and temporal value extraction."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from dateutil import parser as date_parser

from app.core.logging import get_logger

logger = get_logger(__name__)

MULTIPLIERS = {
    "thousand": 1_000.0,
    "k": 1_000.0,
    "million": 1_000_000.0,
    "millions": 1_000_000.0,
    "m": 1_000_000.0,
    "mn": 1_000_000.0,
    "billion": 1_000_000_000.0,
    "billions": 1_000_000_000.0,
    "b": 1_000_000_000.0,
    "bn": 1_000_000_000.0,
    "crore": 10_000_000.0,
    "crores": 10_000_000.0,
    "cr": 10_000_000.0,
    "lakh": 100_000.0,
    "lakhs": 100_000.0,
    "lac": 100_000.0,
}

CURRENCY_SYMBOLS = {
    "$": "USD",
    "usd": "USD",
    "₹": "INR",
    "inr": "INR",
    "rs": "INR",
    "€": "EUR",
    "eur": "EUR",
    "£": "GBP",
    "gbp": "GBP",
}

UNIT_WORDS = {
    "kg": "kg",
    "kilogram": "kg",
    "kilograms": "kg",
    "g": "g",
    "employee": "employees",
    "employees": "employees",
    "people": "employees",
    "person": "employees",
    "staff": "employees",
    "percent": "%",
    "percentage": "%",
}

_NUMBER_TOKEN = r"(?:\d{1,3}(?:,\d{2,3})+|\d+(?:\.\d+)?)"
_MULTIPLIER = r"(?:thousand|million|millions|billion|billions|crore|crores|lakh|lakhs|lac|mn|bn|cr|[kKmMbB])"
_CURRENCY = r"(?:USD|INR|EUR|GBP|Rs\.?|₹|\$|€|£)"
_UNIT = r"(?:kg|kilograms?|employees?|people|persons?|staff|grams?)"

MONEY_RE = re.compile(
    rf"(?P<currency_pre>{_CURRENCY})?\s*"
    rf"(?P<number>{_NUMBER_TOKEN})\s*"
    rf"(?P<multiplier>(?:{_MULTIPLIER})(?![A-Za-z]))?\s*"
    rf"(?P<currency_post>{_CURRENCY})?",
    re.IGNORECASE,
)
PERCENT_RE = re.compile(rf"(?P<number>{_NUMBER_TOKEN})\s*(?P<unit>%|percent|percentage)(?![A-Za-z])", re.IGNORECASE)
QUANTITY_RE = re.compile(rf"(?P<number>{_NUMBER_TOKEN})\s*(?P<unit>{_UNIT})\b", re.IGNORECASE)
BARE_NUMBER_RE = re.compile(rf"(?<![A-Za-z])(?P<number>{_NUMBER_TOKEN})(?![A-Za-z%])")

ISO_DATE_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
SLASH_DATE_RE = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b")
QUARTER_RE = re.compile(r"\bQ([1-4])\s*(?:of\s*)?(\d{4})\b", re.IGNORECASE)
MONTH_YEAR_RE = re.compile(
    r"\b("
    r"January|February|March|April|May|June|July|August|September|October|November|December|"
    r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
    r")\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?:,)?\s+(\d{4})\b",
    re.IGNORECASE,
)
DAY_MONTH_YEAR_RE = re.compile(
    r"\b(\d{1,2})(?:st|nd|rd|th)?\s+("
    r"January|February|March|April|May|June|July|August|September|October|November|December|"
    r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
    r")\.?,?\s+(\d{4})\b",
    re.IGNORECASE,
)
MONTH_ONLY_RE = re.compile(
    r"\b("
    r"January|February|March|April|May|June|July|August|September|October|November|December|"
    r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
    r")\.?\s+(\d{4})\b",
    re.IGNORECASE,
)


@dataclass
class ExtractedValue:
    raw_text: str
    numeric_value: Optional[float]
    unit: Optional[str] = None
    currency: Optional[str] = None
    percentage: bool = False
    normalized_value: Optional[float] = None
    start: int = 0
    end: int = 0

    @property
    def comparable_key(self) -> tuple:
        if self.percentage:
            return ("percent",)
        if self.currency:
            return ("money", self.currency)
        if self.unit:
            return ("unit", self.unit)
        return ("number",)


@dataclass
class ExtractedDate:
    raw_text: str
    iso_date: Optional[str]
    parsed: Optional[date]
    precision: str = "day"
    start: int = 0
    end: int = 0


@dataclass
class ValueDelta:
    old: ExtractedValue
    new: ExtractedValue
    absolute_change: Optional[float]
    percentage_change: Optional[float]


@dataclass
class DateDelta:
    old: ExtractedDate
    new: ExtractedDate
    days_changed: Optional[int]


class ValueExtractor:
    """Extract and compare numeric and temporal values in sentence text."""

    def extract_values(self, text: str) -> list[ExtractedValue]:
        values: list[ExtractedValue] = []
        occupied: list[tuple[int, int]] = [
            (item.start, item.end) for item in self.extract_dates(text)
        ]

        for match in PERCENT_RE.finditer(text):
            number = _parse_number(match.group("number"))
            values.append(
                ExtractedValue(
                    raw_text=match.group(0).strip(),
                    numeric_value=number,
                    unit="%",
                    percentage=True,
                    normalized_value=number,
                    start=match.start(),
                    end=match.end(),
                )
            )
            occupied.append((match.start(), match.end()))

        for match in MONEY_RE.finditer(text):
            if _overlaps(match.start(), match.end(), occupied):
                continue
            currency = _normalize_currency(match.group("currency_pre") or match.group("currency_post"))
            multiplier_raw = match.group("multiplier")
            # Bare numbers without currency or scale are handled later.
            if not currency and not multiplier_raw:
                continue
            number = _parse_number(match.group("number"))
            multiplier = _multiplier(multiplier_raw)
            normalized = None if number is None else number * multiplier
            values.append(
                ExtractedValue(
                    raw_text=match.group(0).strip(),
                    numeric_value=number,
                    unit=currency,
                    currency=currency,
                    normalized_value=normalized,
                    start=match.start(),
                    end=match.end(),
                )
            )
            occupied.append((match.start(), match.end()))

        for match in QUANTITY_RE.finditer(text):
            if _overlaps(match.start(), match.end(), occupied):
                continue
            number = _parse_number(match.group("number"))
            unit = UNIT_WORDS.get(match.group("unit").lower(), match.group("unit").lower())
            values.append(
                ExtractedValue(
                    raw_text=match.group(0).strip(),
                    numeric_value=number,
                    unit=unit,
                    normalized_value=number,
                    start=match.start(),
                    end=match.end(),
                )
            )
            occupied.append((match.start(), match.end()))

        for match in BARE_NUMBER_RE.finditer(text):
            if _overlaps(match.start(), match.end(), occupied):
                continue
            number = _parse_number(match.group("number"))
            values.append(
                ExtractedValue(
                    raw_text=match.group(0).strip(),
                    numeric_value=number,
                    normalized_value=number,
                    start=match.start(),
                    end=match.end(),
                )
            )
            occupied.append((match.start(), match.end()))

        return values

    def extract_dates(self, text: str) -> list[ExtractedDate]:
        dates: list[ExtractedDate] = []
        occupied: list[tuple[int, int]] = []

        for match in ISO_DATE_RE.finditer(text):
            parsed = _safe_date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            dates.append(_date_from_parsed(match.group(0), parsed, "day", match.start(), match.end()))
            occupied.append((match.start(), match.end()))

        for match in MONTH_YEAR_RE.finditer(text):
            parsed = _parse_flexible(match.group(0))
            dates.append(_date_from_parsed(match.group(0), parsed, "day", match.start(), match.end()))
            occupied.append((match.start(), match.end()))

        for match in DAY_MONTH_YEAR_RE.finditer(text):
            if _overlaps(match.start(), match.end(), occupied):
                continue
            parsed = _parse_flexible(match.group(0), dayfirst=True)
            dates.append(_date_from_parsed(match.group(0), parsed, "day", match.start(), match.end()))
            occupied.append((match.start(), match.end()))

        for match in QUARTER_RE.finditer(text):
            if _overlaps(match.start(), match.end(), occupied):
                continue
            quarter = int(match.group(1))
            year = int(match.group(2))
            month = 1 + (quarter - 1) * 3
            parsed = date(year, month, 1)
            dates.append(_date_from_parsed(match.group(0), parsed, "quarter", match.start(), match.end()))
            occupied.append((match.start(), match.end()))

        for match in MONTH_ONLY_RE.finditer(text):
            if _overlaps(match.start(), match.end(), occupied):
                continue
            parsed = _parse_flexible(f"1 {match.group(0)}")
            dates.append(_date_from_parsed(match.group(0), parsed, "month", match.start(), match.end()))
            occupied.append((match.start(), match.end()))

        for match in SLASH_DATE_RE.finditer(text):
            if _overlaps(match.start(), match.end(), occupied):
                continue
            parsed = _parse_flexible(match.group(0), dayfirst=True)
            dates.append(_date_from_parsed(match.group(0), parsed, "day", match.start(), match.end()))
            occupied.append((match.start(), match.end()))

        return dates

    def compare_values(
        self,
        old_values: list[ExtractedValue],
        new_values: list[ExtractedValue],
    ) -> list[ValueDelta]:
        deltas: list[ValueDelta] = []
        used_new: set[int] = set()
        for old in old_values:
            best_index = None
            for index, new in enumerate(new_values):
                if index in used_new:
                    continue
                if old.comparable_key != new.comparable_key:
                    continue
                best_index = index
                break
            if best_index is None:
                continue
            new = new_values[best_index]
            used_new.add(best_index)
            old_norm = old.normalized_value
            new_norm = new.normalized_value
            if old_norm is None or new_norm is None:
                continue
            if abs(old_norm - new_norm) < 1e-9:
                continue
            absolute = new_norm - old_norm
            percent = None if abs(old_norm) < 1e-12 else (absolute / abs(old_norm)) * 100.0
            deltas.append(
                ValueDelta(
                    old=old,
                    new=new,
                    absolute_change=absolute,
                    percentage_change=percent,
                )
            )
        return deltas

    def compare_dates(
        self,
        old_dates: list[ExtractedDate],
        new_dates: list[ExtractedDate],
    ) -> list[DateDelta]:
        deltas: list[DateDelta] = []
        used_new: set[int] = set()
        for old in old_dates:
            if old.parsed is None:
                continue
            best_index = None
            for index, new in enumerate(new_dates):
                if index in used_new or new.parsed is None:
                    continue
                best_index = index
                break
            if best_index is None:
                continue
            new = new_dates[best_index]
            used_new.add(best_index)
            if old.parsed == new.parsed:
                continue
            days = (new.parsed - old.parsed).days
            deltas.append(DateDelta(old=old, new=new, days_changed=days))
        return deltas


def _parse_number(raw: str) -> Optional[float]:
    try:
        return float(raw.replace(",", ""))
    except (TypeError, ValueError):
        return None


def _multiplier(raw: str | None) -> float:
    if not raw:
        return 1.0
    return MULTIPLIERS.get(raw.lower(), 1.0)


def _normalize_currency(raw: str | None) -> Optional[str]:
    if not raw:
        return None
    cleaned = raw.strip().rstrip(".").lower()
    if cleaned in CURRENCY_SYMBOLS:
        return CURRENCY_SYMBOLS[cleaned]
    if raw.strip() in CURRENCY_SYMBOLS:
        return CURRENCY_SYMBOLS[raw.strip()]
    return cleaned.upper()


def _overlaps(start: int, end: int, occupied: list[tuple[int, int]]) -> bool:
    for left, right in occupied:
        if start < right and end > left:
            return True
    return False


def _safe_date(year: int, month: int, day: int) -> Optional[date]:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _parse_flexible(text: str, dayfirst: bool = False) -> Optional[date]:
    try:
        parsed = date_parser.parse(text, dayfirst=dayfirst, fuzzy=True, default=datetime(2000, 1, 1))
        return parsed.date()
    except (ValueError, OverflowError, TypeError):
        return None


def _date_from_parsed(
    raw: str,
    parsed: Optional[date],
    precision: str,
    start: int,
    end: int,
) -> ExtractedDate:
    return ExtractedDate(
        raw_text=raw,
        iso_date=parsed.isoformat() if parsed else None,
        parsed=parsed,
        precision=precision,
        start=start,
        end=end,
    )
