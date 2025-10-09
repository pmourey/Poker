SHELL := /bin/bash

# Valeurs par défaut; surchargez via: make option-b SECRET_KEY=... HOST=... PORT=...
SECRET_KEY ?= change-me-in-prod
HOST ?= 0.0.0.0
PORT ?= 5000

.PHONY: option-b
option-b:
	@echo "[make] Lancement Option B (build React + start Flask)"
	@SECRET_KEY=$(SECRET_KEY) HOST=$(HOST) PORT=$(PORT) bash scripts/option_b.sh
