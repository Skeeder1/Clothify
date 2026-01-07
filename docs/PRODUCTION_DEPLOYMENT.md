# Guide de Transition LOCAL → PRODUCTION

Ce guide explique comment adapter les variables d'environnement lors du déploiement sur Coolify.

## 📋 Variables à Modifier

### ✅ Variables IDENTIQUES (Local et Production)

Ces variables doivent avoir **exactement la même valeur** en local et en production :

```bash
# Discord
DISCORD_TOKEN=<your-discord-bot-token>
DISCORD_CHANNEL_NAME=bot_clothify
DISCORD_GUILD_ID=your-guild-id

# Google AI
GOOGLE_AI_API_KEY=<your-google-ai-api-key>

# n8n
N8N_ENCRYPTION_KEY=<your-n8n-encryption-key>
GENERIC_TIMEZONE=Europe/Paris
TZ=Europe/Paris
N8N_PORT=5678

# Bot Behavior
POLL_INTERVAL_SECONDS=5
WATCH_TIMEOUT_SECONDS=120
WATCH_INTERVAL_SECONDS=5

# Docker Path Mapping (identiques car logique interne)
DOCKER_INPUT_PREFIX=/files/input/
DOCKER_OUTPUT_PREFIX=/files/output/
HOST_INPUT_PREFIX=images/input/
HOST_OUTPUT_PREFIX=images/output/
```

---

### 🔄 Variables à ADAPTER (Différentes selon environnement)

#### 1. DATABASE_URL

**LOCAL (docker-compose):**
```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/clothify
```

**PRODUCTION (Coolify):**
```bash
DATABASE_URL=postgresql://postgres:VOTRE_MOT_DE_PASSE_FORT@postgres:5432/clothify
```

> **Important:** Remplacez `localhost` par `postgres` (nom du service Docker) et utilisez un mot de passe sécurisé.

---

#### 2. POSTGRES_PASSWORD

**LOCAL:**
```bash
POSTGRES_PASSWORD=postgres
```

**PRODUCTION:**
```bash
POSTGRES_PASSWORD=<your-postgres-password>!@#
```

> **Sécurité:** Générez un mot de passe fort : `openssl rand -base64 32`

---

#### 3. INPUT_IMAGES_PATH & OUTPUT_IMAGES_PATH

**LOCAL (Bot sur host):**
```bash
INPUT_IMAGES_PATH=./images/input
OUTPUT_IMAGES_PATH=./images/output
```

**PRODUCTION (Bot dockerisé):**
```bash
INPUT_IMAGES_PATH=/app/images/input
OUTPUT_IMAGES_PATH=/app/images/output
```

> **Explication:** En production, le bot tourne dans un container Docker, les chemins sont donc absolus dans le filesystem du container.

---

## 🚀 Procédure de Déploiement sur Coolify

### 1. Créer la Base de Données PostgreSQL

1. Dashboard Coolify → **New Resource** → **Database** → **PostgreSQL 16**
2. Configuration :
   - **Name:** `clothify-db`
   - **Database:** `clothify`
   - **Username:** `postgres`
   - **Password:** Générer un mot de passe fort
3. **Deploy**
4. Noter le hostname interne (ex: `postgres` ou `clothify-db`)

### 2. Initialiser la Base de Données

Via le terminal Coolify du container PostgreSQL :

```bash
# Se connecter au container
docker exec -it clothify-db psql -U postgres -d clothify

# Ou via Coolify UI : Services → clothify-db → Terminal
\i /path/to/01-schema.sql
\i /path/to/002_add_queue_system.sql
\i /path/to/003_add_n8n_notify_trigger.sql
\i /path/to/004_cleanup_polling_elements.sql
\q
```

### 3. Déployer n8n

1. **New Resource** → **Docker Compose** ou **Application** → n8n template
2. **Volumes persistants:**
   - `/home/node/.n8n` → Volume Coolify (workflows)
   - `/files/input` → Volume partagé `clothify-images-input`
   - `/files/output` → Volume partagé `clothify-images-output`
3. **Variables d'environnement:** (copier depuis `.env` local + adaptations)
   ```bash
   N8N_ENCRYPTION_KEY=<your-n8n-encryption-key>
   GOOGLE_AI_API_KEY=<your-google-ai-api-key>
   DB_POSTGRESDB_HOST=postgres
   DB_POSTGRESDB_DATABASE=clothify
   DB_POSTGRESDB_USER=postgres
   DB_POSTGRESDB_PASSWORD=<votre-mot-de-passe-fort>
   DISCORD_TOKEN=<your-discord-bot-token>
   GENERIC_TIMEZONE=Europe/Paris
   TZ=Europe/Paris
   ```
4. **Deploy**

### 4. Importer les Workflows n8n

1. Accéder à n8n via Tailscale : `http://100.x.x.x:5678`
2. **Workflows** → **Import from File**
3. Importer tous les fichiers JSON de `n8n/workflows/`
4. Configurer les credentials :
   - PostgreSQL (host: `postgres`, database: `clothify`)
   - Google AI API Key
5. **Activer** tous les workflows

### 5. Déployer le Bot Discord

1. **New Resource** → **Application** → **Dockerfile**
2. **Repository:** `https://github.com/Skeeder1/Clothify`
3. **Dockerfile Path:** `bot/Dockerfile`
4. **Build Context:** `./bot`
5. **Volumes persistants:**
   - `/app/images/input` → Volume partagé `clothify-images-input` (même que n8n)
   - `/app/images/output` → Volume partagé `clothify-images-output` (même que n8n)
6. **Variables d'environnement:** (ATTENTION aux changements)
   ```bash
   # Discord (identique)
   DISCORD_TOKEN=<your-discord-bot-token>
   DISCORD_CHANNEL_NAME=bot_clothify
   DISCORD_GUILD_ID=your-guild-id
   
   # Database (CHANGÉ: localhost → postgres)
   DATABASE_URL=postgresql://postgres:VotreMotDePasseFort@postgres:5432/clothify
   
   # File Paths (CHANGÉ: chemins absolus Docker)
   INPUT_IMAGES_PATH=/app/images/input
   OUTPUT_IMAGES_PATH=/app/images/output
   
   # Bot Behavior (identique)
   POLL_INTERVAL_SECONDS=5
   WATCH_TIMEOUT_SECONDS=120
   WATCH_INTERVAL_SECONDS=5
   
   # Path Mapping (identique)
   DOCKER_INPUT_PREFIX=/files/input/
   DOCKER_OUTPUT_PREFIX=/files/output/
   HOST_INPUT_PREFIX=images/input/
   HOST_OUTPUT_PREFIX=images/output/
   ```
7. **Deploy**

---

## ✅ Checklist de Vérification Post-Déploiement

- [ ] PostgreSQL accessible depuis n8n et bot
- [ ] Volumes partagés correctement montés (`/files/input` et `/files/output` accessibles par n8n ET bot)
- [ ] n8n workflows activés et LISTEN sur `n8n_jobs_channel`
- [ ] Bot connecté à Discord (vérifier les logs Coolify)
- [ ] Tester un upload : Image → Sélection → Génération → Réception
- [ ] Vérifier les logs de chaque service en cas d'erreur

---

## 🔧 Maintenance et Mises à Jour

### Mettre à jour le code (après git push)

**Sur le serveur (via Tailscale SSH ou Coolify UI):**

1. **Bot:** Coolify détecte automatiquement les nouveaux commits → **Redeploy**
2. **n8n:** Si workflows modifiés, réimporter via l'UI
3. **Database:** Si migrations nécessaires, exécuter via terminal :
   ```bash
   docker exec -it clothify-db psql -U postgres -d clothify -f /migrations/00X_nouvelle_migration.sql
   ```

### Consulter les logs

```bash
# Via Coolify UI
Services → [service_name] → Logs

# Via CLI (si accès SSH)
docker logs -f clothify-bot
docker logs -f clothify-n8n
docker logs -f clothify-db
```

---

## 📝 Template `.env` pour PRODUCTION (Coolify)

Copier ce template dans Coolify UI pour chaque service :

```bash
# ===========================================
# PRODUCTION ENVIRONMENT (Coolify)
# ===========================================

# === DISCORD ===
DISCORD_TOKEN=<your-discord-bot-token>
DISCORD_CHANNEL_NAME=bot_clothify
DISCORD_GUILD_ID=your-guild-id

# === DATABASE ===
DATABASE_URL=postgresql://postgres:VOTRE_MOT_DE_PASSE_FORT@postgres:5432/clothify
POSTGRES_USER=postgres
POSTGRES_PASSWORD=VOTRE_MOT_DE_PASSE_FORT
POSTGRES_DB=clothify

# === FILE PATHS (Docker Absolus) ===
INPUT_IMAGES_PATH=/app/images/input
OUTPUT_IMAGES_PATH=/app/images/output

# === N8N ===
GENERIC_TIMEZONE=Europe/Paris
TZ=Europe/Paris
N8N_PORT=5678
N8N_ENCRYPTION_KEY=<your-n8n-encryption-key>

# === GOOGLE AI ===
GOOGLE_AI_API_KEY=<your-google-ai-api-key>

# === BOT BEHAVIOR ===
POLL_INTERVAL_SECONDS=5
WATCH_TIMEOUT_SECONDS=120
WATCH_INTERVAL_SECONDS=5

# === DOCKER PATH MAPPING ===
DOCKER_INPUT_PREFIX=/files/input/
DOCKER_OUTPUT_PREFIX=/files/output/
HOST_INPUT_PREFIX=images/input/
HOST_OUTPUT_PREFIX=images/output/
```

---

## 🆘 Troubleshooting

### Problème : Bot ne reçoit pas les messages Discord

**Solution:** Vérifier `DISCORD_CHANNEL_NAME` correspond bien au nom du canal.

### Problème : n8n ne détecte pas les nouveaux jobs

**Solutions:**
1. Vérifier que le trigger PostgreSQL est bien installé : `SELECT * FROM pg_trigger WHERE tgname = 'trg_n8n_new_job';`
2. Vérifier que le workflow n8n est **activé** (toggle ON)
3. Vérifier les credentials PostgreSQL dans n8n

### Problème : Images non trouvées après génération

**Solutions:**
1. Vérifier les volumes partagés : `docker volume ls` → Doivent être les mêmes pour bot et n8n
2. Vérifier `INPUT_IMAGES_PATH` et `OUTPUT_IMAGES_PATH` dans le bot
3. Vérifier les permissions : `ls -la /app/images/` dans le container bot

### Problème : Erreur de connexion à la base de données

**Solutions:**
1. Vérifier `DATABASE_URL` utilise bien `postgres` (nom du service) et non `localhost`
2. Vérifier que le mot de passe correspond bien dans tous les services
3. Tester la connexion : `docker exec -it clothify-bot psql $DATABASE_URL`

---

**Dernière mise à jour:** 6 janvier 2026  
**Testé avec:** Coolify 4.x, PostgreSQL 16, n8n latest, Python 3.11
