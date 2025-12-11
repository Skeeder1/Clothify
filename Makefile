.PHONY: help start stop logs build start-n8n stop-n8n

help:
	@echo "make start      - Start all services"
	@echo "make stop       - Stop all services"
	@echo "make start-n8n  - Start n8n only"
	@echo "make stop-n8n   - Stop n8n only"
	@echo "make logs       - View logs"
	@echo "make build      - Rebuild images"

start:
	docker compose up -d

stop:
	docker compose down

start-n8n:
	docker compose up -d postgres n8n

stop-n8n:
	docker compose stop n8n postgres

logs:
	docker compose logs -f

build:
	docker compose build --no-cache

backup:
	docker compose exec postgres pg_dump -U n8n n8n > backup_$$(date +%Y%m%d).sql
