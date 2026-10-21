# Serves the prototype interface and API with the frozen artefact.
# The analysis itself runs on the host with `make run-all`; the image only
# needs the package (for the artefact class and feature construction), the
# webapp and the artefact files.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    ANTENATAL_DATABASE_URL=sqlite:////app/state/app.sqlite3
WORKDIR /app

COPY requirements.txt pyproject.toml README.md ./
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
RUN pip install --no-cache-dir --no-deps .
COPY webapp ./webapp

RUN useradd --create-home appuser && mkdir -p /app/state && chown appuser /app/state
USER appuser
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"
CMD ["uvicorn", "webapp.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
