"""Presets the user picks in the UI; each one becomes instructions inside the prompt.

TONE_PRESETS         - how the text should sound.
TEXT_AMOUNT_PRESETS  - how much text goes on a slide: a description for the model
                       and word limits for a bullet slide and for smaller text blocks.
"""

TONE_PRESETS = {
    "💼 Professional": (
        "TONE MANDATE [Professional]: Use formal corporate language, passive voice where appropriate, "
        "and data-driven framing. Focus heavily on key metrics, KPIs, risk factors, efficiency gains, "
        "and strategic business impact. Avoid exclamations or overly enthusiastic language."
    ),
    "🚀 Creative / Pitch Deck": (
        "TONE MANDATE [Creative/Pitch Deck]: Use punchy, high-energy, persuasive language. "
        "Structure content as a narrative arc: Call out a painful Problem, introduce a disruptive Solution, "
        "and highlight key Differentiators. Use active verbs, bold statements, and compelling storytelling."
    ),
    "📚 Educational / Academic": (
        "TONE MANDATE [Educational]: Use clear, explanatory language designed for learning. "
        "Break down complex terms with direct analogies, 'Key Takeaway' definitions, step-by-step logic, "
        "and concrete real-world examples."
    )
}

TEXT_AMOUNT_PRESETS = {
    "Paragraph-style": {
        "description": (
            "Write in flowing paragraphs. Each item in \"bullets\" is one short paragraph "
            "of 2-4 complete sentences with explanations and, where useful, examples. "
            "Prefer fewer, longer items."
        ),
        "max_words": 80,     # limit for all bullets of one slide together
        "item_words": 35,    # limit for one card text, one column, one timeline step
    },
    "Talking-Points-Style": {
        "description": (
            "Write short talking points that help a presenter improvise the speech: "
            "each item is a few words up to one short line (max ~10 words), focused on key ideas, "
            "facts and takeaways. Prefer more, shorter items."
        ),
        "max_words": 45,
        "item_words": 14,
    },
    "Balanced": {
        "description": (
            "Mix concise bullet points with short explanatory sentences: each slide combines "
            "a few short bullets with one or two explanatory sentences."
        ),
        "max_words": 60,
        "item_words": 24,
    },
}
