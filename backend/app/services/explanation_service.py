"""Deterministic human-readable explanations for classified changes."""

from __future__ import annotations

from app.models.change import Change, ChangeType


class ExplanationService:
    """Generate template explanations. LLM generation can be added behind this interface."""

    def explain(self, change: Change) -> str:
        """Return an explanation and store it on the change."""
        explanation = self._build(change)
        change.explanation = explanation
        return explanation

    def explain_all(self, changes: list[Change]) -> list[Change]:
        for change in changes:
            self.explain(change)
        return changes

    def _build(self, change: Change) -> str:
        details = change.details or {}
        if change.type == ChangeType.ADDITION:
            return f"A new statement was added: {change.new_text}"
        if change.type == ChangeType.DELETION:
            return f"A statement was removed: {change.old_text}"
        if change.type == ChangeType.UNCHANGED:
            if change.old_text and change.new_text and change.old_text.strip() != change.new_text.strip():
                return "The wording changed but the meaning is the same."
            return "The statement is unchanged between document versions."
        if change.type == ChangeType.NUMERICAL_CHANGE:
            return _numerical_explanation(change, details)
        if change.type == ChangeType.TEMPORAL_CHANGE:
            return _temporal_explanation(details)
        if change.type == ChangeType.ENTITY_CHANGE:
            old_entity = details.get("old_entity")
            new_entity = details.get("new_entity")
            label = (details.get("label") or "entity").lower()
            if old_entity and new_entity:
                if label == "org":
                    return f"The organization changed from {old_entity} to {new_entity}."
                if label in {"gpe", "loc"}:
                    return f"The location changed from {old_entity} to {new_entity}."
                if label == "person":
                    return f"The person changed from {old_entity} to {new_entity}."
                return f"The {label} changed from {old_entity} to {new_entity}."
            return "An important named entity changed between the two versions."
        if change.type == ChangeType.CONTRADICTION:
            topic = _topic_hint(change)
            if topic:
                return f"The new version contradicts the previous statement about {topic}."
            return "The new version contradicts the previous statement."
        if change.type == ChangeType.REFINEMENT:
            return (
                "The new version keeps the previous meaning and adds more specific information: "
                f"{change.new_text}"
            )
        if change.old_text and change.new_text:
            return "The statement was modified between document versions."
        return "A semantic change was detected."


def _numerical_explanation(change: Change, details: dict) -> str:
    entity = details.get("entity") or "The value"
    old_raw = details.get("old_raw") or change.old_text
    new_raw = details.get("new_raw") or change.new_text
    old_value = details.get("old_value")
    new_value = details.get("new_value")
    percent = details.get("percentage_change")
    if isinstance(old_value, (int, float)) and isinstance(new_value, (int, float)):
        direction = "increased" if new_value > old_value else "decreased"
        if percent is None:
            return f"{_title(entity)} {direction} from {old_raw} to {new_raw}."
        noun = "increase" if new_value > old_value else "decrease"
        return (
            f"{_title(entity)} {direction} from {old_raw} to {new_raw} "
            f"({abs(percent):.1f}% {noun})."
        )
    return f"{_title(entity)} changed from {old_raw} to {new_raw}."


def _temporal_explanation(details: dict) -> str:
    old_raw = details.get("old_date_raw") or details.get("old_date")
    new_raw = details.get("new_date_raw") or details.get("new_date")
    days = details.get("days_changed")
    if isinstance(days, int):
        if days > 0:
            delay = f"a delay of {days} days"
        elif days < 0:
            delay = f"{abs(days)} days earlier"
        else:
            delay = "no day difference"
        return f"The project deadline moved from {old_raw} to {new_raw}, {delay}."
    return f"The date changed from {old_raw} to {new_raw}."


def _topic_hint(change: Change) -> str | None:
    text = " ".join(filter(None, [change.old_text, change.new_text])).lower()
    if "weekend" in text:
        return "weekend availability"
    if "office" in text:
        return "office hours"
    if "available" in text or "availability" in text:
        return "availability"
    return None


def _title(entity: str) -> str:
    if not entity:
        return "The value"
    if entity[:1].isupper():
        return entity
    return entity[:1].upper() + entity[1:]
