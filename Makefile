.PHONY: help setup setup-bot bot start_bot start stop restart logs status process process-all clean debug-config

help:
	@echo "Clothify - Image Processor & Discord Bot"
	@echo ""
	@echo "Setup:"
	@echo "  make setup        - Create venv and install all dependencies"
	@echo "  make setup-bot    - Install bot dependencies only"
	@echo ""
	@echo "Docker Services (PostgreSQL + n8n + Bot):"
	@echo "  make start        - Start all Docker services (including bot)"
	@echo "  make stop         - Stop all Docker services"
	@echo "  make restart      - Restart all Docker services"
	@echo "  make rebuild      - Rebuild and restart all services"
	@echo "  make rebuild-bot  - Rebuild and restart bot only"
	@echo "  make logs         - View Docker logs (all services)"
	@echo "  make logs-bot     - View bot logs only"
	@echo "  make logs-n8n     - View n8n logs only"
	@echo "  make status       - Show Docker services status"
	@echo ""
	@echo "Discord Bot (Local Development):"
	@echo "  make start_bot_local - Start bot on host (without Docker)"
	@echo "  make bot             - Run bot directly (for debugging)"
	@echo "  make debug-config    - Show configuration and paths (debugging)"
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
	@echo "  - Bot:        Running in container"

stop:
	docker compose down
	@echo "All services stopped."

restart:
	docker compose restart
	@echo "Services restarted."

logs:
	docker compose logs -f

logs-bot:
	docker compose logs -f bot

logs-n8n:
	docker compose logs -f n8n

status:
	docker compose ps

rebuild:
	docker compose up -d --build
	@echo "Services rebuilt and restarted."

rebuild-bot:
	docker compose up -d --build bot
	@echo "Bot service rebuilt and restarted."

# Discord bot (local development - without Docker)
bot:
	.venv/bin/python -m bot.main

start_bot_local:
	@echo "Starting Clothify Discord Bot (LOCAL mode)..."
	@echo "Press Ctrl+C to stop"
	@echo ""
	@set -a && source .env && set +a && .venv/bin/python -m bot.main

debug-config:
	@echo "Running configuration debug script..."
	@set -a && source .env && set +a && .venv/bin/python bot/debug_config.py

# Image processing (legacy)
process:
	.venv/bin/python image-processor/main.py

process-all:
	.venv/bin/python image-processor/main.py --all

clean:
	rm -rf .venv
	@echo "Virtual environment removed."
