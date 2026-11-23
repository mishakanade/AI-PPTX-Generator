# The app in a container: no Python to install, one command to start.
#
#   docker build -t ai-pptx-generator .
#   docker run -p 8501:8501 --env-file .env ai-pptx-generator
#
# then open http://localhost:8501. The keys come from your .env file (see .env.example),
# or are typed into the sidebar. Without LibreOffice the image is much smaller, and the
# app simply offers no PDF:
#
#   docker build --build-arg WITH_PDF=0 -t ai-pptx-generator .

FROM python:3.13-slim

# LibreOffice makes the PDF; Carlito and Liberation have exactly the letter widths of
# Calibri and Arial, so the PDF looks like the slides were laid out (see generator/export.py)
ARG WITH_PDF=1
RUN if [ "$WITH_PDF" = "1" ]; then \
        apt-get update \
        && apt-get install -y --no-install-recommends libreoffice-impress fonts-crosextra-carlito fonts-liberation \
        && rm -rf /var/lib/apt/lists/*; \
    fi

# the app does not need to run as the all-powerful root user
RUN useradd --create-home app
WORKDIR /home/app/ai-pptx-generator

# the libraries first: Docker keeps this step cached while only the code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=app:app . .
USER app

EXPOSE 8501
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"
CMD ["python", "-m", "streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", "--browser.gatherUsageStats=false"]
