"""What makes a presentation good, written down for the model.

A chat assistant asked for "a presentation about X" produces a list of topics with generic
bullets. Good presentations are built differently: they have a purpose, a known audience,
a storyline that fits the purpose, and every slide makes one point stated in its title.
This module holds that knowledge so the prompts can apply it every time:

    GOALS          the purpose of the talk and the storyline that serves it
    WRITING_RULES  the "house style" every slide is held to
    notes_words()  how long the speaker notes should be for the length of the talk
"""

# Each goal: a short description for the model and the storyline, step by step.
# The storyline is a guide for ordering the slides, not a list of required slide titles.
GOALS = {
    "inform": {
        "label": "Inform / overview",
        "intent": "give the audience a clear, well-ordered understanding of the topic",
        "storyline": [
            "why the topic matters to this audience right now",
            "the essential context, briefly",
            "the key facts and how they connect, from most to least important",
            "what it means in practice: consequences, examples",
            "the few things the audience should remember",
        ],
    },
    "persuade": {
        "label": "Persuade / proposal",
        "intent": "convince the audience to accept a recommendation and act on it",
        "storyline": [
            "situation: what the audience already agrees with",
            "complication: what has changed or what is at stake",
            "the recommendation, stated early and plainly",
            "evidence for it: data, examples, comparisons",
            "the strongest objections and the answers to them",
            "the concrete next step you ask the audience to take",
        ],
    },
    "teach": {
        "label": "Teach / lecture",
        "intent": "make the audience able to understand and use something new",
        "storyline": [
            "what the audience will be able to do after this talk",
            "a hook that connects to what they already know",
            "the concepts one at a time, each with a concrete example",
            "a worked example or a step-by-step process",
            "common mistakes and how to avoid them",
            "a recap and a question to check understanding",
        ],
    },
    "report": {
        "label": "Report / results",
        "intent": "tell decision makers what happened, why, and what comes next",
        "storyline": [
            "the executive summary first: the result and its meaning in one slide",
            "the key numbers against the targets",
            "what worked and why",
            "what did not work and why",
            "risks and open questions",
            "next steps with owners or dates where possible",
        ],
    },
    "pitch": {
        "label": "Pitch / investors",
        "intent": "make investors or partners want to back the idea",
        "storyline": [
            "the problem, made concrete with who has it and what it costs them",
            "the solution and why it works",
            "why now",
            "the market and its size",
            "the product or the business model",
            "traction or proof so far",
            "competition and the advantage over it",
            "the team",
            "the ask: what you want and what it will achieve",
        ],
    },
}
DEFAULT_GOAL = "inform"

WRITING_RULES = [
    "Every content slide makes ONE point. Its title states that point as a short sentence, "
    "a takeaway the audience could repeat (for example \"Cars take 70% of street space but carry "
    "30% of trips\"), not a topic label (not \"Street space\"). Agenda, section, quote and closing "
    "slides keep short titles.",
    "Read the titles alone, in order: they must tell the whole story.",
    "Be specific: names, numbers with units, dates, examples. Cut anything that would fit any topic.",
    "No filler phrases such as \"in today's world\", \"it is important to note\", \"plays a key role\", "
    "\"in conclusion\", \"various\", \"a wide range of\", or their equivalents in other languages.",
    "Bullets on one slide have the same grammatical form and similar length.",
    "Never repeat a point that another slide already makes.",
    "Numbers must be real. If you are not sure of a number, describe the fact without it.",
]

WORDS_PER_MINUTE = 130     # a calm speaking pace


def notes_words(minutes, num_slides):
    """How many words of speaker notes per slide fill a talk of the given length."""
    if not minutes:
        return None
    return max(25, round(minutes * WORDS_PER_MINUTE / (num_slides + 1)))


def goal_block(goal, audience):
    """The part of a prompt that states purpose, audience and storyline."""
    data = GOALS.get(goal, GOALS[DEFAULT_GOAL])
    lines = [f"PURPOSE: {data['intent']}."]
    if audience.strip():
        lines.append(f"AUDIENCE: {audience.strip()}. Choose depth, terms and examples for them.")
    lines.append("STORYLINE: order the slides so they follow this arc (merge or skip steps the topic does "
                 "not need; this is a guide, not a list of slide titles):")
    lines += [f"  {i}. {step}" for i, step in enumerate(data["storyline"], 1)]
    return lines


def rules_block():
    return ["WRITING RULES:"] + [f"- {rule}" for rule in WRITING_RULES]
