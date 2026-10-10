# AI-PPTX-Generator
An open code AI agent that generates presentations based on the user's input on the topic of the Presentation, chosen color preset, style and tone of the text and additional commentary.
Works on this APIs: google-genai, Unsplash API

This version is only in Alpha - the project will keep improving with time, as this is built in solo.

Its a BYOK (Bring Your Own Key) application. To get your api keys, go to those websites : 
- https://unsplash.com/developers
- https://aistudio.google.com/api-keys

To run the project, follow this steps:
  1. Git clone the project into a directory
  2. CD the directory
  3. Download all the needed libraries (stated in requirements.txt)
  4. In your .env file, put your API keys you got in the variables "GEMINI_API_KEY" and "UNSPLASH_CLIENT_ID"
  5. Run this in the terminal : "python -m streamlit run app.py"
