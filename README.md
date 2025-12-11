# NanoBanana Bot

Discord bot + n8n for generating product visuals.

## Setup

```bash
cp .env.example .env
nano .env  # Configure your tokens
make start
```

## Access

- n8n: http://localhost:5678

## Commands

```bash
make start      # Start all services
make stop       # Stop all services
make start-n8n  # Start n8n only
make stop-n8n   # Stop n8n only
make logs       # View logs
make backup     # Backup database
```
