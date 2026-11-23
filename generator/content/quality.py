"""Checking a written presentation against the writing rules, without asking any AI.

Every check is plain Python, so it is instant, free and gives the same result every time.
The findings are used twice: they are shown to the user, and they are given back to the
model in a second pass that fixes them (see prompt.build_review_prompt).

check_deck() returns a list of Issue objects. An Issue has a code (the interface turns it
into a sentence in the user's language), the slide it is about, values for the message,
and an English description for the model.
"""
import re
from dataclasses import dataclass, field

from generator.content.presets import TEXT_AMOUNT_PRESETS

# Phrases that sound like content but say nothing (English and Russian).
FILLER = [
    "in today's world", "in today's fast-paced", "in the modern world", "it is important to note",
    "it's important to note", "it is worth noting", "it's worth noting", "plays a key role",
    "plays a crucial role", "plays an important role", "a wide range of", "in conclusion", "needless to say",
    "last but not least", "game-changer", "game changer", "unlock the potential", "cutting-edge",
    "в современном мире", "в наше время", "на сегодняшний день", "в настоящее время", "важно отметить",
    "стоит отметить", "следует отметить", "необходимо отметить", "играет ключевую роль", "играет важную роль",
    "играет огромную роль", "широкий спектр", "широкий круг", "в заключение", "не секрет, что",
    "как известно", "неотъемлемой частью", "неотъемлемая часть",
]
# Slide types whose title should state a takeaway, not just name a topic.
POINT_TYPES = {"bullets", "two_columns", "cards", "stats", "chart", "timeline", "table", "image"}
WORD = re.compile(r"[\w%$€£№]+", re.UNICODE)


@dataclass
class Issue:
    code: str
    slide: int | None        # index in deck.slides, or None for the whole deck
    values: dict = field(default_factory=dict)
    detail: str = ""            # English, for the model


def words(text):
    return WORD.findall(str(text or ""))


def slide_texts(slide):
    """All visible texts of a slide, as a list of strings."""
    texts = [slide.title, slide.subtitle or "", slide.quote or ""]
    texts += slide.bullets or []
    for column in slide.columns or []:
        texts += [column.heading] + column.bullets
    for card in slide.cards or []:
        texts += [card.heading, card.text]
    for stat in slide.stats or []:
        texts += [stat.value, stat.label]
    for step in slide.steps or []:
        texts += [step.label, step.text]
    if slide.table:
        texts += slide.table.headers + [cell for row in slide.table.rows for cell in row.cells]
    return [t for t in texts if t]


def _item_texts(slide):
    """The smaller text blocks that have a per-item word limit."""
    items = [card.text for card in slide.cards or []] + [step.text for step in slide.steps or []]
    items += [bullet for column in slide.columns or [] for bullet in column.bullets]
    return items


def _cyrillic_share(text):
    letters = [ch for ch in text if ch.isalpha()]
    return sum("а" <= ch.lower() <= "я" or ch.lower() == "ё" for ch in letters) / len(letters) if letters else None


def _similar(a, b):
    """True when two points say nearly the same thing (by shared words)."""
    wa, wb = {w.lower() for w in words(a) if len(w) > 3}, {w.lower() for w in words(b) if len(w) > 3}
    if len(wa) < 4 or len(wb) < 4:
        return False
    return len(wa & wb) / len(wa | wb) >= 0.6


def check_deck(deck, text_amount="Balanced", speaker_notes=True):
    """All findings for a deck, in slide order."""
    amount = TEXT_AMOUNT_PRESETS.get(text_amount, TEXT_AMOUNT_PRESETS["Balanced"])
    issues = []
    deck_share = _cyrillic_share(" ".join([deck.title, deck.subtitle] + [s.title for s in deck.slides]))

    for i, slide in enumerate(deck.slides):
        title_words = len(words(slide.title))
        if slide.type in POINT_TYPES and title_words <= 2:
            issues.append(Issue("title_label", i, {"title": slide.title},
                                f'the title "{slide.title}" names a topic; '
                                "state the slide's takeaway as a short sentence"))
        if title_words > 14:
            issues.append(Issue("title_long", i, {"words": title_words},
                                f"the title has {title_words} words; keep it under 13"))

        if slide.type == "bullets" and slide.bullets:
            total = sum(len(words(b)) for b in slide.bullets)
            if total > amount["max_words"] * 1.15:
                issues.append(Issue("too_much_text", i, {"words": total, "limit": amount["max_words"]},
                                    f"{total} words in bullets; the limit is {amount['max_words']}"))
        long_items = [t for t in _item_texts(slide) if len(words(t)) > amount["item_words"] * 1.5]
        if long_items:
            issues.append(Issue("long_items", i, {"count": len(long_items), "limit": amount["item_words"]},
                                f"{len(long_items)} card/column/step texts are longer than "
                                f"{amount['item_words']} words"))

        text = " ".join(slide_texts(slide)).lower()
        for phrase in FILLER:
            if phrase in text:
                issues.append(Issue("filler", i, {"phrase": phrase}, f'remove the filler phrase "{phrase}"'))
                break

        for stat in slide.stats or []:
            if not re.search(r"\d", stat.value):
                issues.append(Issue("stat_without_number", i, {"value": stat.value},
                                    f'the figure "{stat.value}" contains no number'))
                break

        share = _cyrillic_share(" ".join(slide_texts(slide)))
        if deck_share is not None and share is not None and abs(share - deck_share) > 0.6:
            issues.append(Issue("language_mix", i, {},
                                "this slide is written in a different language than the rest of the deck"))

    # points repeated on two different slides
    seen = []
    for i, slide in enumerate(deck.slides):
        for point in (slide.bullets or []) + [c.text for c in slide.cards or []]:
            for j, other in seen:
                if j != i and _similar(point, other):
                    issues.append(Issue("repeat", i, {"other": j + 2},
                                        f"a point repeats what slide {j + 2} already says: \"{point[:60]}\""))
                    break
            else:
                seen.append((i, point))
                continue
            break

    # three slides of the same type in a row
    for i in range(2, len(deck.slides)):
        kinds = {deck.slides[k].type for k in (i - 2, i - 1, i)}
        if len(kinds) == 1 and deck.slides[i].type not in ("section",):
            issues.append(Issue("same_type_run", i, {"type": deck.slides[i].type},
                                f'three "{deck.slides[i].type}" slides in a row; vary the slide types'))

    if len(deck.slides) >= 4 and deck.slides[-1].type != "closing":
        issues.append(Issue("no_closing", None, {}, 'the last slide should be a "closing" slide with takeaways'))
    if speaker_notes:
        missing = [i + 2 for i, s in enumerate(deck.slides) if not s.notes]
        if missing:
            issues.append(Issue("missing_notes", None, {"slides": ", ".join(map(str, missing))},
                                f"speaker notes are missing on slides {', '.join(map(str, missing))}"))
    issues.sort(key=lambda issue: (issue.slide is None, issue.slide or 0))
    return issues


def score(issues):
    """A rough quality score from 0 to 100 for the interface: fewer and lighter findings, higher score."""
    weights = {"title_label": 4, "filler": 4, "repeat": 6, "language_mix": 8, "too_much_text": 5,
               "long_items": 3, "stat_without_number": 4, "same_type_run": 3, "no_closing": 4,
               "missing_notes": 3, "title_long": 2}
    return max(0, 100 - sum(weights.get(issue.code, 3) for issue in issues))


def describe_for_model(issues):
    """The findings as a numbered list for the review prompt."""
    lines = []
    for n, issue in enumerate(issues, 1):
        where = f"slide {issue.slide + 2}" if issue.slide is not None else "whole presentation"
        lines.append(f"{n}. {where}: {issue.detail}")
    return "\n".join(lines)
