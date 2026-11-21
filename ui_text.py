"""Every text of the interface in English and Russian.

The interface asks for a text by its key: tr("generate"). Texts with {placeholders} are
filled in by tr("slides_count", count=5). The language of the generated presentations does
not depend on this: it follows the language of the topic or the document.

To add a language: add a dictionary with the same keys to TEXTS and its name to LANGUAGES.
"""

LANGUAGES = {"en": "English", "ru": "Русский"}

TEXTS = {
    "en": {
        "page_caption": "Describe a topic, pick a design, and get an editable PowerPoint presentation.",
        "language": "Language",

        # keys
        "keys_header": "🔑 API keys",
        "gemini_key": "Gemini API key",
        "unsplash_key": "Unsplash access key (optional)",
        "key_on_server": "Set on the server",
        "key_paste": "Paste your key",
        "key_no_photos": "Without it: no photos",
        "key_get": "Get one at {url}",
        "keys_note": "Keys typed here stay only in this browser session and are not saved.",
        "need_gemini_key": (
            "🔑 **A Gemini API key is needed to generate presentations.** Get one at "
            "https://aistudio.google.com/api-keys and paste it into **API keys** in the sidebar, "
            "or put it into `GEMINI_API_KEY` in the `.env` file and restart the app. "
            "Until then you can explore the styles and themes below."
        ),
        "no_unsplash_key": (
            "🖼️ No Unsplash key, so presentations will be generated without photos. "
            "Add one (https://unsplash.com/developers) under **API keys** in the sidebar or in `.env`."
        ),

        # content form
        "content": "Content",
        "topic": "Presentation topic",
        "topic_placeholder": "The History of Space Exploration",
        "document": "Source document (optional)",
        "tone": "Tone",
        "text_amount": "Text amount per slide",
        "wishes": "Additional wishes (optional)",
        "wishes_placeholder": "Focus on the environmental impact",
        "num_slides": "Number of slides",
        "speaker_notes": "Write speaker notes",
        "speaker_notes_help": "What to say on each slide. Saved in the notes of the PowerPoint file.",
        "generate": "🚀 Generate presentation",
        "design_hint": "The design on the right can be changed at any time, even after generation.",

        # design
        "design": "Design",
        "colour_theme": "Colour theme",
        "custom_colours": "✏️ Custom colours",
        "colour_bg": "Slide",
        "colour_title": "Titles",
        "colour_text": "Text",
        "colour_accent": "Accent",
        "adjusted": "Adjusted for readability: {names}.",
        "style": "Style",
        "selected": "✓ Selected",
        "select": "Select",

        # generation
        "doc_ignored": "⚠️ {reason} The document was ignored.",
        "doc_unsupported": "Unsupported file type: {name}.",
        "doc_damaged": "Could not read {name}: the file looks damaged.",
        "doc_empty": "No text found in {name}.",
        "doc_scan": "No text found in {name}. It may be a scan: pages stored as images, not text.",
        "doc_long": "ℹ️ The document is long: only the first {used:,} of its {total:,} characters were used.",
        "add_key_first": "⚠️ Add a Gemini API key under **API keys** in the sidebar first.",
        "need_topic": "⚠️ Please enter a topic or upload a document!",
        "status_writing": "Writing the content with Gemini…",
        "status_photos": "Looking for photos on Unsplash…",
        "status_done": "Content is ready",
        "status_failed": "Generation failed",
        "error": "❌ An error occurred: {error}",
        "build_error": "❌ Could not build the presentation: {error}",
        "unsplash_limit": (
            "Unsplash rejected some requests: the key is invalid or its hourly limit is used up, "
            "so some slides have no photo."
        ),

        # result
        "result_caption": "{count} slides · {style} style · {theme}. "
                          "Pick another style or theme above to redraw it with the same content.",
        "theme_named": "{name} theme",
        "theme_custom": "custom colours",
        "download": "📥 Download .pptx",
        "preview_note": "The preview is drawn by the browser and may differ slightly from PowerPoint "
                        "(for example if a font is not installed on this computer).",
        "notes_header": "🎤 Speaker notes",
        "title_slide": "Title slide",
        "notes_note": "The notes are also saved in the .pptx file: PowerPoint shows them in presenter view.",
        "credits_header": "📷 Photo credits",
        "credit_line": "- *{keyword}*: photo by [{author}]({url}) on [Unsplash]({unsplash})",
        "credits_note": "The same credits are saved in the speaker notes of the slides.",
        "json_header": "🔍 Generated content (JSON)",
        "example": "Example",
        "example_caption": "This is a built-in sample presentation drawn in the selected style and theme. "
                           "Fill in the form on the left to generate your own.",

        # editing
        "edit_header": "✏️ Edit slides",
        "edit_caption": "Change titles and text, or delete slides. The file is redrawn without a new "
                        "request to Gemini; photos and speaker notes are kept.",
        "deck_title": "Presentation title",
        "deck_subtitle": "Subtitle",
        "slide_heading": "Slide {number} · {type}",
        "delete": "Delete",
        "slide_title": "Title",
        "slide_text": "Text",
        "author": "Author",
        "apply": "Apply changes",
        "keep_one": "⚠️ At least one slide must stay.",

        # regenerating one slide
        "regen_header": "🔄 Regenerate one slide",
        "regen_caption": "Gemini rewrites only the chosen slide, keeping the rest. Optionally say what to change.",
        "regen_slide": "Slide",
        "regen_wish": "What to change (optional)",
        "regen_wish_placeholder": "Shorter, with an example / Turn it into a chart",
        "regen_button": "🔄 Regenerate",
        "regen_working": "Gemini is rewriting the slide…",
    },

    "ru": {
        "page_caption": "Опишите тему, выберите оформление и получите редактируемую презентацию PowerPoint.",
        "language": "Язык",

        "keys_header": "🔑 API-ключи",
        "gemini_key": "Ключ Gemini API",
        "unsplash_key": "Ключ Unsplash (необязательно)",
        "key_on_server": "Задан на сервере",
        "key_paste": "Вставьте ключ",
        "key_no_photos": "Без него — без фото",
        "key_get": "Получить: {url}",
        "keys_note": "Введённые здесь ключи живут только в этой сессии браузера и нигде не сохраняются.",
        "need_gemini_key": (
            "🔑 **Для генерации нужен ключ Gemini API.** Получите его на "
            "https://aistudio.google.com/api-keys и вставьте в **API-ключи** на боковой панели "
            "или впишите в `GEMINI_API_KEY` в файле `.env` и перезапустите приложение. "
            "А пока можно посмотреть стили и палитры ниже."
        ),
        "no_unsplash_key": (
            "🖼️ Нет ключа Unsplash, поэтому презентации будут без фотографий. "
            "Добавьте его (https://unsplash.com/developers) в **API-ключи** на боковой панели или в `.env`."
        ),

        "content": "Содержание",
        "topic": "Тема презентации",
        "topic_placeholder": "История освоения космоса",
        "document": "Документ-источник (необязательно)",
        "tone": "Тон",
        "text_amount": "Объём текста на слайде",
        "wishes": "Дополнительные пожелания (необязательно)",
        "wishes_placeholder": "Сделайте акцент на влиянии на экологию",
        "num_slides": "Количество слайдов",
        "speaker_notes": "Писать заметки докладчика",
        "speaker_notes_help": "Что говорить на каждом слайде. Сохраняется в заметках файла PowerPoint.",
        "generate": "🚀 Создать презентацию",
        "design_hint": "Оформление справа можно менять когда угодно, даже после генерации.",

        "design": "Оформление",
        "colour_theme": "Цветовая палитра",
        "custom_colours": "✏️ Свои цвета",
        "colour_bg": "Фон",
        "colour_title": "Заголовки",
        "colour_text": "Текст",
        "colour_accent": "Акцент",
        "adjusted": "Подправлено для читаемости: {names}.",
        "style": "Стиль",
        "selected": "✓ Выбран",
        "select": "Выбрать",

        "doc_ignored": "⚠️ {reason} Документ не использован.",
        "doc_unsupported": "Неподдерживаемый тип файла: {name}.",
        "doc_damaged": "Не удалось прочитать {name}: файл, похоже, повреждён.",
        "doc_empty": "В файле {name} нет текста.",
        "doc_scan": "В файле {name} нет текста. Возможно, это скан: страницы сохранены картинками.",
        "doc_long": "ℹ️ Документ длинный: использованы первые {used:,} из {total:,} символов.",
        "add_key_first": "⚠️ Сначала добавьте ключ Gemini API в **API-ключи** на боковой панели.",
        "need_topic": "⚠️ Введите тему или загрузите документ!",
        "status_writing": "Gemini пишет содержание…",
        "status_photos": "Ищу фотографии на Unsplash…",
        "status_done": "Содержание готово",
        "status_failed": "Генерация не удалась",
        "error": "❌ Произошла ошибка: {error}",
        "build_error": "❌ Не удалось собрать презентацию: {error}",
        "unsplash_limit": (
            "Unsplash отклонил часть запросов: ключ неверный или исчерпан часовой лимит, "
            "поэтому на некоторых слайдах нет фото."
        ),

        "result_caption": "Слайдов: {count} · стиль {style} · {theme}. "
                          "Выберите другой стиль или палитру выше, и презентация перерисуется с тем же текстом.",
        "theme_named": "палитра {name}",
        "theme_custom": "свои цвета",
        "download": "📥 Скачать .pptx",
        "preview_note": "Превью рисует браузер, поэтому оно может немного отличаться от PowerPoint "
                        "(например, если на компьютере нет нужного шрифта).",
        "notes_header": "🎤 Заметки докладчика",
        "title_slide": "Титульный слайд",
        "notes_note": "Заметки сохранены и в файле .pptx: PowerPoint показывает их в режиме докладчика.",
        "credits_header": "📷 Авторы фотографий",
        "credit_line": "- *{keyword}*: фото [{author}]({url}), [Unsplash]({unsplash})",
        "credits_note": "Те же подписи сохранены в заметках к слайдам.",
        "json_header": "🔍 Сгенерированное содержание (JSON)",
        "example": "Пример",
        "example_caption": "Это встроенная демонстрационная презентация в выбранном стиле и палитре. "
                           "Заполните форму слева, чтобы создать свою.",

        "edit_header": "✏️ Правка слайдов",
        "edit_caption": "Меняйте заголовки и текст или удаляйте слайды. Файл перерисуется без нового "
                        "запроса к Gemini; фото и заметки сохранятся.",
        "deck_title": "Название презентации",
        "deck_subtitle": "Подзаголовок",
        "slide_heading": "Слайд {number} · {type}",
        "delete": "Удалить",
        "slide_title": "Заголовок",
        "slide_text": "Текст",
        "author": "Автор",
        "apply": "Применить",
        "keep_one": "⚠️ Должен остаться хотя бы один слайд.",

        "regen_header": "🔄 Пересоздать один слайд",
        "regen_caption": "Gemini перепишет только выбранный слайд, остальные останутся как есть. "
                         "Можно написать, что изменить.",
        "regen_slide": "Слайд",
        "regen_wish": "Что изменить (необязательно)",
        "regen_wish_placeholder": "Короче и с примером / Сделай диаграммой",
        "regen_button": "🔄 Пересоздать",
        "regen_working": "Gemini переписывает слайд…",
    },
}

# Names of the choices in the form. The internal values (the keys) never change.
TONES = {
    "ru": {"💼 Professional": "💼 Деловой", "🚀 Creative / Pitch Deck": "🚀 Креативный / питч",
           "📚 Educational / Academic": "📚 Учебный / научный"},
}
TEXT_AMOUNTS = {
    "ru": {"Paragraph-style": "Абзацы", "Talking-Points-Style": "Тезисы для выступления",
           "Balanced": "Сбалансированно"},
}
STYLE_DESCRIPTIONS = {
    "ru": {
        "minimal": "Воздух, тонкие линии, спокойный шрифт",
        "editorial": "Заголовки с засечками, фото до края",
        "corporate": "Полоса заголовка, плотные цветные блоки",
        "soft": "Скруглённые карточки, мягкие тени",
        "bold": "Градиенты, крупные заголовки",
    },
}

SLIDE_TYPES = {
    "en": {
        "bullets": "Bullet points", "image": "Photo with a statement", "two_columns": "Two columns",
        "cards": "Cards", "stats": "Key numbers", "chart": "Chart", "quote": "Quote",
        "statement": "Key statement", "timeline": "Timeline", "table": "Table", "agenda": "Agenda",
        "section": "Section divider", "closing": "Closing takeaways",
    },
    "ru": {
        "bullets": "Пункты", "image": "Фото с подписью", "two_columns": "Две колонки",
        "cards": "Карточки", "stats": "Ключевые цифры", "chart": "Диаграмма", "quote": "Цитата",
        "statement": "Ключевая мысль", "timeline": "Хронология", "table": "Таблица", "agenda": "Содержание",
        "section": "Разделитель", "closing": "Итоги",
    },
}

EDIT_HINTS = {
    "en": {
        "bullets": "One point per line.",
        "closing": "One takeaway per line.",
        "agenda": "One part per line.",
        "cards": "One card per line: Heading — text",
        "stats": "One figure per line: 73% — what it means",
        "timeline": "One step per line: 1969 — what happened",
        "two_columns": "# Column heading, then its points. A blank line between the two columns.",
        "table": "Cells separated by |. The first line holds the headers.",
        "quote": "The quotation.",
        "chart": "The insight shown next to the chart (optional). Edit the numbers in PowerPoint.",
    },
    "ru": {
        "bullets": "Один пункт на строку.",
        "closing": "Один вывод на строку.",
        "agenda": "Одна часть на строку.",
        "cards": "Одна карточка на строку: Заголовок — текст",
        "stats": "Одна цифра на строку: 73% — что она значит",
        "timeline": "Один этап на строку: 1969 — что произошло",
        "two_columns": "# Заголовок колонки, затем её пункты. Между колонками — пустая строка.",
        "table": "Ячейки через |. В первой строке — заголовки столбцов.",
        "quote": "Текст цитаты.",
        "chart": "Вывод рядом с диаграммой (необязательно). Числа правятся в PowerPoint.",
    },
}


def pick(table, lang, key, default=None):
    """A translated name from one of the tables above, falling back to English or the key."""
    return table.get(lang, {}).get(key) or table.get("en", {}).get(key) or default or key
