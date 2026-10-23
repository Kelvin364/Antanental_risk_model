# Serves the prototype interface and API with the frozen artefact.
# The analysis itself runs on the host with `make run-all`; the image only
# needs the package (for the artefact class and feature construction), the
# webapp and the artefact files. The Next.js interface is built in its own
# stage and only its static export is copied into the final image.
FROM node:22-slim AS interface
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
RUN NEXT_TELEMETRY_DISABLED=1 npm run build

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    ANTENATAL_DATABASE_URL=sqlite:////app/state/app.sqlite3
WORKDIR /app

COPY requirements.txt pyproject.toml README.md ./
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
RUN pip install --no-cache-dir --no-deps .
COPY webapp ./webapp
COPY --from=interface /frontend/out ./frontend/out

COPY deploy/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN useradd --create-home appuser && mkdir -p /app/state && chown appuser /app/state

# The entrypoint hands /app/state to appuser and drops root before the server starts.
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["uvicorn", "webapp.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
