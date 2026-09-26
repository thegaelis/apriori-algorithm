PYTHON ?= python

.PHONY: install run test help

help:
	@echo "Targets:"
	@echo "  make run      Run self-hosted educational Apriori web app"
	@echo "  make test     Run unit tests"
	@echo "  make install  Install dependencies (optional, pure Python standard library)"

install:
	$(PYTHON) -m pip install -r requirements.txt

run:
	$(PYTHON) app.py

test:
	$(PYTHON) -m unittest discover -s tests

