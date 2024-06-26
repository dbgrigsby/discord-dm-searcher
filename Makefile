VENV_DIR = virtualenv_run
PYTHON = $(VENV_DIR)/bin/python

virtualenv_run:
	python3 -m venv $(VENV_DIR)
	@echo "Virtual environment created at: $(VENV_DIR)"
	@echo "Upgrading pip..."
	$(PYTHON) -m pip install --upgrade pip
	@echo "Installing requirements..."
	$(PYTHON) -m pip install --prefer-binary -r requirements.txt

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

.PHONY: build
build:
	sudo docker build -t discord-dm-searcher .

.PHONY: clean
clean:
	rm -rf virtualenv_run/

.PHONY: test
test: virtualenv_run
	${PYTHON} -m pytest --disable-warnings