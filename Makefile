PYTHON ?= .venv/bin/python

.PHONY: install browsers test e2e report-pdf lint format run-all notebook serve clean-outputs \
	frontend api-types frontend-dev benchmark accessibility docker audit deploy backup-online

install:
	python3.12 -m venv .venv
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements-dev.txt
	$(PYTHON) -m pip install -e .

browsers:
	$(PYTHON) -m playwright install chromium firefox webkit

test:
	$(PYTHON) -m pytest --cov --cov-report=term

e2e:
	$(PYTHON) -m pytest tests/e2e -o addopts=""

report-pdf:
	$(PYTHON) scripts/build_report_pdf.py

lint:
	$(PYTHON) -m ruff check src tests webapp scripts
	$(PYTHON) -m black --check src tests webapp scripts

format:
	$(PYTHON) -m black src tests webapp scripts
	$(PYTHON) -m ruff check --fix src tests webapp scripts

run-all:
	$(PYTHON) -m antenatal run-all

notebook:
	cd notebooks && ../$(PYTHON) -m jupyter nbconvert --to notebook --execute --inplace 01_data_audit.ipynb
	cd notebooks && ../$(PYTHON) -m jupyter nbconvert --to notebook --execute --inplace 02_model_notebook.ipynb

serve:
	$(PYTHON) -m uvicorn webapp.app.main:app --host 127.0.0.1 --port 8000

# The Next.js interface. `make frontend` builds the static export that
# `make serve` then serves at http://127.0.0.1:8000/.
frontend:
	cd frontend && npm ci && npm run build

# Regenerate the typed client after a change to an API request or response.
api-types:
	$(PYTHON) scripts/export_openapi.py
	cd frontend && npm run gen:types

# Hot reloading interface on :3000, forwarding /api to `make serve` on :8000.
frontend-dev:
	cd frontend && npm run dev

# Evidence: API start up, latency and memory, and Lighthouse accessibility scores.
benchmark:
	$(PYTHON) scripts/benchmark_api.py

accessibility:
	$(PYTHON) scripts/accessibility_audit.py

# The interface and API in one container at http://127.0.0.1:8000/.
docker:
	docker compose up --build

# Evidence that the held out records never reached training (decision D7).
audit:
	$(PYTHON) -m antenatal audit-holdout

# Online deployment on Fly.io and its backup to the local environment (docs/OPERATIONS.md).
deploy:
	fly deploy --remote-only

backup-online:
	mkdir -p backups
	fly ssh console -C "python -c \"import sqlite3; sqlite3.connect('/app/state/app.sqlite3').backup(sqlite3.connect('/app/state/backup.sqlite3'))\""
	fly ssh sftp get /app/state/backup.sqlite3 backups/online.sqlite3
