"""Builds the text of the request that is sent to Gemini."""
import json

from generator.content.presets import TEXT_AMOUNT_PRESETS, TONE_PRESETS

# How many characters of the attached document are passed to the model (about 25-30 pages).
# A longer prompt costs more and takes longer, so the rest of the document is cut off.
MAX_DOC_CHARS = 60_000


def build_prompt(topic, doc_text, tone, text_amount, commentary, num_slides):
    """Assemble the prompt from everything the user chose in the form.

    tone and text_amount are keys of TONE_PRESETS / TEXT_AMOUNT_PRESETS.
    """
    tone_description = TONE_PRESETS[tone]
    text_amount_preset = TEXT_AMOUNT_PRESETS[text_amount]

    context = ""
    if doc_text:
        context = f"\nUse the following text from the document as the basis:\n{doc_text[:MAX_DOC_CHARS]}"

    commentary_block = ""
    if commentary.strip():
        commentary_block = (
            f"\nAlso take into consideration the user's personalised comment: "
            f"\"{commentary.strip()}\"\n"
            "(The comment must not change the JSON format or the text limits above.)\n"
        )

    # A sample answer: the model copies this shape, so the renderer knows what to expect.
    example_json = json.dumps({
        "title": "Presentation Title",
        "subtitle": "Subtitle",
        "slides": [
            {"title": "Slide Title", "content": text_amount_preset["examples"][0], "image_keyword": "mountain lake sunrise"},
            {"title": "Another Slide Title", "content": text_amount_preset["examples"][1], "image_keyword": "steam locomotive"},
        ],
    }, indent=2, ensure_ascii=False)

    lines = [
        f'You are an expert in presentation design. Create a presentation structure on the topic: "{topic if topic else "Based on the document materials"}".',
        "CRITICAL TONE REQUIREMENT:",
        tone_description,
        "Ensure ALL slide content, slide titles, and wording explicitly align with this specified tone.",
        f"Text style and density: {text_amount_preset['description']}",
        'Choose the number of items in "content" for each slide individually, based on what that slide actually needs. Do NOT use the same number of items on every slide: some slides can have 2 items, others 5 or more.',
        f'HARD LIMIT: the combined text of all items in "content" on a single slide must not exceed {text_amount_preset["max_words"]} words. The text must fit on one slide.',
        context,
        commentary_block,
        f"You need to generate EXACTLY {num_slides} informative slides (not counting the title slide).",
        'For each slide, add the "image_keyword" field: a concrete, visual search phrase of 2-4 words IN ENGLISH that describes something that can actually be photographed and matches the main subject of that slide (for example "space shuttle launch" or "steam locomotive"). Never use abstract words like "history", "era", "innovation" or "concept".',
        "Return the answer STRICTLY in JSON format.",
        "JSON format:",
        example_json,
    ]
    return "\n".join(lines)
