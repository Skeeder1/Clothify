# Clothify - System Architecture Documentation

**Version:** 1.0  
**Date:** January 5, 2026  
**Purpose:** Knowledge Base for AI Agents & Development Team

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Business Workflow](#business-workflow)
3. [System Architecture](#system-architecture)
4. [Data Flow Diagram](#data-flow-diagram)
5. [Microservices Topology](#microservices-topology)
6. [Database Schema](#database-schema)
7. [File Storage & Volume Management](#file-storage--volume-management)
8. [Environment Configurations](#environment-configurations)
9. [Network Topology](#network-topology)
10. [Configuration Management](#configuration-management)
11. [Architectural Decisions](#architectural-decisions)
12. [Deployment Procedures](#deployment-procedures)

---

## Project Overview

**Clothify** is an automated Virtual Try-On service accessible via Discord. Users upload garment images, select product attributes (type and size), and receive AI-generated professional product images directly in their Discord channel.

### Key Capabilities

- **Input:** User uploads garment photo(s) via Discord
- **Processing:** AI-powered image generation using Google Gemini API
- **Output:** Professional product visualization delivered to Discord
- **Queue Management:** PostgreSQL-backed job queue with real-time notifications
- **Async Architecture:** Push-based workflow triggering via PostgreSQL NOTIFY/LISTEN

### Technology Stack

- **Bot Framework:** Python 3.11+ with `discord.py` (async)
- **Database:** PostgreSQL 16 with native NOTIFY/LISTEN triggers
- **Workflow Orchestrator:** n8n (self-hosted)
- **AI Generation:** Google Gemini API (originally designed for Banana.dev)
- **Container Runtime:** Docker + Docker Compose (local) / Coolify (production)
- **Networking:** Tailscale VPN (production secure access)

---

## Business Workflow

### End-to-End User Journey

```
1. UPLOAD
   User posts image(s) in #bot_clothify channel on Discord
   ↓
2. INTERACTIVE SELECTION
   Bot presents dropdown menu with 15 garment types
   User selects (e.g., "tshirt", "pull", "robe")
   ↓
   Bot presents size selection buttons
   User selects size: 1 (Petit), 2 (Standard), 3 (Moyen), 4 (Grand)
   ↓
3. JOB CREATION
   Bot saves image(s) to ./images/input/
   Generates unique 6-char product ID (e.g., "A3X7K2")
   Creates database record with status='pending'
   Adds ⏳ reaction to original message
   ↓
4. REAL-TIME TRIGGER
   PostgreSQL trigger fires NOTIFY event
   n8n receives instant notification via LISTEN channel
   ↓
5. AI PROCESSING
   n8n updates job status to 'processing'
   Reads input image from shared volume
   Calls Google Gemini API for generation
   Saves output to ./images/output/
   Calls complete_job() database function
   ↓
6. POLLING & DELIVERY
   Bot polls job status every 5 seconds (max 120s timeout)
   Detects output_file_path populated
   Reads generated image from ./images/output/
   Posts result to Discord thread/channel
   Updates job status to 'sent'
   Replaces ⏳ with ✅ reaction
```

### Workflow Timing

- **User Interaction:** ~10-30 seconds (upload + selections)
- **Queue Trigger:** <100ms (PostgreSQL NOTIFY is near-instant)
- **AI Generation:** Variable (typically 15-60 seconds depending on Gemini API)
- **Polling Detection:** 0-5 seconds (bot checks every 5s)
- **Total Time:** ~30-90 seconds from upload to delivery

---

## System Architecture

### Three-Tier Microservices Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                    │
│                   Discord (External)                     │
└────────────────────┬────────────────────────────────────┘
                     │ Webhooks/Gateway
┌────────────────────┴────────────────────────────────────┐
│                    APPLICATION LAYER                     │
│  ┌──────────────┐              ┌──────────────┐         │
│  │ Bot Service  │◄────────────►│  n8n Service │         │
│  │  (Python)    │   Shared Vol │ (Workflow)   │         │
│  └──────┬───────┘              └──────┬───────┘         │
│         │                              │                 │
└─────────┼──────────────────────────────┼─────────────────┘
          │         DATABASE LAYER       │
┌─────────┴──────────────────────────────┴─────────────────┐
│              PostgreSQL 16 Database                       │
│  ┌──────────┐  ┌──────────┐  ┌─────────────┐            │
│  │  users   │  │   jobs   │  │  job_logs   │            │
│  └──────────┘  └──────────┘  └─────────────┘            │
│                                                           │
│  Triggers: trg_n8n_new_job → NOTIFY → n8n_jobs_channel   │
└───────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

```mermaid
graph TB
    A[Discord User] -->|1. Upload Image| B[Bot Service]
    B -->|2. Save to /images/input/| C[Shared Volume]
    B -->|3. INSERT job status=pending| D[(PostgreSQL)]
    
    D -->|4. TRIGGER: NOTIFY n8n_jobs_channel| E[n8n Workflow]
    E -->|5. UPDATE status=processing| D
    E -->|6. Read input image| C
    E -->|7. API Call| F[Google Gemini API]
    F -->|8. Generated Image| E
    E -->|9. Save to /images/output/| C
    E -->|10. complete_job function| D
    
    D -->|11. Bot polls every 5s| B
    B -->|12. Read output image| C
    B -->|13. Post result| A
    B -->|14. UPDATE status=sent| D
    
    style A fill:#7289DA
    style B fill:#3498DB
    style D fill:#2ECC71
    style E fill:#E74C3C
    style F fill:#F39C12
    style C fill:#95A5A6
```

### Detailed Component Interaction

| Step | Component A | Action | Component B | Latency |
|------|-------------|--------|-------------|---------|
| 1 | Discord User | Upload image + message | Bot (`on_message`) | ~100ms |
| 2 | Bot | `save_attachment()` | Filesystem | ~50ms |
| 3 | Bot | `create_job()` INSERT | PostgreSQL | ~10ms |
| 4 | PostgreSQL | `notify_n8n_new_job()` NOTIFY | n8n (LISTEN) | <100ms |
| 5 | n8n | UPDATE `status='processing'` | PostgreSQL | ~10ms |
| 6 | n8n | Read file | Shared Volume | ~10ms |
| 7 | n8n | HTTP POST | Gemini API | 15-60s |
| 8 | Gemini API | Return image binary | n8n | 1-5s |
| 9 | n8n | Write file | Shared Volume | ~20ms |
| 10 | n8n | `complete_job()` function | PostgreSQL | ~15ms |
| 11 | Bot | `get_job_output()` poll | PostgreSQL | ~5ms (every 5s) |
| 12 | Bot | Read file | Shared Volume | ~10ms |
| 13 | Bot | Discord.File upload | Discord CDN | 500ms-2s |
| 14 | Bot | `update_job_status('sent')` | PostgreSQL | ~10ms |

---

## Microservices Topology

### Service A: Discord Bot (Python)

**Repository Path:** `bot/`

**Entry Point:** `bot/main.py`

**Key Components:**
- `bot/config.py` - Environment configuration loader
- `bot/database.py` - AsyncPG connection pool & query functions
- `bot/handlers/message.py` - Discord event handlers (`on_message`, `on_ready`)
- `bot/handlers/views.py` - Interactive UI (GarmentSelectView, SizeSelectView)
- `bot/handlers/tasks.py` - Background async tasks (polling, cleanup)
- `bot/utils/files.py` - File save/read utilities

**Dependencies:**
```
discord.py>=2.0.0
asyncpg>=0.27.0
python-dotenv>=1.0.0
```

**Responsibilities:**
1. Listen to Discord gateway events
2. Validate and save uploaded attachments
3. Present interactive UI for garment/size selection
4. Create job records in database
5. Poll database for job completion
6. Convert Docker paths to host paths
7. Send generated images to Discord
8. Update job statuses (sent, error, timeout)

**Communication:**
- **Inbound:** Discord Gateway (WebSocket)
- **Outbound:** PostgreSQL (asyncpg), Discord API (HTTPS), Filesystem (shared volumes)

---

### Service B: PostgreSQL Database

**Repository Path:** `Database/`

**Initialization:** `Database/scripts/init/01-schema.sql`

**Migrations:** `Database/scripts/migrations/00X_*.sql`

**Key Features:**
- UUID-based primary keys (`uuid_generate_v4()`)
- ENUM types for controlled vocabularies
- Trigger-based notifications (`NOTIFY/LISTEN`)
- Stored functions for business logic
- Automatic job status auditing via `job_logs`

**Responsibilities:**
1. Persist user data and job queue
2. Enforce data integrity (foreign keys, enums)
3. Trigger real-time notifications to n8n
4. Execute retry logic via `fail_job()` function
5. Reset stale jobs (>5 minutes in 'processing')
6. Provide queue statistics

**Communication:**
- **Inbound:** Bot (asyncpg), n8n (native PostgreSQL driver)
- **Outbound:** n8n (NOTIFY channel: `n8n_jobs_channel`)

---

### Service C: n8n Workflow Orchestrator

**Repository Path:** `n8n/workflows/`

**Configuration:** Workflows imported via UI, stored in `n8n-data` volume

**Key Workflows:**
1. **Main Processing Workflow:**
   - Trigger: PostgreSQL LISTEN on `n8n_jobs_channel`
   - Nodes: Status Update → Read File → Gemini API → Save File → Complete Job

**Responsibilities:**
1. Listen for PostgreSQL NOTIFY events
2. Update job status to 'processing'
3. Read input images from `/files/input/`
4. Call external AI API (Google Gemini)
5. Save generated images to `/files/output/`
6. Invoke `complete_job()` database function
7. Handle errors via `fail_job()` function

**Communication:**
- **Inbound:** PostgreSQL (NOTIFY/LISTEN), Filesystem (read input images)
- **Outbound:** Gemini API (HTTPS), Filesystem (write output images), PostgreSQL (function calls)

---

## Database Schema

### ER Diagram

```mermaid
erDiagram
    users ||--o{ jobs : "creates"
    jobs ||--o{ job_logs : "has audit trail"
    
    users {
        uuid id PK
        varchar discord_id UK
        varchar discord_username
        timestamp created_at
        timestamp last_seen_at
        integer total_jobs
        boolean is_active
    }
    
    jobs {
        uuid id PK
        uuid user_id FK
        varchar discord_message_id
        text custom_prompt
        text input_file_paths
        text output_file_path
        varchar product_name UK
        garment_type garment
        size_code size
        job_status status
        integer attempts
        integer max_attempts
        text error_message
        timestamp created_at
        timestamp started_at
        timestamp completed_at
    }
    
    job_logs {
        serial id PK
        uuid job_id FK
        job_status status
        text message
        timestamp logged_at
    }
```

### Tables

#### `users`

Stores Discord user information and usage statistics.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, DEFAULT uuid_generate_v4() | Internal user ID |
| `discord_id` | VARCHAR(20) | UNIQUE, NOT NULL | Discord snowflake ID |
| `discord_username` | VARCHAR(100) | - | Display name |
| `created_at` | TIMESTAMP | DEFAULT NOW() | First seen date |
| `last_seen_at` | TIMESTAMP | DEFAULT NOW() | Last activity |
| `total_jobs` | INTEGER | DEFAULT 0 | Lifetime job count |
| `is_active` | BOOLEAN | DEFAULT TRUE | Soft delete flag |

**Indexes:**
- `idx_users_discord_id` on `discord_id`

---

#### `jobs`

Core job queue table tracking all Virtual Try-On requests.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, DEFAULT uuid_generate_v4() | Job ID |
| `user_id` | UUID | FK → users.id | Requester |
| `discord_message_id` | VARCHAR(20) | - | Original message reference |
| `custom_prompt` | TEXT | - | Optional user text |
| `input_file_paths` | TEXT | NOT NULL | JSON array string of input paths |
| `output_file_path` | TEXT | - | Generated image path (Docker format) |
| `product_name` | VARCHAR(255) | UNIQUE, NOT NULL | 6-char alphanumeric ID |
| `garment` | garment_type | NOT NULL | Selected garment type |
| `size` | size_code | NOT NULL | Selected size (1-4) |
| `status` | job_status | DEFAULT 'pending' | Current state |
| `attempts` | INTEGER | DEFAULT 0 | Retry counter |
| `max_attempts` | INTEGER | DEFAULT 3 | Retry limit |
| `error_message` | TEXT | - | Failure reason |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Queue entry time |
| `started_at` | TIMESTAMP | - | Processing start |
| `completed_at` | TIMESTAMP | - | Done/error time |

**Indexes:**
- `idx_jobs_status` on `status`
- `idx_jobs_user_id` on `user_id`
- `idx_jobs_created_at` on `created_at`

---

#### `job_logs`

Audit trail for job status transitions.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | SERIAL | PK | Log entry ID |
| `job_id` | UUID | FK → jobs.id ON DELETE CASCADE | Associated job |
| `status` | job_status | NOT NULL | New status |
| `message` | TEXT | - | Context/error details |
| `logged_at` | TIMESTAMP | DEFAULT NOW() | Transition time |

**Indexes:**
- `idx_job_logs_job_id` on `job_id`

---

### ENUMs

#### `job_status`

```sql
CREATE TYPE job_status AS ENUM (
    'pending',      -- Awaiting n8n processing
    'processing',   -- Currently being processed by n8n
    'done',         -- Output generated, awaiting delivery
    'error',        -- Failed (max retries exceeded)
    'sent'          -- Delivered to Discord user
);
```

#### `garment_type`

```sql
CREATE TYPE garment_type AS ENUM (
    'echarpe', 'pull', 'tshirt', 'chemise', 'veste', 
    'manteau', 'pantalon', 'jean', 'short', 'jupe', 
    'robe', 'bonnet', 'casquette', 'sac', 'other'
);
```

#### `size_code`

```sql
CREATE TYPE size_code AS ENUM ('1', '2', '3', '4');
-- Mapping: 1=Petit, 2=Standard, 3=Moyen, 4=Grand
```

---

### Database Functions

#### `complete_job(p_job_id UUID, p_output_path TEXT)`

Marks a job as successfully completed.

**Actions:**
- Sets `status='done'`
- Sets `output_file_path=p_output_path`
- Sets `completed_at=NOW()`
- Inserts audit log

**Called by:** n8n workflow after successful generation

---

#### `fail_job(p_job_id UUID, p_error_msg TEXT)`

Handles job failures with automatic retry logic.

**Logic:**
- Increments `attempts`
- If `attempts < max_attempts`: Sets `status='pending'` (retry)
- If `attempts >= max_attempts`: Sets `status='error'` (permanent failure)
- Sets `error_message=p_error_msg`
- Inserts audit log

**Called by:** n8n workflow on errors, bot on timeouts

---

#### `reset_stale_jobs(timeout_minutes INTEGER DEFAULT 5)`

Resets jobs stuck in 'processing' state.

**Logic:**
- Finds jobs with `status='processing'` AND `started_at < NOW() - timeout_minutes`
- Resets to `status='pending'`
- Clears `started_at`
- Useful for recovery after n8n crashes

**Called by:** Manual maintenance or scheduled job (not currently automated)

---

#### `get_queue_stats()`

Returns job counts by status.

**Returns:**
```sql
(pending INTEGER, processing INTEGER, done INTEGER, error INTEGER)
```

**Called by:** Bot `!stats` command (if implemented), monitoring dashboards

---

#### `notify_n8n_new_job()`

Trigger function that sends NOTIFY events.

**Actions:**
- Constructs JSON payload with job details
- Executes `NOTIFY n8n_jobs_channel, '<json_payload>'`

**Triggered by:** `trg_n8n_new_job` AFTER INSERT on `jobs`

---

### Triggers

#### `trg_n8n_new_job`

```sql
CREATE TRIGGER trg_n8n_new_job
    AFTER INSERT ON jobs
    FOR EACH ROW
    EXECUTE FUNCTION notify_n8n_new_job();
```

**Purpose:** Instantly notify n8n when new jobs are created (push-based architecture)

**Payload Example:**
```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "user_id": "987fcdeb-51a2-43d7-9876-543210fedcba",
  "discord_message_id": "1234567890123456789",
  "product_name": "A3X7K2",
  "garment": "tshirt",
  "size": "2",
  "input_file_paths": "[\"./images/input/tshirt.jpg\"]",
  "custom_prompt": "white background"
}
```

---

## File Storage & Volume Management

### Directory Structure

```
/home/luffy/Github/Clothify/
├── images/                         # Shared volume root
│   ├── input/                      # User-uploaded images
│   │   └── (dynamic files)         # e.g., tshirt_1.jpg
│   └── output/                     # AI-generated images
│       └── (dynamic files)         # e.g., A3X7K2.jpg
├── bot/                            # Bot service code
├── Database/scripts/init/          # SQL init scripts
├── n8n/workflows/                  # Workflow definitions (JSON)
├── docker-compose.yml              # Local orchestration
└── .env                            # Local environment config
```

### Volume Mappings

#### Local Development

| Service | Container Path | Host Path | Purpose |
|---------|----------------|-----------|---------|
| Bot | N/A (runs on host) | `./images/input/` | Write uploads |
| Bot | N/A (runs on host) | `./images/output/` | Read results |
| n8n | `/files/input/` | `./images/input/` | Read uploads |
| n8n | `/files/output/` | `./images/output/` | Write results |
| postgres | `/docker-entrypoint-initdb.d` | `./Database/scripts/init/` | Schema init |
| postgres | `/var/lib/postgresql/data` | `postgres-data` (named volume) | Data persistence |
| n8n | `/home/node/.n8n` | `n8n-data` (named volume) | Workflow storage |

#### Production (Coolify)

| Service | Container Path | Coolify Volume | Purpose |
|---------|----------------|----------------|---------|
| Bot | `/app/images/input/` | Coolify persistent volume | Write uploads |
| Bot | `/app/images/output/` | Coolify persistent volume | Read results |
| n8n | `/files/input/` | Coolify persistent volume | Read uploads |
| n8n | `/files/output/` | Coolify persistent volume | Write results |
| postgres | `/var/lib/postgresql/data` | Coolify database volume | Data persistence |
| n8n | `/home/node/.n8n` | Coolify app volume | Workflow storage |

> **Note:** In production, Coolify manages volume creation and binding automatically via its UI.

---

### Path Translation

#### Bot Path Converter

**Function:** `docker_to_host_path()` in `bot/utils/files.py`

**Purpose:** Convert n8n's Docker-internal paths to bot-accessible paths

**Example:**
```python
# n8n saves: /files/output/A3X7K2.jpg (inside container)
# Database stores: /files/output/A3X7K2.jpg
# Bot converts to: ./images/output/A3X7K2.jpg (host filesystem)

docker_path = "/files/output/A3X7K2.jpg"
host_path = docker_to_host_path(docker_path)
# Result: "./images/output/A3X7K2.jpg"
```

**Local Logic:**
- Strip `/files/` prefix
- Prepend `./images/`

**Production Logic:** (Handled by Coolify volume mounts)
- All services see consistent paths via shared persistent volume

---

### File Naming Conventions

**Input Files:**
- Original filename preserved: `shirt.jpg`
- Duplicates get counter suffix: `shirt_1.jpg`, `shirt_2.jpg`
- Saved by: `save_attachment()` in `bot/utils/files.py`

**Output Files:**
- Named by product ID: `{product_name}.jpg` (e.g., `A3X7K2.jpg`)
- Product name: 6-char alphanumeric generated by `generate_unique_product_id()`
- Uniqueness enforced by database UNIQUE constraint on `jobs.product_name`

**Supported Extensions:**
```python
SUPPORTED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp']
```

---

## Environment Configurations

### Comparison: LOCAL vs PRODUCTION

| Aspect | LOCAL (Development) | PRODUCTION (Deployed) |
|--------|---------------------|----------------------|
| **Host Machine** | PC Personnel (Developer laptop/desktop) | Debian Server (Home Lab) |
| **Orchestration** | `docker-compose` (manual) | Coolify (Web UI) |
| **Network Type** | Docker bridge (default) | Coolify-managed Docker network |
| **Bot Deployment** | Runs on host (`python bot/main.py`) | Dockerized via Coolify |
| **Database Access** | `localhost:5432` (port mapping) | Internal DNS (`postgres:5432`) or Coolify service name |
| **n8n Access** | `localhost:5678` (port mapping) | Internal DNS (`n8n:5678`) or Coolify service name |
| **Configuration Source** | `.env` file in project root | Coolify UI (Environment Variables section) |
| **Volume Storage** | Host filesystem (`./images/`) | Coolify persistent volumes (managed) |
| **External Access** | Not exposed (local only) | Tailscale VPN (100.x.x.x private IPs) |
| **Port Exposure** | Public ports mapped (5432, 5678) | NO public ports (Tailscale mesh only) |
| **Service Discovery** | Hostname in `.env` (e.g., `postgres`, `localhost`) | Coolify internal DNS |
| **Secrets Management** | `.env` file (not committed to git) | Coolify encrypted environment variables |
| **Log Access** | `docker-compose logs -f` | Coolify Web UI (Logs tab) |
| **Restart Strategy** | Manual (`docker-compose restart`) | Automatic (Coolify health checks + restarts) |
| **Backup Strategy** | Manual (`pg_dump`, volume copy) | Coolify automatic volume snapshots (if configured) |

---

## Network Topology

### Local Environment Network

```
┌────────────────────────────────────────────────────────────┐
│                     Host Machine (PC)                      │
│                                                            │
│  ┌──────────────┐                                         │
│  │  Bot Process │  (Python, asyncpg)                      │
│  │  Port: N/A   │                                         │
│  └──────┬───────┘                                         │
│         │                                                  │
│         │ localhost:5432 (port mapping)                   │
│         │                                                  │
│  ┌──────┴────────────────────────────────────────────┐    │
│  │         Docker Bridge Network (default)           │    │
│  │                                                    │    │
│  │  ┌──────────────┐       ┌──────────────┐         │    │
│  │  │  postgres    │       │     n8n      │         │    │
│  │  │  Port: 5432  │◄─────►│  Port: 5678  │         │    │
│  │  └──────────────┘       └──────────────┘         │    │
│  │         │                        │                │    │
│  │         └────────────────────────┘                │    │
│  │          Internal: postgres:5432                  │    │
│  └───────────────────────────────────────────────────┘    │
│                                                            │
│  Volumes:                                                  │
│  • postgres-data (named)                                   │
│  • n8n-data (named)                                        │
│  • ./images/input/ → n8n:/files/input/ (bind mount)       │
│  • ./images/output/ → n8n:/files/output/ (bind mount)     │
└────────────────────────────────────────────────────────────┘
```

**Characteristics:**
- Bot runs directly on host (not containerized locally)
- Services communicate via `localhost` (host) or container names (internal)
- Port 5432 and 5678 exposed to host for development access
- File sharing via bind mounts (host ↔ container)

---

### Production Environment Network

```
                    ┌─────────────────────┐
                    │   Public Internet   │
                    └──────────┬──────────┘
                               │
                               │ (NO EXPOSED PORTS)
                               │
                    ┌──────────┴──────────┐
                    │  Tailscale Mesh VPN  │
                    │  (Encrypted Overlay)  │
                    └──────────┬──────────┘
                               │
                       100.x.x.x (private IP)
                               │
┌──────────────────────────────┴───────────────────────────────┐
│              Debian Home Lab Server (Tailscale Node)         │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐   │
│  │                  Coolify PaaS Layer                   │   │
│  │                                                        │   │
│  │  ┌─────────────────────────────────────────────────┐  │   │
│  │  │     Coolify-Managed Docker Network              │  │   │
│  │  │                                                  │  │   │
│  │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐     │  │   │
│  │  │  │   Bot    │  │ postgres │  │   n8n    │     │  │   │
│  │  │  │Container │◄─┤Container │─►│Container │     │  │   │
│  │  │  └────┬─────┘  └──────────┘  └────┬─────┘     │  │   │
│  │  │       │                             │           │  │   │
│  │  │       └─────────────┬───────────────┘           │  │   │
│  │  │                     │                           │  │   │
│  │  │         Shared Persistent Volume                │  │   │
│  │  │         (Coolify-managed)                       │  │   │
│  │  └─────────────────────────────────────────────────┘  │   │
│  │                                                        │   │
│  │  Service Discovery: Internal DNS                      │   │
│  │  • postgres.coolify.internal                          │   │
│  │  • n8n.coolify.internal                               │   │
│  │  • bot.coolify.internal                               │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                               │
│  Host Firewall: ALL PORTS CLOSED (except Tailscale)          │
└───────────────────────────────────────────────────────────────┘
```

**Characteristics:**
- **Zero Trust Access:** No public ports exposed; all access via Tailscale VPN
- **Private Mesh Network:** Tailscale assigns 100.x.x.x IP range (CGNAT)
- **Coolify Orchestration:** Manages container lifecycle, networking, volumes
- **Internal DNS:** Services resolve each other via Coolify's DNS (e.g., `postgres:5432`)
- **Persistent Volumes:** Coolify-managed volumes shared across services
- **Automatic SSL/TLS:** Tailscale provides encrypted transport (WireGuard)

---

### Tailscale Integration (Production Only)

**What is Tailscale?**
- Zero-config VPN based on WireGuard protocol
- Creates secure mesh network (peer-to-peer)
- Each device gets private 100.x.x.x IP
- No port forwarding or firewall rules needed
- Devices appear as if on local LAN

**Clothify Usage:**
1. **Server Node:** Debian Home Lab server runs Tailscale client
2. **Developer Node:** Developer laptop/PC runs Tailscale client
3. **Mesh Connection:** Both nodes can reach each other via private IPs
4. **Service Access:** Developer accesses Coolify UI at `http://100.x.x.x:8000` (example)
5. **Database Access:** Optional direct connection to Postgres at `100.x.x.x:5432` (if needed)

**Security Benefits:**
- Server firewall blocks all public ports (ufw deny all)
- Only Tailscale (UDP 41641) allowed through firewall
- End-to-end encryption (WireGuard)
- ACLs can restrict which Tailscale users access which services

**Example Tailscale ACL:**
```json
{
  "acls": [
    {
      "action": "accept",
      "src": ["developer@example.com"],
      "dst": ["homelab-server:*"]
    }
  ]
}
```

---

## Configuration Management

### Environment Variables

#### Bot Service

**File:** `.env` (local) or Coolify UI (production)

**Required Variables:**

```bash
# Discord Configuration
DISCORD_TOKEN=<bot_token_from_discord_dev_portal>

# Database Connection
DATABASE_URL=postgresql://<user>:<password>@<host>:<port>/<database>
# Example (local): postgresql://postgres:postgres@localhost:5432/clothify
# Example (prod):  postgresql://postgres:postgres@postgres:5432/clothify

# File Paths
INPUT_DIR=./images/input    # Local path (bot reads/writes here)
OUTPUT_DIR=./images/output  # Local path (bot reads generated images)

# Job Polling Configuration
WATCH_INTERVAL=5            # Seconds between job status checks
WATCH_TIMEOUT=120           # Max seconds to wait for job completion
```

**Loading Mechanism:**
- `bot/config.py` uses `python-dotenv` to load `.env`
- Variables accessed via `os.getenv()`
- Validation performed in `Config.validate()` method

---

#### n8n Service

**File:** `docker-compose.yml` (local) or Coolify Environment Variables (production)

**Required Variables:**

```bash
# Localization
GENERIC_TIMEZONE=Europe/Paris
TZ=Europe/Paris

# Security
N8N_ENCRYPTION_KEY=<random_32_char_string>  # For encrypting credentials

# External API
GOOGLE_AI_API_KEY=<gemini_api_key>          # For AI image generation

# Discord (optional, if using Discord nodes)
DISCORD_TOKEN=<same_as_bot_token>

# Database Connection (n8n internal)
DB_POSTGRESDB_HOST=postgres                 # Container name or Coolify DNS
DB_POSTGRESDB_PORT=5432
DB_POSTGRESDB_DATABASE=clothify
DB_POSTGRESDB_USER=postgres
DB_POSTGRESDB_PASSWORD=postgres
```

---

#### PostgreSQL Service

**File:** `docker-compose.yml` (local) or Coolify UI (production)

**Required Variables:**

```bash
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres  # Change in production!
POSTGRES_DB=clothify
```

**Initialization:**
- Scripts in `./Database/scripts/init/` run automatically on first start
- Migrations in `./Database/scripts/migrations/` must be run manually

---

### Configuration Best Practices

#### 1. Environment-Agnostic Code

**✅ CORRECT:**
```python
import os
from bot.config import Config

db_url = Config.DATABASE_URL  # Loaded from os.getenv()
```

**❌ INCORRECT:**
```python
db_url = "postgresql://postgres:postgres@localhost:5432/clothify"  # Hardcoded!
```

---

#### 2. Path Handling

**✅ CORRECT:**
```python
input_dir = Config.INPUT_DIR  # From environment
output_path = os.path.join(Config.OUTPUT_DIR, filename)
```

**❌ INCORRECT:**
```python
output_path = "/home/luffy/Github/Clothify/images/output/file.jpg"  # Hardcoded!
```

---

#### 3. Service Discovery

**✅ CORRECT (docker-compose.yml):**
```yaml
DATABASE_URL: postgresql://postgres:postgres@postgres:5432/clothify
```
Uses container name `postgres` which Docker resolves automatically.

**❌ INCORRECT:**
```yaml
DATABASE_URL: postgresql://postgres:postgres@192.168.1.100:5432/clothify
```
Hardcoded IP will break in different environments.

---

## Architectural Decisions

### 1. Push-Based Job Notifications (NOTIFY/LISTEN)

**Decision:** Use PostgreSQL's native `NOTIFY/LISTEN` instead of polling.

**Rationale:**
- **Latency:** Sub-100ms vs 5-60 second polling intervals
- **Resource Efficiency:** No wasted database queries
- **Scalability:** NOTIFY supports multiple listeners without load multiplication
- **Real-time:** Jobs start processing immediately upon creation

**Migration History:**
- **v1 (Original):** n8n polled `jobs` table every 10 seconds for `status='pending'`
- **v2 (002_add_queue_system.sql):** Added `locked_by`, `locked_at` for distributed locking
- **v3 (003_add_n8n_notify_trigger.sql):** Introduced `NOTIFY/LISTEN` trigger
- **v4 (004_cleanup_polling_elements.sql):** Removed polling artifacts (`locked_by`, `take_next_job()`)

**Implementation:**
- `Database/scripts/migrations/003_add_n8n_notify_trigger.sql` adds trigger
- n8n workflow uses PostgreSQL Trigger node (not Polling node)
- Channel name: `n8n_jobs_channel`

---

### 2. Hybrid Completion Detection (Bot Still Polls)

**Decision:** Bot polls for job completion; n8n uses push notifications.

**Rationale:**
- **Simplicity:** Bot polling logic already exists and works reliably
- **Decoupling:** Bot doesn't need to maintain WebSocket or LISTEN connection
- **Short Duration:** Poll interval is 5s with 120s timeout (max 24 checks)
- **Future Optimization:** Could add NOTIFY for completion, but current performance acceptable

**Trade-off Analysis:**
- **Pros:** Simple, stateless bot, no persistent connections
- **Cons:** 0-5 second delay in user notification (acceptable for UX)

---

### 3. Shared Volume Architecture

**Decision:** Use filesystem volumes instead of S3/object storage.

**Rationale:**
- **Simplicity:** No external dependencies, no API calls
- **Cost:** Free (no S3 charges)
- **Performance:** Local disk I/O faster than network requests
- **Development:** Easy to inspect files during debugging

**Limitations:**
- Not suitable for multi-region deployment
- Requires persistent volumes in production (handled by Coolify)

**Future Consideration:** Could migrate to S3-compatible storage (MinIO, Backblaze B2) if horizontal scaling needed.

---

### 4. Python Async Throughout

**Decision:** Use `asyncio` for all I/O operations.

**Rationale:**
- **Discord.py Requirement:** discord.py is async-native
- **Concurrency:** Handle multiple users simultaneously without threads
- **Database:** `asyncpg` provides non-blocking queries
- **File I/O:** Use `aiofiles` for non-blocking reads/writes (if implemented)

**Implementation:**
- `bot/main.py`: `@bot.event async def on_message()`
- `bot/database.py`: `async def create_job()`, `async def get_job_output()`
- `bot/handlers/tasks.py`: `async def watch_job_status()`

---

### 5. Interactive UI (Discord Views)

**Decision:** Use discord.py Select/Button components instead of command-based input.

**Rationale:**
- **UX:** Dropdown menus and buttons more intuitive than text commands
- **Validation:** Enforces valid choices (enum values)
- **Discoverability:** Users see available options
- **Error Prevention:** No typos or invalid inputs

**Implementation:**
- `bot/handlers/views.py`: `GarmentSelectView`, `SizeSelectView`
- Timeout: 300 seconds (5 minutes)
- Session tracking: `pending_uploads` dict keyed by `user_id`

---

### 6. Unique Product IDs

**Decision:** Generate 6-character alphanumeric IDs instead of UUIDs.

**Rationale:**
- **User-Friendly:** Easy to reference in support ("Can you check product A3X7K2?")
- **Filename Compatibility:** Short, no special characters
- **Collision Avoidance:** 36^6 = 2.17 billion combinations (sufficient for use case)
- **Database Enforcement:** UNIQUE constraint prevents duplicates

**Implementation:**
- `bot/handlers/views.py`: `generate_unique_product_id()` function
- Retry logic if collision detected (highly unlikely)
- Used as filename for output images

---

## Deployment Procedures

### Local Development Deployment

#### Initial Setup

```bash
# 1. Clone repository
git clone https://github.com/Skeeder1/Clothify.git
cd Clothify

# 2. Create .env file
cp .env.example .env
nano .env  # Edit with your tokens and config

# 3. Start Docker services
docker-compose up -d

# 4. Verify services
docker-compose ps
docker-compose logs -f postgres  # Check database initialization
docker-compose logs -f n8n       # Check n8n startup

# 5. Access n8n UI
open http://localhost:5678

# 6. Import workflows
# Navigate to n8n UI → Workflows → Import from File
# Select n8n/workflows/*.json

# 7. Configure n8n credentials
# Add PostgreSQL credentials in n8n UI (Settings → Credentials)
# Add Google AI API key

# 8. Install Python dependencies
cd bot
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 9. Run bot
python main.py

# 10. Test in Discord
# Post an image in configured channel
```

---

#### Running Commands

```bash
# View logs
docker-compose logs -f postgres
docker-compose logs -f n8n

# Restart services
docker-compose restart postgres
docker-compose restart n8n

# Stop all
docker-compose down

# Stop and remove volumes (DESTRUCTIVE - deletes database!)
docker-compose down -v

# Database shell access
docker-compose exec postgres psql -U postgres -d clothify

# Run migrations
docker-compose exec postgres psql -U postgres -d clothify -f /migrations/002_add_queue_system.sql
```

---

### Production Deployment (Coolify)

#### Pre-Requisites

1. **Tailscale Setup:**
   - Install Tailscale on home lab server: `curl -fsSL https://tailscale.com/install.sh | sh`
   - Authenticate: `sudo tailscale up`
   - Note server IP: `tailscale ip -4`

2. **Coolify Installation:**
   - Follow official guide: https://coolify.io/docs/installation
   - Access UI: `http://<tailscale-ip>:8000`

---

#### Deployment Steps

**1. Create New Project in Coolify:**
- Dashboard → New Project → Name: "Clothify"

**2. Add PostgreSQL Database:**
- Add Resource → Database → PostgreSQL 16
- Configuration:
  - Name: `clothify-db`
  - Database: `clothify`
  - User: `postgres`
  - Password: `<generate-strong-password>`
  - Persistent Storage: ✅ Enabled
- Deploy

**3. Run Database Initialization:**
- Coolify → `clothify-db` → Terminal
- Execute:
  ```bash
  psql -U postgres -d clothify
  \i /path/to/01-schema.sql  # Upload via Coolify file manager
  \i /path/to/002_add_queue_system.sql
  \i /path/to/003_add_n8n_notify_trigger.sql
  \i /path/to/004_cleanup_polling_elements.sql
  \q
  ```

**4. Add n8n Service:**
- Add Resource → Docker Compose → Import existing `docker-compose.yml` (n8n section only)
- OR: Add Resource → Application → n8n (from Coolify templates)
- Configuration:
  - Name: `clothify-n8n`
  - Image: `n8nio/n8n:latest`
  - Persistent Volumes:
    - `/home/node/.n8n` → Coolify managed volume
    - `/files/input` → Shared volume (create new: `clothify-images-input`)
    - `/files/output` → Shared volume (create new: `clothify-images-output`)
  - Environment Variables:
    - `N8N_ENCRYPTION_KEY`: `<generate-random-key>`
    - `GOOGLE_AI_API_KEY`: `<your-gemini-key>`
    - `DB_POSTGRESDB_HOST`: `clothify-db` (Coolify internal DNS)
    - `DB_POSTGRESDB_DATABASE`: `clothify`
    - `DB_POSTGRESDB_USER`: `postgres`
    - `DB_POSTGRESDB_PASSWORD`: `<from-step-2>`
    - `GENERIC_TIMEZONE`: `Europe/Paris`
    - `TZ`: `Europe/Paris`
  - Port: `5678` (optional, for Tailscale access)
- Deploy

**5. Import n8n Workflows:**
- Access n8n: `http://<tailscale-ip>:5678`
- Workflows → Import from File
- Upload all JSON files from `n8n/workflows/`
- Configure credentials (PostgreSQL, Google AI)
- Activate workflows

**6. Add Bot Service:**
- Add Resource → Application → Dockerfile
- Repository: `https://github.com/Skeeder1/Clothify` (or private Git repo)
- Dockerfile Path: `bot/Dockerfile`
- Build Context: `./bot`
- Persistent Volumes:
  - `/app/images/input` → Shared volume: `clothify-images-input` (same as n8n)
  - `/app/images/output` → Shared volume: `clothify-images-output` (same as n8n)
- Environment Variables:
  - `DISCORD_TOKEN`: `<your-discord-bot-token>`
  - `DATABASE_URL`: `postgresql://postgres:<password>@clothify-db:5432/clothify`
  - `INPUT_DIR`: `/app/images/input`
  - `OUTPUT_DIR`: `/app/images/output`
  - `WATCH_INTERVAL`: `5`
  - `WATCH_TIMEOUT`: `120`
- Deploy

**7. Verify Deployment:**
- Check service health: Coolify → Services → Status (all green)
- Check logs: Each service → Logs tab
- Test Discord bot: Post image in configured channel

---

#### Post-Deployment Maintenance

**Database Backups:**
```bash
# Manual backup (via Tailscale SSH)
docker exec clothify-db pg_dump -U postgres clothify > backup_$(date +%Y%m%d).sql

# Automatic backups: Configure in Coolify UI → Database → Backups
```

**Monitoring:**
- Coolify provides basic health checks
- Consider adding: Uptime Kuma, Prometheus + Grafana (if needed)

**Updates:**
- Coolify auto-pulls latest images (configure in UI)
- For database migrations: Use Coolify Terminal or SSH access

---

## Appendix

### A. Key Files Reference

| File Path | Purpose |
|-----------|---------|
| `bot/main.py` | Bot entry point, Discord client setup |
| `bot/config.py` | Environment variable loader |
| `bot/database.py` | Database connection pool and query functions |
| `bot/handlers/message.py` | Discord message event handlers |
| `bot/handlers/views.py` | Interactive UI components (Select/Button) |
| `bot/handlers/tasks.py` | Background polling tasks |
| `bot/utils/files.py` | File save/load utilities |
| `Database/scripts/init/01-schema.sql` | Database schema initialization |
| `Database/scripts/migrations/002_*.sql` | Database migration scripts |
| `docker-compose.yml` | Local orchestration configuration |
| `n8n/workflows/*.json` | n8n workflow definitions |

---

### B. Common Troubleshooting

**Problem:** Bot can't connect to database

**Solution:**
- Local: Check `DATABASE_URL` in `.env`, ensure `postgres` container is running
- Prod: Verify Coolify service names, check network connectivity

---

**Problem:** n8n doesn't receive job notifications

**Solution:**
- Verify trigger is installed: `SELECT * FROM pg_trigger WHERE tgname = 'trg_n8n_new_job';`
- Check n8n workflow is active (toggle in UI)
- Verify PostgreSQL credentials in n8n match database config

---

**Problem:** Bot times out waiting for job completion

**Solution:**
- Check n8n logs for errors
- Verify Gemini API key is valid
- Check shared volume permissions (must be writable by n8n)
- Manually check job status: `SELECT * FROM jobs WHERE id='<job_id>';`

---

**Problem:** Images not found after generation

**Solution:**
- Verify path translation: `docker_to_host_path()` logic
- Check volume mounts in `docker-compose.yml` or Coolify config
- Ensure output directory exists and is writable

---

### C. Glossary

| Term | Definition |
|------|------------|
| **Discord Snowflake** | Unique 64-bit ID used by Discord for all entities (messages, users, channels) |
| **NOTIFY/LISTEN** | PostgreSQL's pub/sub mechanism for real-time event notifications |
| **Tailscale** | Zero-config VPN service based on WireGuard protocol |
| **Coolify** | Self-hosted Platform-as-a-Service for Docker container management |
| **Garment Type** | Clothing category enum (e.g., tshirt, robe, pantalon) |
| **Size Code** | Size selection enum (1=Petit, 2=Standard, 3=Moyen, 4=Grand) |
| **Product Name** | Unique 6-character alphanumeric identifier for each job |
| **Job Status** | State enum (pending, processing, done, error, sent) |
| **asyncpg** | Asynchronous PostgreSQL driver for Python |
| **discord.py** | Python library for Discord bot development |

---

### D. External API Documentation

**Google Gemini API:**
- Documentation: https://ai.google.dev/docs
- Rate Limits: Varies by plan (check API console)
- Error Codes: 400 (Bad Request), 401 (Unauthorized), 429 (Rate Limit), 500 (Server Error)

**Note:** Originally designed for Banana.dev API; migration path available if needed.

---

### E. Future Enhancements

1. **Completion Notifications:** Add PostgreSQL NOTIFY for job completion (eliminate bot polling)
2. **Horizontal Scaling:** Migrate to S3-compatible storage for multi-instance deployments
3. **Queue Priority:** Add priority field for VIP users or rush jobs
4. **Retry Strategies:** Implement exponential backoff for API rate limits
5. **Monitoring:** Integrate Prometheus + Grafana for metrics
6. **Admin Dashboard:** Build web UI for queue management and statistics
7. **Multi-Language:** Support English translations alongside French UI

---

**Document Revision History:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-05 | System Architecture Team | Initial comprehensive documentation |

---

**End of Document**
