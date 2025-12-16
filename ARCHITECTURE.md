# CLOTHIFY - Architecture Documentation

## Overview

Clothify is a Discord bot that generates e-commerce product images using AI. Users send clothing photos, and the system returns professional model photos wearing the garments.

## System Components

| Component | Technology | Role |
|-----------|------------|------|
| Client | Discord User | Sends images + parameters |
| Discord Bot | Python (discord.py) | Receives messages, saves files, polls results |
| Database | PostgreSQL | Stores jobs and status |
| Workflow | n8n | Orchestrates image generation |
| AI Model | Google Gemini (gemini-2.0-flash-preview-image-generation) | Generates images |

## Architecture Flow

```
┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│   CLIENT    │   │ DISCORD BOT │   │ POSTGRESQL  │   │     N8N     │
└──────┬──────┘   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘
       │                 │                 │                 │
       │  1. Send msg    │                 │                 │
       │  [garment,      │                 │                 │
       │   size,         │                 │                 │
       │   pictures[],   │                 │                 │
       │   prompt]       │                 │                 │
       ├────────────────▶│                 │                 │
       │                 │                 │                 │
       │                 │  2. INSERT job  │                 │
       │                 │  status=pending │                 │
       │                 ├────────────────▶│                 │
       │                 │                 │                 │
       │                 │                 │  3. poll/trigger│
       │                 │                 │◀────────────────┤
       │                 │                 │                 │
       │                 │                 │  4. UPDATE      │
       │                 │                 │  status=        │
       │                 │                 │  processing     │
       │                 │                 ├────────────────▶│
       │                 │                 │                 │
       │                 │                 │        5. 🍌    │
       │                 │                 │     NanoBanana  │
       │                 │                 │     (generate)  │
       │                 │                 │                 │
       │                 │                 │  6. UPDATE      │
       │                 │                 │  status=done    │
       │                 │                 │  output_path    │
       │                 │                 │◀────────────────┤
       │                 │                 │                 │
       │                 │  7. poll done   │                 │
       │                 │◀────────────────┤                 │
       │                 │                 │                 │
       │  8. output_image│                 │                 │
       │◀────────────────┤                 │                 │
       │                 │                 │                 │
       │                 │  9. UPDATE      │                 │
       │                 │  status=sent    │                 │
       │                 ├────────────────▶│                 │
       │                 │                 │                 │
```

## Database Schema

### Enums

```sql
job_status: pending | processing | done | error | sent
garment_type: echarpe | pull | tshirt | chemise | veste | manteau | pantalon | jean | short | jupe | robe | bonnet | casquette | sac | other
size_code: 1 (XS) | 2 (S/M) | 3 (L) | 4 (XL)
```

### Tables

#### users
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| discord_id | VARCHAR(20) | Discord user ID (unique) |
| discord_name | VARCHAR(100) | Display name |
| created_at | TIMESTAMP | Account creation |
| last_seen_at | TIMESTAMP | Last activity |
| total_jobs | INTEGER | Job counter |
| is_active | BOOLEAN | Active status |

#### jobs
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | Foreign key → users |
| discord_message_id | VARCHAR(20) | Original message ID |
| custom_prompt | TEXT | User-provided prompt (optional) |
| input_file_paths | TEXT[] | Array of input image paths |
| output_file_path | TEXT | Generated image path |
| product_name | VARCHAR(255) | Product name from filename |
| garment | garment_type | Type of clothing |
| size | size_code | Size category |
| status | job_status | Current status |
| error_message | TEXT | Error details if failed |
| created_at | TIMESTAMP | Job creation |
| started_at | TIMESTAMP | Processing start |
| completed_at | TIMESTAMP | Processing end |

#### job_logs
| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| job_id | UUID | Foreign key → jobs |
| status | job_status | Status at this point |
| message | TEXT | Log message |
| created_at | TIMESTAMP | Log timestamp |

## File Structure

```
clothify/
├── bot/
│   ├── main.py              # Discord bot entry point
│   ├── commands/            # Bot commands
│   └── utils/               # Helper functions
├── images/
│   ├── input/               # User-uploaded images
│   └── output/              # Generated images
├── n8n/
│   └── workflows/           # n8n workflow exports
├── database/
│   └── schema.sql           # PostgreSQL schema
├── docker-compose.yml       # Docker configuration
└── .env                     # Environment variables
```

## Environment Variables

```env
# Discord
DISCORD_BOT_TOKEN=xxx

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=clothify
POSTGRES_USER=clothify
POSTGRES_PASSWORD=xxx

# Google AI
GOOGLE_AI_API_KEY=xxx

# n8n
N8N_WEBHOOK_URL=http://localhost:5678/webhook/clothify
```

## Status Flow

```
pending ──▶ processing ──▶ done ──▶ sent
                │
                └──▶ error
```

| Status | Description | Actor |
|--------|-------------|-------|
| pending | Job created, waiting | Discord Bot |
| processing | n8n picked up job | n8n |
| done | Image generated | n8n |
| error | Generation failed | n8n |
| sent | Delivered to user | Discord Bot |

## Input Filename Convention

Format: `{product_name}-{garment_type}-{size_code}.{ext}`

Examples:
- `hoodie_nike-pull-2.webp` → hoodie_nike, pull, size S/M
- `jean_levis-jean-3.jpg` → jean_levis, jean, size L

## API Endpoints

### n8n Webhook (if using webhook trigger)
```
POST /webhook/clothify
Content-Type: application/json

{
  "job_id": "uuid",
  "input_file_paths": ["/images/input/file.webp"],
  "garment": "pull",
  "size": "2",
  "custom_prompt": "optional"
}
```

## Key Implementation Notes

1. **Image Storage**: Files stored on disk, paths in database
2. **Polling Interval**: Discord bot polls every 5 seconds for done jobs
3. **Timeout**: NanoBanana API timeout is 180 seconds
4. **Supported Formats**: .jpg, .jpeg, .png, .webp
5. **Multiple Images**: input_file_paths is an array for multiple angles of same product
