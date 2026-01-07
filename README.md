# Clothify - Virtual Try-On Service

Discord bot + n8n workflow orchestrator for generating professional e-commerce product visuals powered by Google Gemini AI.

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Discord Bot Token ([Get one here](https://discord.com/developers/applications))
- Google AI API Key ([Get one here](https://aistudio.google.com/apikey))

### Installation

```bash
# 1. Clone and setup environment
cp .env.example .env
nano .env  # Configure DISCORD_TOKEN, GOOGLE_AI_API_KEY, etc.

# 2. Start infrastructure (PostgreSQL + n8n)
make start

# 3. Start Discord bot
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
```

## 📚 Documentation

- **System Architecture:** [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md) - Complete technical overview
- **Configuration Guide:** [docs/CONFIGURATION.md](docs/CONFIGURATION.md) - Environment setup and config management
- **Production Deployment:** [docs/PRODUCTION_DEPLOYMENT.md](docs/PRODUCTION_DEPLOYMENT.md) - Coolify deployment guide
- **Database Guide:** [Database/GUIDE_ACCES.md](Database/GUIDE_ACCES.md) - PostgreSQL connection details
- **n8n Workflows:** [n8n/workflows/README.md](n8n/workflows/README.md) - Workflow documentation

## 🔧 Architecture

**3-tier microservices:**
- **Discord Bot** (Python/asyncpg) - User interface and job orchestration
- **PostgreSQL 16** - Job queue with NOTIFY/LISTEN triggers
- **n8n** - Workflow engine for AI processing

**Data flow:** Discord → Bot → PostgreSQL (NOTIFY) → n8n → Google Gemini API → PostgreSQL → Bot → Discord

## 🤖 AI Agents

Repository-specific GitHub Copilot instructions: [.github/copilot-instructions.md](.github/copilot-instructions.md)

## 📝 License

Private project - Clothify Virtual Try-On Service
