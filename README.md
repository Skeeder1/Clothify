# Clothify — Virtual Try-On Service

Discord bot + n8n workflow orchestrator that turns a photo of a garment into a
professional e-commerce product visual, powered by image models served through
[OpenRouter](https://openrouter.ai).

## ✨ Results

The user uploads a flat photo of a garment; the pipeline returns a model wearing it.

| Input (uploaded to Discord) | Generated output | Alternate angle |
|---|---|---|
| <img src="docs/images/exemple-pull-source.jpg" width="200"> | <img src="docs/images/exemple-pull-openrouter.jpg" width="200"> | <img src="docs/images/exemple-pull-dos.jpg" width="200"> |

<img src="docs/images/exemple-maillot-openrouter.jpg" width="300">

*Generated with `openai/gpt-5.4-image-2` — 1024×1024, ~135 s end-to-end, ~$0.23 per image.
The workflow now runs `openai/gpt-5-image-mini`: 4.5x cheaper at ~$0.051 per image and
about twice as fast, at the cost of small embroidered text. Presets and their measured
figures are in `scripts/switch_model.py`.*

## 🎬 Demo

**Discord — from upload to result.** A garment photo goes in, the bot creates a
job and posts back the model shot. The on-screen timer shows the **real
generation time**; playback is accelerated (×2 during setup, ×15 during the wait).

![Discord demo](docs/media/clothify-discord-demo.gif)

▶ [Full-quality MP4](docs/media/clothify-discord-demo.mp4)

**Under the hood — the n8n pipeline running.** The same job flowing through the
workflow: Postgres trigger → prompt build → OpenRouter call → image extraction →
DB update, ending on the success state. Accelerated ×6.

![n8n workflow](docs/media/clothify-n8n-workflow.gif)

▶ [Full-quality MP4](docs/media/clothify-n8n-workflow.mp4)

> GIFs autoplay inline; click a **Full-quality MP4** link for the crisp version.
> Sources live in [`docs/media/`](docs/media/).

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Discord Bot Token ([Get one here](https://discord.com/developers/applications))
- OpenRouter API Key ([Get one here](https://openrouter.ai/keys))

### Installation

```bash
# 1. Clone and setup environment
cp .env.example .env
nano .env  # Configure DISCORD_TOKEN, POSTGRES_*, SHARED_VOLUME_PATH, etc.

# 2. Start infrastructure (PostgreSQL + n8n)
make start

# 3. Import the n8n workflow and its credential
#    The OpenRouter key is stored as an n8n credential, NOT as an env var.
#    See docs/IMAGE_GENERATION.md §3.

# 4. Start Discord bot
make start_bot
```

## 📖 Usage

### Discord Commands

Upload an image in the Discord channel and follow the interactive prompts:

1. **Upload image** → Bot detects and saves it
2. **Select garment type** → Choose from dropdown (pull, tshirt, jean, etc.)
3. **Choose size** → Pick visualization size (1-4)
4. **Wait for result** → AI generates professional product visual

Bot commands:
- `!help` - Show usage guide
- `!stats` - Display queue statistics and your job count

### Access Points

- **n8n Dashboard:** http://localhost:5678
- **PostgreSQL:** localhost:5432 (credentials in `.env`)

## 🛠️ Development

```bash
# Docker services
make start          # Start PostgreSQL + n8n
make stop           # Stop all services
make restart        # Restart services
make logs           # View Docker logs
make status         # Check services status

# Bot management
make start_bot      # Run bot (foreground with logs)
make setup-bot      # Install/update bot dependencies

# Database
psql postgresql://postgres:postgres@localhost:5432/clothify

# End-to-end test, bypassing Discord entirely.
# Inserts a single job and waits for the output file.
# ⚠ consumes API credit (~$0.05 per run)
bash scripts/e2e_test.sh <source_image> <garment> <genre> <size> <timeout_s>

# Switch image model (run on the Docker host)
sudo python3 scripts/switch_model.py --list
sudo python3 scripts/switch_model.py gpt-5.4-image-2
```

## 🔧 Architecture

**3-tier, decoupled through the database:**
- **Discord Bot** (Python/asyncpg) — user interface and job orchestration
- **PostgreSQL 16** — job queue with NOTIFY/LISTEN triggers
- **n8n** — workflow engine; **this is where the image model is called**

**Data flow:** Discord → Bot → PostgreSQL (NOTIFY) → n8n → OpenRouter → PostgreSQL → Bot → Discord

The bot never calls an image API. It writes a job row and polls for
`status = 'done'`. Swapping the AI provider requires no change to the Python
code — only to the n8n workflow.

## 📦 What lives in this repository

Everything needed to rebuild the system, including the parts that normally only
exist inside running containers:

| Path | Contents |
|---|---|
| `bot/` | Discord bot source (Python) |
| `n8n/workflows/*.json` | **Exported n8n workflows** — the generation logic |
| `Database/clothify_schema.sql` | **Real schema dump**: tables, enums, NOTIFY trigger |
| `Database/clothify_schema.dbml` | Same schema as an ER diagram source |
| `scripts/e2e_test.sh` | End-to-end test that bypasses Discord |
| `docs/` | Technical documentation |

> n8n workflows live in n8n's own database, so they are **not** version-controlled
> by default. After changing a workflow, re-export it:
> `n8n export:workflow --all --output=n8n/workflows/`

## 📚 Documentation

- **Agent instructions:** [AGENTS.md](AGENTS.md) — start here when working on the repo
- **Image generation pipeline:** [docs/IMAGE_GENERATION.md](docs/IMAGE_GENERATION.md) — API contract, costs, failure modes
- **System Architecture:** [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md) - Complete technical overview
- **Configuration Guide:** [docs/CONFIGURATION.md](docs/CONFIGURATION.md) - Environment setup and config management
- **Production Deployment:** [docs/PRODUCTION_DEPLOYMENT.md](docs/PRODUCTION_DEPLOYMENT.md) - Coolify deployment guide
- **Database Guide:** [Database/GUIDE_ACCES_local_database.md](Database/GUIDE_ACCES_local_database.md) - PostgreSQL connection details
- **n8n Workflows:** [n8n/workflows/README.md](n8n/workflows/README.md) - Workflow documentation

## 🤖 AI Agents

Repository-specific GitHub Copilot instructions: [.github/copilot-instructions.md](.github/copilot-instructions.md)

## 📝 License

Private project - Clothify Virtual Try-On Service
