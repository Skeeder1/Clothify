.PHONY: help setup setup-bot bot process process-all db-start db-stop db-logs clean

help:
	@echo "Clothify - Image Processor & Discord Bot"
	@echo ""
	@echo "Setup:"
	@echo "  make setup        - Create venv and install all dependencies"
	@echo "  make setup-bot    - Install bot dependencies only"
	@echo ""
	@echo "Discord Bot:"
	@echo "  make bot          - Run the Discord bot"
	@echo ""
	@echo "Database:"
	@echo "  make db-start     - Start PostgreSQL database"
	@echo "  make db-stop      - Stop PostgreSQL database"
	@echo "  make db-logs      - View database logs"
	@echo ""
	@echo "Image Processing:"
	@echo "  make process      - Process 1 random image"
	@echo "  make process-all  - Process all images"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean        - Remove virtual environment"

setup:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r bot/requirements.txt
	@echo ""
	@echo "Setup complete! Run 'make bot' to start the Discord bot."

setup-bot:
	.venv/bin/pip install -r bot/requirements.txt
	@echo "Bot dependencies installed."

bot:
	.venv/bin/python -m bot.main

db-start:
	docker compose -f Database/docker-compose.yml up -d
	@echo "PostgreSQL database started on port 5432"

db-stop:
	docker compose -f Database/docker-compose.yml down
	@echo "PostgreSQL database stopped"

db-logs:
	docker compose -f Database/docker-compose.yml logs -f

process:
	.venv/bin/python image-processor/main.py

process-all:
	.venv/bin/python image-processor/main.py --all

clean:
	rm -rf .venv
	@echo "Virtual environment removed."
