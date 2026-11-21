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

        # AI provider
        "ai_header": "🤖 AI",
        "provider": "Who writes the content",
        "provider_gemini": "Gemini API",
        "provider_openai": "ChatGPT API (OpenAI)",
        "provider_claude": "Claude API (Anthropic)",
        "provider_chat": "Any AI chat (copy & paste)",
        "model": "Model",
        "model_help": "Leave empty for the default model.",
        "chat_mode_info": "💬 No API key needed: after you press Generate, the app gives you a request "
                          "to paste into ChatGPT, Claude, Gemini or any other AI chat.",

        # keys
        "keys_header": "🔑 API keys",
        "gemini_key": "Gemini API key",
        "openai_key": "OpenAI API key",
        "claude_key": "Anthropic API key",
        "unsplash_key": "Unsplash access key (optional)",
        "key_on_server": "Set on the server",
        "key_paste": "Paste your key",
        "key_no_photos": "Without it: no photos",
        "key_get": "Get one at {url}",
        "keys_note": "Keys typed here stay only in this browser session and are not saved.",
        "need_ai_key": (
            "🔑 **A {provider} API key is needed to generate presentations.** Get one at {url} "
            "and paste it into **API keys** in the sidebar, or put it into `{env}` in the `.env` file "
            "and restart the app. Or choose **Any AI chat (copy & paste)** to work without a key."
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
        "outline_first": "Show me the plan first",
        "outline_first_help": "The AI first proposes the list of slides; you edit it, then the slides are written.",
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
        "transition": "Slide transition",
        "transition_help": "The animation PowerPoint plays when moving to the next slide.",
        "transition_none": "None",
        "transition_fade": "Fade",
        "transition_push": "Push",
        "transition_wipe": "Wipe",
        "logo": "Logo (optional)",
        "logo_help": "Placed in a free corner of every slide. A PNG with a transparent background looks best.",
        "logo_remove": "✖ Remove logo",
        "logo_not_image": "⚠️ The logo file is not a picture.",
        "selected": "✓ Selected",
        "select": "Select",

        # generation
        "doc_ignored": "⚠️ {reason} The document was ignored.",
        "doc_unsupported": "Unsupported file type: {name}.",
        "doc_damaged": "Could not read {name}: the file looks damaged.",
        "doc_empty": "No text found in {name}.",
        "doc_scan": "No text found in {name}. It may be a scan: pages stored as images, not text.",
        "doc_long": "ℹ️ The document is long: only the first {used:,} of its {total:,} characters were used.",
        "add_key_first": "⚠️ Add a {provider} API key under **API keys** in the sidebar first.",
        "need_topic": "⚠️ Please enter a topic or upload a document!",
        "status_writing": "Writing the content with {provider}…",
        "status_photos": "Looking for photos on Unsplash…",
        "status_planning": "Planning the presentation with {provider}…",
        "status_plan_done": "The plan is ready",
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
                        "request to the AI; photos and speaker notes are kept.",
        "deck_title": "Presentation title",
        "deck_subtitle": "Subtitle",
        "slide_heading": "Slide {number} · {type}",
        "delete": "Delete",
        "slide_title": "Title",
        "slide_text": "Text",
        "author": "Author",
        "apply": "Apply changes",
        "keep_one": "⚠️ At least one slide must stay.",

        # copy & paste mode
        "chat_header": "💬 Ask any AI chat",
        "chat_steps": (
            "1. Copy the request below (the button appears in its top-right corner).\n"
            "2. Paste it into ChatGPT, Claude, Gemini or another AI chat and send it.\n"
            "3. Copy the whole answer, paste it below and press **Build presentation**. "
            "Photos are added automatically if an Unsplash key is set."
        ),
        "chat_answer": "The AI's answer",
        "chat_answer_placeholder": "Paste the whole answer here, including the JSON",
        "chat_file": "…or upload the answer as a file",
        "chat_build": "🧩 Build presentation",
        "chat_need_answer": "⚠️ Paste the AI's answer first.",
        "chat_bad_answer": (
            "❌ Could not read a presentation from this answer ({error}). Make sure you copied the "
            "whole answer including the JSON; if it was cut off, ask the chat to continue and paste it all."
        ),
        "regen_chat_show": "📋 Show the request",
        "regen_chat_apply": "Apply the answer",

        # outline
        "outline_header": "🗂️ The plan",
        "outline_caption": "Change the types and titles, delete slides or fill in an empty row to add one. "
                           "Then the AI writes the slides exactly by this plan.",
        "outline_type": "Type",
        "outline_title": "Title",
        "outline_focus": "What it says",
        "outline_delete": "Delete",
        "outline_new": "New slide",
        "outline_write": "✍️ Write the slides",
        "outline_empty": "⚠️ The plan needs at least one slide.",

        # projects
        "save_project": "💾 Save project",
        "save_project_help": "Everything in one file: text, photos, style and colours. Open it later to keep working.",
        "make_pdf": "📄 Make a PDF",
        "make_pdf_help": "Made by LibreOffice on this computer. Fonts may differ slightly from PowerPoint.",
        "download_pdf": "📥 Download PDF",
        "pdf_working": "LibreOffice is making the PDF…",
        "pdf_error": "❌ The PDF could not be made: {error}",
        "open_project": "📂 Open a saved project",
        "open_project_help": "A project saved here, or an AI chat's JSON answer saved as a file.",
        "project_error": "❌ Could not open this file: {error}",

        # photos
        "photos_header": "🖼️ Photos",
        "photos_caption": "Swap a slide's photo for another one from Unsplash, upload your own picture, or remove it.",
        "another_photo": "🔄 Another",
        "upload_photo": "Your own picture",
        "remove_photo": "✖ Remove",
        "no_photo": "No photo",
        "photo_not_image": "⚠️ This file is not a picture.",
        "photo_none_found": "⚠️ No other photo was found for “{keyword}”.",

        # regenerating one slide
        "regen_header": "🔄 Regenerate one slide",
        "regen_caption": "The AI rewrites only the chosen slide, keeping the rest. Optionally say what to change.",
        "regen_slide": "Slide",
        "regen_wish": "What to change (optional)",
        "regen_wish_placeholder": "Shorter, with an example / Turn it into a chart",
        "regen_button": "🔄 Regenerate",
        "regen_working": "{provider} is rewriting the slide…",
    },

    "ru": {
        "page_caption": "Опишите тему, выберите оформление и получите редактируемую презентацию PowerPoint.",
        "language": "Язык",

        "ai_header": "🤖 ИИ",
        "provider": "Кто пишет содержание",
        "provider_gemini": "Gemini API",
        "provider_openai": "ChatGPT API (OpenAI)",
        "provider_claude": "Claude API (Anthropic)",
        "provider_chat": "Любой ИИ-чат (копировать и вставить)",
        "model": "Модель",
        "model_help": "Оставьте пустым для модели по умолчанию.",
        "chat_mode_info": "💬 Ключ API не нужен: после нажатия «Создать» приложение выдаст запрос, "
                          "который нужно вставить в ChatGPT, Claude, Gemini или любой другой ИИ-чат.",

        "keys_header": "🔑 API-ключи",
        "gemini_key": "Ключ Gemini API",
        "openai_key": "Ключ OpenAI API",
        "claude_key": "Ключ Anthropic API",
        "unsplash_key": "Ключ Unsplash (необязательно)",
        "key_on_server": "Задан на сервере",
        "key_paste": "Вставьте ключ",
        "key_no_photos": "Без него — без фото",
        "key_get": "Получить: {url}",
        "keys_note": "Введённые здесь ключи живут только в этой сессии браузера и нигде не сохраняются.",
        "need_ai_key": (
            "🔑 **Для генерации нужен ключ {provider} API.** Получите его на {url} и вставьте в "
            "**API-ключи** на боковой панели или впишите в `{env}` в файле `.env` и перезапустите "
            "приложение. Или выберите **Любой ИИ-чат (копировать и вставить)** — тогда ключ не нужен."
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
        "outline_first": "Сначала показать план",
        "outline_first_help": "ИИ сначала предложит список слайдов; вы его поправите, и только потом пишутся слайды.",
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
        "transition": "Переход между слайдами",
        "transition_help": "Анимация, которую PowerPoint показывает при смене слайда.",
        "transition_none": "Без перехода",
        "transition_fade": "Растворение",
        "transition_push": "Сдвиг",
        "transition_wipe": "Появление",
        "logo": "Логотип (необязательно)",
        "logo_help": "Ставится в свободный угол каждого слайда. Лучше всего — PNG с прозрачным фоном.",
        "logo_remove": "✖ Убрать логотип",
        "logo_not_image": "⚠️ Файл логотипа не похож на картинку.",
        "selected": "✓ Выбран",
        "select": "Выбрать",

        "doc_ignored": "⚠️ {reason} Документ не использован.",
        "doc_unsupported": "Неподдерживаемый тип файла: {name}.",
        "doc_damaged": "Не удалось прочитать {name}: файл, похоже, повреждён.",
        "doc_empty": "В файле {name} нет текста.",
        "doc_scan": "В файле {name} нет текста. Возможно, это скан: страницы сохранены картинками.",
        "doc_long": "ℹ️ Документ длинный: использованы первые {used:,} из {total:,} символов.",
        "add_key_first": "⚠️ Сначала добавьте ключ {provider} API в **API-ключи** на боковой панели.",
        "need_topic": "⚠️ Введите тему или загрузите документ!",
        "status_writing": "{provider} пишет содержание…",
        "status_photos": "Ищу фотографии на Unsplash…",
        "status_planning": "{provider} составляет план…",
        "status_plan_done": "План готов",
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
                        "запроса к ИИ; фото и заметки сохранятся.",
        "deck_title": "Название презентации",
        "deck_subtitle": "Подзаголовок",
        "slide_heading": "Слайд {number} · {type}",
        "delete": "Удалить",
        "slide_title": "Заголовок",
        "slide_text": "Текст",
        "author": "Автор",
        "apply": "Применить",
        "keep_one": "⚠️ Должен остаться хотя бы один слайд.",

        "chat_header": "💬 Спросите любой ИИ-чат",
        "chat_steps": (
            "1. Скопируйте запрос ниже (кнопка появляется в его правом верхнем углу).\n"
            "2. Вставьте его в ChatGPT, Claude, Gemini или другой ИИ-чат и отправьте.\n"
            "3. Скопируйте весь ответ, вставьте его ниже и нажмите **Собрать презентацию**. "
            "Фото добавятся сами, если задан ключ Unsplash."
        ),
        "chat_answer": "Ответ ИИ",
        "chat_answer_placeholder": "Вставьте сюда весь ответ вместе с JSON",
        "chat_file": "…или загрузите ответ файлом",
        "chat_build": "🧩 Собрать презентацию",
        "chat_need_answer": "⚠️ Сначала вставьте ответ ИИ.",
        "chat_bad_answer": (
            "❌ Не удалось прочитать презентацию из этого ответа ({error}). Проверьте, что скопирован "
            "весь ответ вместе с JSON; если он оборвался, попросите чат продолжить и вставьте всё целиком."
        ),
        "regen_chat_show": "📋 Показать запрос",
        "regen_chat_apply": "Применить ответ",

        "outline_header": "🗂️ План",
        "outline_caption": "Поменяйте типы и заголовки, удалите слайды или заполните пустую строку, чтобы добавить. "
                           "Затем ИИ напишет слайды строго по этому плану.",
        "outline_type": "Тип",
        "outline_title": "Заголовок",
        "outline_focus": "О чём слайд",
        "outline_delete": "Удалить",
        "outline_new": "Новый слайд",
        "outline_write": "✍️ Написать слайды",
        "outline_empty": "⚠️ В плане должен быть хотя бы один слайд.",

        "save_project": "💾 Сохранить проект",
        "save_project_help": "Всё в одном файле: текст, фото, стиль и цвета. Откройте его позже, чтобы продолжить.",
        "make_pdf": "📄 Сделать PDF",
        "make_pdf_help": "Делается программой LibreOffice на этом компьютере. Шрифты могут немного отличаться от PowerPoint.",
        "download_pdf": "📥 Скачать PDF",
        "pdf_working": "LibreOffice делает PDF…",
        "pdf_error": "❌ Не удалось сделать PDF: {error}",
        "open_project": "📂 Открыть сохранённый проект",
        "open_project_help": "Проект, сохранённый здесь, или JSON-ответ ИИ-чата, сохранённый в файл.",
        "project_error": "❌ Не удалось открыть файл: {error}",

        "photos_header": "🖼️ Фотографии",
        "photos_caption": "Замените фото на слайде другим с Unsplash, загрузите свою картинку или уберите фото.",
        "another_photo": "🔄 Другое",
        "upload_photo": "Своя картинка",
        "remove_photo": "✖ Убрать",
        "no_photo": "Без фото",
        "photo_not_image": "⚠️ Этот файл не похож на картинку.",
        "photo_none_found": "⚠️ Другого фото для «{keyword}» не нашлось.",

        "regen_header": "🔄 Пересоздать один слайд",
        "regen_caption": "ИИ перепишет только выбранный слайд, остальные останутся как есть. "
                         "Можно написать, что изменить.",
        "regen_slide": "Слайд",
        "regen_wish": "Что изменить (необязательно)",
        "regen_wish_placeholder": "Короче и с примером / Сделай диаграммой",
        "regen_button": "🔄 Пересоздать",
        "regen_working": "{provider} переписывает слайд…",
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
