VENV_DIR = virtualenv_run
PYTHON = $(VENV_DIR)/bin/python


virtualenv_run:
	python3 -m venv $(VENV_DIR)
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt

.PHONY: ingest_data
ingest_data:
	@FILES=$$(ls import/*.json); \
	COUNT=$$(echo $$FILES | wc -w); \
	if [ $$COUNT -ne 2 ]; then \
		echo "Error: There must be exactly two JSON files in the import directory."; \
		exit 1; \
	fi; \
	$(PYTHON) -m src.ingest_messages $$FILES

.PHONY: run
run: ingest_data virtualenv_run
	${PYTHON} -m src.bot
