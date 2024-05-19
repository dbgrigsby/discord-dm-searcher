VENV_DIR = virtualenv_run
PYTHON = $(VENV_DIR)/bin/python

.PHONY: virtualenv_run ingest_data search

virtualenv_run:
	python3 -m venv $(VENV_DIR)
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt

ingest_data:
	@for file in import/*.json; do \
		$(PYTHON) src/ingest_messages.py $$file; \
	done

search:
	@echo "To search, use the following command:"
	@echo "$(PYTHON) src/search_messages.py [--no-cost] search_term"
