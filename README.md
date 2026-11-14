# AI-PPTX-Generator
An open code AI agent that generates presentations based on the user's input on the topic of the Presentation, chosen color preset, style and tone of the text and additional commentary.
Works on this APIs: google-genai, Unsplash API

This version is only in Alpha - the project will keep improving with time, as this is built in solo.

The UI might be a little crooked and unappealing, this will be fixed in the next versions.

Its a BYOK (Bring Your Own Key) application. To get your api keys, go to those websites : 
- https://unsplash.com/developers
- https://aistudio.google.com/api-keys

To run the project, follow these steps:
  1. Git clone the project into a directory
  2. CD into that directory (example): `cd C:\Users\Your Username\Documents\MyProject`
  3. Install the libraries: `pip install -r requirements.txt`
  4. Copy `.env.example` to a new file named `.env` and put your API keys into the variables "GEMINI_API_KEY" and "UNSPLASH_CLIENT_ID" (the Unsplash key is optional: without it presentations are generated without images)
  5. Run this in the terminal: `python -m streamlit run app.py`

Supported documents: TXT, PDF and DOCX. After a presentation is generated you can switch the design theme, and the file is rebuilt with the same content without a new request to Gemini.

## Project structure

```
app.py                      Streamlit interface: the form, messages, download button
generator/
  config.py                 API keys and model names
  content/
    presets.py              tone and text-amount presets
    prompt.py               builds the request text for Gemini
    llm.py                  sends the request, retries on failures, parses the answer
    documents.py            reads text from TXT / PDF / DOCX
  design/
    themes.py               colour palettes
  images/
    unsplash.py             finds and downloads pictures
  render/
    pptx_builder.py         turns the content + theme + pictures into a .pptx file
```

How a presentation is made: `app.py` collects the form → `prompt.py` builds the request → `llm.py` gets the slide structure from Gemini as JSON → `unsplash.py` downloads a picture for each slide → `pptx_builder.py` builds the file.
