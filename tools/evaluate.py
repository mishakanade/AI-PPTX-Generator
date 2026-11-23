"""Developer tool: is the app better than simply asking an AI chat for a presentation?

For every topic the same model writes two presentations:

  plain  - what you get by typing "make a presentation about X" into a chat: a short request
           for slide titles and bullet points, nothing else;
  app    - the app's way: the purpose and audience, the storyline and writing rules, the
           slide types, then the editor's pass on what the automatic check found.

Both are then compared in two ways:

  1. The app's own automatic check (generator/content/quality.py): score, findings, and a
     few plain counts (slide types used, slides with a number, words per slide). Cheap, but
     the app's prompts are written to pass exactly these checks, so it favours the app.
  2. A judge: a model (another provider is best) sees both presentations as "A" and "B",
     without knowing which is which, and scores them on criteria a real audience cares about.
     Every pair is judged twice with A and B swapped, because judges tend to prefer one side.

Needs an API key for the chosen provider (in .env, as for the app). A run costs about five
requests per topic, two more with the judge. Run from the project folder:

    python tools/evaluate.py                              Gemini, the built-in topics
    python tools/evaluate.py --provider claude --judge-provider openai
    python tools/evaluate.py --topics my_topics.txt --slides 8 --pptx

The report goes to evaluation/report.md (not tracked by git), the presentations next to it.
"""
import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pydantic import BaseModel, Field, ValidationError  # noqa: E402

from generator.content import llm  # noqa: E402
from generator.content.prompt import build_prompt, build_review_prompt  # noqa: E402
from generator.content.quality import check_deck, describe_for_model, score, slide_texts, words  # noqa: E402
from generator.content.schema import ContentError  # noqa: E402

# (topic, purpose of the talk, audience); a topics file has one topic per line, or
# "topic | purpose | audience"
TOPICS = [
    ("The future of urban mobility", "inform", "city council members"),
    ("Why our startup should adopt a four-day work week", "persuade", "the company's founders"),
    ("How vaccines train the immune system", "teach", "high-school students"),
    ("Quarterly results of an online bookshop", "report", "the management team"),
    ("A mobile app that matches volunteers with local charities", "pitch", "seed investors"),
    ("Влияние искусственного интеллекта на рынок труда", "inform", "студенты экономического вуза"),
    ("Переход офиса на возобновляемую энергию", "persuade", "совет директоров"),
    ("История освоения космоса", "teach", "школьники 8 класса"),
]
TONE, AMOUNT = "💼 Professional", "Balanced"

PLAIN_PROMPT = """Make a presentation about "{topic}" with {slides} slides.
Write it in the language of the topic.
Answer only with JSON:
{{"title": "...", "subtitle": "...", "slides": [{{"title": "...", "bullets": ["...", "..."]}}]}}"""

CRITERIA = {
    "message": "Is there one clear main message, and does every slide serve it?",
    "storyline": "Do the slides build a logical story for this purpose, from start to conclusion?",
    "specifics": "Concrete facts, numbers and examples instead of vague general statements",
    "audience": "Does it fit this audience and this purpose?",
    "slide_design": "Would each slide work on screen: little text, varied and fitting slide types?",
}
JUDGE_PROMPT = """You are an experienced presentation coach. Two presentations were written for the same request.
Judge them as the audience would experience them. Do not prefer the longer one for its length.

REQUEST: a presentation about "{topic}", purpose: {goal}, audience: {audience}.

Score each presentation from 1 (poor) to 5 (excellent) on every criterion:
{criteria}

Then say which one you would rather present: "A", "B" or "tie".

<presentation_a>
{a}
</presentation_a>

<presentation_b>
{b}
</presentation_b>

Answer only with JSON in this form:
{{"a": {{{example}}}, "b": {{{example}}}, "better": "A", "why": "one or two sentences"}}"""


class Scores(BaseModel):
    message: int = Field(ge=1, le=5)
    storyline: int = Field(ge=1, le=5)
    specifics: int = Field(ge=1, le=5)
    audience: int = Field(ge=1, le=5)
    slide_design: int = Field(ge=1, le=5)


class Verdict(BaseModel):
    a: Scores
    b: Scores
    better: str
    why: str = ""


def parse_verdict(raw):
    match = re.search(r"\{.*\}", raw or "", re.DOTALL)
    try:
        verdict = Verdict.model_validate_json(match.group(0) if match else raw or "")
    except ValidationError as e:
        raise ContentError("The judge's answer is not in the expected form.") from e
    verdict.better = verdict.better.strip().upper() if verdict.better.strip().upper() in ("A", "B") else "TIE"
    return verdict


def deck_as_text(deck):
    """A presentation as plain text for the judge: slide type, title, and everything on the slide."""
    lines = [f"Title: {deck.title}", f"Subtitle: {deck.subtitle}"]
    for n, slide in enumerate(deck.slides, 2):
        lines.append(f"\nSlide {n} [{slide.type}]: {slide.title}")
        lines += [f"  - {text}" for text in slide_texts(slide) if text != slide.title]
    return "\n".join(lines)


@dataclass
class Side:
    deck: object
    score: int
    findings: list
    judge: dict = field(default_factory=dict)       # criterion -> average score


def counts(deck):
    slides = deck.slides
    with_number = sum(any(ch.isdigit() for ch in " ".join(slide_texts(s)[1:])) for s in slides)
    body_words = [len(words(" ".join(slide_texts(s)[1:]))) for s in slides]
    return {"types": len({s.type for s in slides}), "with_number": with_number,
            "words": round(sum(body_words) / max(1, len(body_words)))}


def write_plain(topic, slides, conn):
    return llm.generate_deck(PLAIN_PROMPT.format(topic=topic, slides=slides), max_slides=slides, **conn)


def write_app(topic, goal, audience, slides, conn):
    """The app's own way, as interface/generation.py does it (without photos)."""
    prompt = build_prompt(topic, "", TONE, AMOUNT, "", slides, goal=goal, audience=audience)
    deck = llm.generate_deck(prompt, max_slides=slides, **conn)
    issues = check_deck(deck, AMOUNT)
    if issues:
        review = build_review_prompt(deck, describe_for_model(issues), TONE, AMOUNT, goal=goal, audience=audience)
        deck = llm.review_deck(deck, review, AMOUNT, **conn)
    return deck


def judge(topic, goal, audience, plain, app, conn):
    """Both orders; returns (plain's scores, app's scores, app's result: +1 better, -1 worse, 0 tie)."""
    criteria = "\n".join(f"- {key}: {text}" for key, text in CRITERIA.items())
    example = ", ".join(f'"{key}": 3' for key in CRITERIA)
    totals = {"plain": {k: 0 for k in CRITERIA}, "app": {k: 0 for k in CRITERIA}}
    result = 0
    for app_is_a in (True, False):
        a, b = (app, plain) if app_is_a else (plain, app)
        prompt = JUDGE_PROMPT.format(topic=topic, goal=goal, audience=audience or "general", criteria=criteria,
                                     example=example, a=deck_as_text(a), b=deck_as_text(b))
        verdict = llm.ask(prompt, Verdict, parse_verdict, **conn)
        app_scores, plain_scores = (verdict.a, verdict.b) if app_is_a else (verdict.b, verdict.a)
        for key in CRITERIA:
            totals["app"][key] += getattr(app_scores, key) / 2
            totals["plain"][key] += getattr(plain_scores, key) / 2
        if verdict.better != "TIE":
            result += 1 if (verdict.better == "A") == app_is_a else -1
    return totals["plain"], totals["app"], result


def evaluate(topics, slides, conn, judge_conn=None, out=None, pptx=False, log=print):
    """Run the comparison and return the report as Markdown."""
    rows = []
    for number, (topic, goal, audience) in enumerate(topics, 1):
        log(f"[{number}/{len(topics)}] {topic}")
        try:
            plain, app = write_plain(topic, slides, conn), write_app(topic, goal, audience, slides, conn)
        except Exception as e:                      # one failed topic should not end the whole run
            log(f"    failed: {e}")
            continue
        sides = {name: Side(deck, score(check_deck(deck, AMOUNT)), check_deck(deck, AMOUNT))
                 for name, deck in (("plain", plain), ("app", app))}
        result = None
        if judge_conn:
            try:
                sides["plain"].judge, sides["app"].judge, result = judge(topic, goal, audience, plain, app, judge_conn)
            except Exception as e:
                log(f"    judge failed: {e}")
        rows.append((topic, goal, audience, sides, result))
        if out:
            save(out, number, sides, pptx)
    return report(rows, slides, conn, judge_conn)


def save(out, number, sides, pptx):
    out.mkdir(parents=True, exist_ok=True)
    for name, side in sides.items():
        (out / f"{number:02d}_{name}.json").write_text(side.deck.model_dump_json(indent=2), encoding="utf-8")
        if pptx:
            from generator.render.builder import build_pptx
            (out / f"{number:02d}_{name}.pptx").write_bytes(build_pptx(side.deck, "corporate", "Corporate Blue", {}))


def mean(values):
    values = list(values)
    return sum(values) / len(values) if values else 0


def report(rows, slides, conn, judge_conn):
    def who(c):
        return f"{c['provider']} {c.get('model') or '(default model)'}" if c else "none"
    lines = ["# Plain chat request vs the app", "",
             f"Writer: {who(conn)}; judge: {who(judge_conn)}; {len(rows)} topics, {slides} slides each.", ""]
    if not rows:
        return "\n".join(lines + ["Nothing was compared: every topic failed."])
    lines += ["## Summary", "", "| | plain request | the app |", "|---|---|---|"]
    lines.append(f"| automatic check score (0-100) | {mean(r[3]['plain'].score for r in rows):.0f} | "
                 f"{mean(r[3]['app'].score for r in rows):.0f} |")
    for label, key in (("slide types used", "types"), ("slides with a number", "with_number"),
                       ("words per slide", "words")):
        lines.append(f"| {label} | {mean(counts(r[3]['plain'].deck)[key] for r in rows):.1f} | "
                     f"{mean(counts(r[3]['app'].deck)[key] for r in rows):.1f} |")
    judged = [r for r in rows if r[4] is not None]
    if judged:
        for key in CRITERIA:
            lines.append(f"| judge: {key} (1-5) | {mean(r[3]['plain'].judge[key] for r in judged):.2f} | "
                         f"{mean(r[3]['app'].judge[key] for r in judged):.2f} |")
        wins = sum(r[4] > 0 for r in judged)
        losses = sum(r[4] < 0 for r in judged)
        lines += ["", f"The judge preferred the app on {wins} of {len(judged)} topics, the plain request on "
                      f"{losses}, and could not decide (or changed its mind when the order was swapped) on "
                      f"{len(judged) - wins - losses}."]
    lines += ["", "## Per topic", "", "| topic | purpose | check: plain → app | judge |", "|---|---|---|---|"]
    for topic, goal, _, sides, result in rows:
        verdict = {None: "-", 2: "app", 1: "app (one order)", 0: "tie", -1: "plain (one order)", -2: "plain"}[result]
        lines.append(f"| {topic} | {goal} | {sides['plain'].score} → {sides['app'].score} | {verdict} |")
    lines += ["", "## What the automatic check found in the plain requests", ""]
    found = {}
    for row in rows:
        for issue in row[3]["plain"].findings:
            found[issue.code] = found.get(issue.code, 0) + 1
    lines += [f"- {code}: {n}" for code, n in sorted(found.items(), key=lambda kv: -kv[1])] or ["- nothing"]
    return "\n".join(lines) + "\n"


def read_topics(path):
    topics = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        parts = [part.strip() for part in line.split("|")]
        if parts[0]:
            topics.append((parts[0], parts[1] if len(parts) > 1 and parts[1] else "inform",
                           parts[2] if len(parts) > 2 else ""))
    return topics


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--provider", default="gemini", choices=["gemini", "openai", "claude"])
    parser.add_argument("--model", help="model name; the provider's default if left out")
    parser.add_argument("--judge-provider", choices=["gemini", "openai", "claude"],
                        help="who judges; the writer's provider if left out")
    parser.add_argument("--judge-model")
    parser.add_argument("--no-judge", action="store_true", help="only the automatic check")
    parser.add_argument("--topics", help="a text file: one topic per line, or 'topic | purpose | audience'")
    parser.add_argument("--limit", type=int, help="only the first N topics")
    parser.add_argument("--slides", type=int, default=8)
    parser.add_argument("--pptx", action="store_true", help="also save both presentations as .pptx")
    parser.add_argument("--out", default=str(ROOT / "evaluation"))
    args = parser.parse_args(argv)

    topics = read_topics(args.topics) if args.topics else TOPICS
    topics = topics[: args.limit] if args.limit else topics
    conn = {"provider": args.provider, "model": args.model}
    judge_conn = None if args.no_judge else {"provider": args.judge_provider or args.provider,
                                             "model": args.judge_model}
    out = Path(args.out)
    text = evaluate(topics, args.slides, conn, judge_conn, out=out, pptx=args.pptx)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.md").write_text(text, encoding="utf-8")
    print(text)
    print(f"Report: {out / 'report.md'}")


if __name__ == "__main__":
    main()
