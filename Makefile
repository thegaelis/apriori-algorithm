# Cross-platform Makefile (Windows, macOS, Ubuntu/Linux).
# Windows note: run `make` via Git Bash, WSL, or MSYS2 so that `rm`, `test`,
# and other POSIX tools used below are available (plain cmd.exe is not supported).

VENV_DIR := venv

ifeq ($(OS),Windows_NT)
	VENV_BIN       := $(VENV_DIR)/Scripts
	VENV_PYTHON    := $(VENV_DIR)/Scripts/python.exe
	DEFAULT_PYTHON := python
else
	VENV_BIN       := $(VENV_DIR)/bin
	VENV_PYTHON    := $(VENV_DIR)/bin/python
	DEFAULT_PYTHON := python3
endif

# Prefer the ./venv created by `make init`; otherwise fall back to whatever
# python/python3 resolves to on PATH (e.g. an already-activated virtualenv).
PYTHON ?= $(if $(wildcard $(VENV_PYTHON)),$(VENV_PYTHON),$(DEFAULT_PYTHON))

.PHONY: init install run test clean help

help:
	@echo "Targets:"
	@echo "  make init     Create a virtual environment in ./$(VENV_DIR)"
	@echo "  make install  Install dependencies into the virtual environment"
	@echo "  make run      Run self-hosted educational Apriori web app"
	@echo "  make test     Run unit tests"
	@echo "  make clean    Remove the virtual environment"
	@echo ""
	@echo "First-time setup: make init && make run"

init:
	$(DEFAULT_PYTHON) -m venv $(VENV_DIR)
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PYTHON) -m pip install -r requirements.txt
	@echo ""
	@echo "Virtual environment ready in ./$(VENV_DIR)"
	@echo "Activate it with:"
	@echo "  source $(VENV_BIN)/activate      (macOS / Ubuntu / Git Bash)"
	@echo "  $(VENV_DIR)/Scripts/activate      (Windows PowerShell / cmd)"

install:
	$(PYTHON) -m pip install -r requirements.txt

run:
	$(PYTHON) app.py

test:
	$(PYTHON) -m unittest discover -s tests

clean:
	rm -rf $(VENV_DIR)

