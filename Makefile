PYTHON ?= .venv/bin/python

.PHONY: install test lint format run-all notebook serve clean-outputs

install:
	python3.12 -m venv .venv
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements-dev.txt
	$(PYTHON) -m pip install -e .

test:
	$(PYTHON) -m pytest --cov --cov-report=term

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
