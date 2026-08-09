# GitHub Copilot Instructions (Clothify)

These instructions apply to all Copilot-generated code and edits in this repository.

---

## System Overview

**Clothify** is a Virtual Try-On service accessible via Discord. Users upload garment images, and an AI generates professional product visualizations delivered back to Discord.

### Architecture
- **3-tier microservices:** Discord Bot (Python) ↔ PostgreSQL ↔ n8n (workflow orchestrator)
- **Data flow:** Discord → Bot → DB → n8n → OpenRouter API → DB → Bot → Discord
- **Push-based:** PostgreSQL NOTIFY/LISTEN triggers instant job processing (no polling between DB and n8n)
- **File sharing:** Shared volumes between bot and n8n for image storage

### Technology Stack
- **Bot:** Python 3.11+, `discord.py` (async), `asyncpg` (async PostgreSQL driver)
- **Database:** PostgreSQL 16 with native NOTIFY/LISTEN, UUIDs, ENUMs, triggers
- **Workflow:** n8n (self-hosted) with PostgreSQL Trigger nodes
- **AI:** OpenRouter (`openai/gpt-5-image-mini`). The call lives in the n8n
  workflow, never in `bot/`. See `docs/IMAGE_GENERATION.md`.
- **Runtime:** Docker Compose (local) or Coolify (production)

### Key Data Models
- **users:** Discord user tracking (`discord_id`, `total_jobs`)
- **jobs:** Queue table (`status`: pending/processing/done/error/sent, `input_file_paths`, `output_file_path`, `product_name`)
- **job_logs:** Audit trail for status transitions

### Workflow Sequence
1. User uploads image in Discord → Bot saves to `./images/input/`
2. Bot inserts job with `status='pending'` → PostgreSQL trigger fires NOTIFY
3. n8n receives instant notification → Updates `status='processing'`
4. n8n reads input, calls OpenRouter, saves output to `./images/output/`, calls `complete_job()`
5. Bot polls job status every 5s → Detects completion → Sends result to Discord

---

## Project Context

- This repo is a Discord bot + n8n workflow runner backed by PostgreSQL.
- The bot is Python (`discord.py`) and uses async PostgreSQL access via `asyncpg`.
- Primary runtime is Docker Compose (local) or Coolify (production with Tailscale VPN).

---

## Dual-Environment Awareness

### LOCAL (Development)
- **Host:** Developer PC/laptop
- **Orchestration:** `docker-compose` (manual)
- **Network:** Docker bridge (default), services communicate via container names (`postgres`, `n8n`)
- **Config:** `.env` file in project root
- **Bot Deployment:** Runs on host (`python bot/main.py`), not containerized
- **Access:** `localhost:5432` (postgres), `localhost:5678` (n8n) via port mappings
- **Volumes:** Bind mounts (`./images/input/`, `./images/output/`) + named volumes

### PRODUCTION (Deployed)
- **Host:** Debian Home Lab server
- **Access:** Tailscale VPN (100.x.x.x private IPs) - NO public ports exposed
- **Orchestration:** Coolify (self-hosted PaaS) manages containers via Web UI
- **Network:** Coolify-managed Docker network with internal DNS (e.g., `postgres.coolify.internal`)
- **Config:** Coolify UI Environment Variables (encrypted)
- **Bot Deployment:** Dockerized via Coolify (uses `bot/Dockerfile`)
- **Access:** Services communicate via Coolify internal DNS
- **Volumes:** Coolify persistent volumes (managed via UI)
- **Security:** Tailscale provides encrypted WireGuard mesh; host firewall blocks all public ports

**Context Differentiation:**
- When user says "local" → assume Docker Compose, `.env` files, host-based bot
- When user says "prod" or "production" → assume Coolify, Tailscale, containerized bot
- If context is unclear, ask: "Are you working in the local (Docker Compose) or production (Coolify) environment?"

---

## Key Locations

- Bot code: `bot/` (entrypoint: `bot/main.py`)
- Bot handlers: `bot/handlers/` (`message.py`, `views.py`, `tasks.py`)
- DB schema/migrations: `Database/scripts/init/` and `Database/scripts/migrations/`
- Compose stack: `docker-compose.yml`
- Workflows: `n8n/workflows/` (JSON exports)
- System docs: `docs/SYSTEM_ARCHITECTURE.md` (comprehensive reference)

---

## Golden Rules

### 1. Environment-Agnostic Code (CRITICAL)
**Always use `os.getenv()` or `Config` class attributes. NEVER hardcode URLs, IPs, or paths.**

✅ **CORRECT:**
```python
from bot.config import Config
db_url = Config.DATABASE_URL  # Reads from environment
input_dir = Config.INPUT_DIR
```

❌ **INCORRECT:**
```python
db_url = "postgresql://postgres:postgres@localhost:5432/clothify"  # NEVER
input_dir = "/home/luffy/Github/Clothify/images/input/"  # NEVER
```

### 2. Service Discovery
Use container names or environment variables for service hostnames:

✅ **CORRECT:**
```yaml
DATABASE_URL: postgresql://postgres:postgres@postgres:5432/clothify
```

❌ **INCORRECT:**
```yaml
DATABASE_URL: postgresql://postgres:postgres@192.168.1.100:5432/clothify
```

### 3. Path Handling
Use path conversion functions and config values:

✅ **CORRECT:**
```python
from bot.utils.files import docker_to_host_path
host_path = docker_to_host_path(db_path)  # Converts /files/output/ → ./images/output/
```

❌ **INCORRECT:**
```python
host_path = db_path.replace("/files/", "./images/")  # Fragile!
```

---

## Working Agreements

- Make the smallest change that solves the request.
- Preserve existing architecture and patterns (no new frameworks).
- Do not add new services, endpoints, or UX features unless explicitly requested.
- Prefer updating existing modules over creating many new files.

---

## Python Conventions

- Keep code compatible with the existing style (type hints are used in config).
- Avoid one-letter variable names and avoid large refactors unless asked.
- When dealing with I/O or DB calls, keep them async-friendly (`async def`, `await`).
- Use `asyncpg` for all database interactions (already imported in `bot/database.py`).
- Follow existing patterns: `get_or_create_user()`, `create_job()`, `update_job_status()`.

---

## Database Conventions

- PostgreSQL is the source of truth.
- If schema changes are required, add a migration under `Database/scripts/migrations/`.
- Keep bot queries consistent with existing tables/enums:
  - **Tables:** `users`, `jobs`, `job_logs`
  - **ENUMs:** `garment_type` (15 values: echarpe, pull, tshirt, etc.), `size_code` (1-4), `job_status` (pending, processing, done, error, sent)
- Use provided functions: `complete_job()`, `fail_job()`, `reset_stale_jobs()`, `get_queue_stats()`.
- Never bypass triggers or constraints.

---

## Docker / Environment

- Prefer configuration via environment variables (see `bot/config.py` and `docker-compose.yml`).
- In local: Services defined in `docker-compose.yml` (postgres, n8n).
- In prod: Coolify manages services; reference `docs/SYSTEM_ARCHITECTURE.md` for deployment steps.
- Volume paths:
  - Local bot: `./images/input/`, `./images/output/`
  - n8n container: `/files/input/`, `/files/output/`
  - Use `docker_to_host_path()` to convert between n8n paths and bot paths.

---

## Validation

- If you modify Docker or DB scripts, sanity-check with:
  - `docker compose config`
  - `docker compose up -d`
- If you modify Python, ensure imports and basic startup remain intact.
- Test async code with `asyncio.run()` or within async context.

---

## Additional Context

### Database Functions Reference
- **complete_job(job_id, output_path):** Sets status='done', stores output path
- **fail_job(job_id, error_msg):** Handles failures with retry logic (max 3 attempts)
- **reset_stale_jobs(timeout_minutes):** Resets jobs stuck in 'processing'
- **get_queue_stats():** Returns counts by status (pending, processing, done, error)

### Bot Commands
- `!help` - Shows usage guide
- `!stats` - Shows queue statistics and user stats

### File Flow
1. User uploads → Bot saves to `./images/input/` (or `/app/images/input/` in prod)
2. n8n reads from `/files/input/` (mounted to same volume)
3. n8n writes to `/files/output/` (mounted to same volume)
4. Bot reads from `./images/output/` (or `/app/images/output/` in prod)

### Critical Files
- `bot/config.py` - Environment loader with validation
- `bot/database.py` - asyncpg connection pool and all DB functions
- `bot/handlers/message.py` - Discord event handlers
- `bot/handlers/views.py` - Interactive UI (GarmentSelectView, SizeSelectView)
- `bot/handlers/tasks.py` - Background polling (watch_job_status)
- `bot/utils/files.py` - File utilities (save_attachment, docker_to_host_path)

### Architectural Evolution
- **Original:** n8n polled database every 10s for pending jobs
- **Migration 002:** Added distributed locking (`locked_by`, `locked_at`)
- **Migration 003:** Introduced PostgreSQL NOTIFY/LISTEN for instant triggers
- **Migration 004:** Removed polling artifacts (current architecture)
- **Current:** Push-based (DB → n8n), bot polls for completion (acceptable 5s latency)

---

## For AI Agents: Context Loading Strategy

1. **For architecture questions:** Reference `docs/SYSTEM_ARCHITECTURE.md`
2. **For code changes:** Read relevant files in `bot/` or `Database/scripts/`
3. **For environment issues:** Check `docker-compose.yml` (local) or ask about Coolify config (prod)
4. **For workflow changes:** Reference `n8n/workflows/README.md`
5. **When unsure about environment:** Always ask "Local or Production?"

---

**Reference:** See `docs/SYSTEM_ARCHITECTURE.md` for complete system documentation, data flow diagrams, deployment procedures, and troubleshooting guides.



# Regle importantes

- tu à interdiction de creer des fichier temporaire de debug ou de test ou de documentation destiné à l'utilisateur pour une modif ponctuelle dans le code. tu dois absolument les ecrire dans bot/tempo.
- pour les tests durable et permanent ( a faire regulierement ) tu dois les faires dans le fichier bot/tests 
- pour les logs de debugg, lorsque tu en met supprime les une fois le probleme corrigé, si tu lis le code et que tu vois des logs de debug inutile, supprime les.
- pour le code, lorsque tu ecrit ou test des choses qui ne fonctionne pas, supprime les avant de tester autre choses, pour ne pas polluer le code. # tu dois toujours respecter le style de code et les conventions déja en place dans le projet.