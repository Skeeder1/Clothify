.PHONY: help setup setup-bot bot start_bot start stop restart logs status process process-all clean

help:
	@echo "Clothify - Image Processor & Discord Bot"
	@echo ""
	@echo "Setup:"
	@echo "  make setup        - Create venv and install all dependencies"
	@echo "  make setup-bot    - Install bot dependencies only"
	@echo ""
	@echo "Docker Services (PostgreSQL + n8n):"
	@echo "  make start        - Start all Docker services"
	@echo "  make stop         - Stop all Docker services"
	@echo "  make restart      - Restart all Docker services"
	@echo "  make logs         - View Docker logs (all services)"
	@echo "  make status       - Show Docker services status"
	@echo ""
	@echo "Discord Bot:"
	@echo "  make start_bot    - Start bot with .env (foreground, logs visible)"
	@echo "  make bot          - Run the Discord bot (without .env loading)"
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
	@echo "Setup complete! Run 'make start' then 'make bot' to begin."

setup-bot:
	.venv/bin/pip install -r bot/requirements.txt
	@echo "Bot dependencies installed."

# Docker services
start:
	docker compose up -d
	@echo ""
	@echo "Services started:"
	@echo "  - PostgreSQL: localhost:5432"
	@echo "  - n8n:        http://localhost:5678"

stop:
	docker compose down
	@echo "All services stopped."

restart:
	docker compose restart
	@echo "Services restarted."

logs:
	docker compose logs -f

status:
	docker compose ps

# Discord bot
bot:
	.venv/bin/python -m bot.main

start_bot:
	@echo "Starting Clothify Discord Bot..."
	@echo "Press Ctrl+C to stop"
	@echo ""
	@set -a && source .env && set +a && .venv/bin/python -m bot.main

# Image processing (legacy)
process:
	.venv/bin/python image-processor/main.py

process-all:
	.venv/bin/python image-processor/main.py --all

clean:
	rm -rf .venv
	@echo "Virtual environment removed."
