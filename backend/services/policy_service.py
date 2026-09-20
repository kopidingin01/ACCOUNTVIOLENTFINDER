from sqlalchemy.orm import Session

from models.enums import ViolationCategory
from models.policy import Policy, PolicyRule


def get_rules_for_platform(db: Session, platform_id: str) -> list[PolicyRule]:
    return (
        db.query(PolicyRule)
        .join(Policy, PolicyRule.policy_id == Policy.id)
        .filter(Policy.platform_id == platform_id)
        .all()
    )


def triage_by_keyword(text: str, rules: list[PolicyRule]) -> list[tuple[PolicyRule, list[str]]]:
    """Keyword matching for TRIAGE ONLY. A keyword hit is a hint to look
    closer at a piece of content with a human/context-aware review — it is
    never treated as a violation decision on its own (see POLICY_ENGINE.md).
    """
    if not text:
        return []
    lowered = text.lower()
    hits: list[tuple[PolicyRule, list[str]]] = []
    for rule in rules:
        if not rule.keywords:
            continue
        matched = [kw.strip() for kw in rule.keywords.split(",") if kw.strip() and kw.strip().lower() in lowered]
        if matched:
            hits.append((rule, matched))
    return hits


def category_display(category: ViolationCategory) -> str:
    return category.value.replace("_", " ").title()
