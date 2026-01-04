# Deploiement Coolify - Guide Complet

Ce guide explique comment deployer Clothify sur Coolify avec 3 services separes.

## Prerequis

- Instance Coolify fonctionnelle (v4+)
- Acces au repository Git (GitHub/GitLab)
- Tokens et cles API:
  - Discord Bot Token
  - Google AI API Key

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        COOLIFY                               │
│  ┌──────────┐    ┌──────────┐    ┌──────────────────────┐   │
│  │ PostgreSQL│◄───│   Bot    │    │        n8n           │   │
│  │   :5432   │    │  Python  │    │       :5678          │   │
│  └─────┬─────┘    └────┬─────┘    └──────────┬───────────┘   │
│        │               │                     │               │
│        └───────────────┴──────────┬──────────┘               │
│                    ┌──────────────┴──────────────┐           │
│                    │   Volumes Partages          │           │
│                    │   - clothify-images-input   │           │
│                    │   - clothify-images-output  │           │
│                    └─────────────────────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

---

## Etape 1: Creer les Volumes Partages

Dans Coolify, creer 2 volumes pour partager les images entre le bot et n8n.

1. Aller dans **Settings** > **Storage** > **Create Volume**
2. Creer les volumes:

| Nom | Mount Path |
|-----|------------|
| `clothify-images-input` | `/files/input` |
| `clothify-images-output` | `/files/output` |

---

## Etape 2: Deployer PostgreSQL

### 2.1 Creer le service

1. **New Resource** > **Database** > **PostgreSQL**
2. Version: **16** (recommande)

### 2.2 Configuration

```
Database Name: clothify
Username: clothify_user
Password: [generer un mot de passe fort]
```

### 2.3 Deployer

Cliquer sur **Deploy** et attendre que le service soit actif.

### 2.4 Noter les informations

Apres deploiement, noter:
- **Internal Hostname**: ex. `postgresql-abc123` (visible dans les details du service)
- **Port**: `5432`

### 2.5 Initialiser le schema

Connectez-vous a la base et executez les scripts SQL:

```bash
# Via le terminal Coolify ou un client PostgreSQL
psql -h <internal-hostname> -U clothify_user -d clothify
```

Executer dans l'ordre:
1. `Database/scripts/init/01-schema.sql`
2. `Database/scripts/migrations/002_add_queue_system.sql`
3. `Database/scripts/migrations/003_add_n8n_notify_trigger.sql`
4. `Database/scripts/migrations/004_cleanup_polling_elements.sql`

---

## Etape 3: Deployer n8n

### 3.1 Creer le service

1. **New Resource** > **Docker Image**
2. Image: `n8nio/n8n:latest`

### 3.2 Variables d'environnement

```env
GENERIC_TIMEZONE=Europe/Paris
TZ=Europe/Paris
N8N_ENCRYPTION_KEY=<generer: openssl rand -base64 32>
GOOGLE_AI_API_KEY=<votre-cle-api>
DISCORD_TOKEN=<votre-token-discord>

# PostgreSQL (utiliser le hostname interne)
DB_POSTGRESDB_HOST=<internal-hostname-postgres>
DB_POSTGRESDB_PORT=5432
DB_POSTGRESDB_DATABASE=clothify
DB_POSTGRESDB_USER=clothify_user
DB_POSTGRESDB_PASSWORD=<meme-password>
```

### 3.3 Volumes

Ajouter les mounts:

| Source | Target |
|--------|--------|
| `clothify-images-input` | `/files/input` |
| `clothify-images-output` | `/files/output` |
| Persistent Storage | `/home/node/.n8n` |

### 3.4 Port et Domaine

- Port: `5678`
- Domaine (optionnel): `n8n.votre-domaine.com`

### 3.5 Deployer

Cliquer sur **Deploy**.

### 3.6 Importer le workflow

1. Acceder a n8n via l'URL
2. **Add Workflow** > **Import from file**
3. Importer `n8n/workflows/clothify-image-generation.json`
4. Configurer les credentials PostgreSQL et Google AI
5. Activer le workflow

---

## Etape 4: Deployer le Bot Discord

### 4.1 Creer le service

1. **New Resource** > **Git Repository**
2. Repository: `https://github.com/votre-user/clothify`
3. Branch: `main`

### 4.2 Configuration Build

```
Build Pack: Dockerfile
Dockerfile Path: bot/Dockerfile
Build Context: .
```

### 4.3 Variables d'environnement

```env
DISCORD_TOKEN=<votre-token-discord>
DATABASE_URL=postgresql://clothify_user:<password>@<postgres-internal-hostname>:5432/clothify
INPUT_IMAGES_PATH=/files/input
OUTPUT_IMAGES_PATH=/files/output
```

### 4.4 Volumes

| Source | Target |
|--------|--------|
| `clothify-images-input` | `/files/input` |
| `clothify-images-output` | `/files/output` |

### 4.5 Deployer

Cliquer sur **Deploy**.

---

## Verification du Deploiement

### 1. Verifier PostgreSQL

```sql
-- Dans le terminal Coolify ou psql
SELECT COUNT(*) FROM users;
SELECT * FROM pg_trigger WHERE tgname = 'trg_n8n_new_job';
```

### 2. Verifier n8n

- Acceder a l'interface web
- Verifier que le workflow est **Active**
- Tester les credentials PostgreSQL

### 3. Verifier le Bot

- Voir les logs dans Coolify
- Le bot doit afficher "Ready" et etre connecte a Discord
- Tester avec `!status` dans Discord

### 4. Test complet

1. Envoyer une image au bot Discord
2. Verifier que le job est cree dans PostgreSQL
3. Verifier que n8n recoit le NOTIFY
4. Verifier que l'image generee est renvoyee

---

## Troubleshooting

### Le bot ne se connecte pas a PostgreSQL

```
Error: Connection refused
```

**Solutions:**
- Verifier que DATABASE_URL utilise le hostname **interne** Coolify
- Verifier que PostgreSQL est dans le meme network
- Verifier les credentials

### n8n ne recoit pas les NOTIFY

**Verifier le trigger:**
```sql
SELECT * FROM pg_trigger WHERE tgname = 'trg_n8n_new_job';
```

**Verifier le channel:**
```sql
LISTEN n8n_jobs_channel;
-- Puis creer un job pour tester
```

### Les images ne sont pas partagees

**Verifier les volumes:**
- Les 3 services doivent utiliser les memes volumes
- Les permissions doivent permettre l'ecriture

```bash
# Dans le container
ls -la /files/input
ls -la /files/output
```

### Le bot crash au demarrage

**Verifier les logs Coolify:**
- Token Discord invalide?
- DATABASE_URL mal formee?
- Variables manquantes?

---

## Maintenance

### Backup de la base

```bash
pg_dump -h <hostname> -U clothify_user clothify > backup_$(date +%Y%m%d).sql
```

### Mise a jour du bot

1. Push sur la branche `main`
2. Coolify redeploit automatiquement (si webhook configure)
3. Sinon: Coolify > Service > **Redeploy**

### Mise a jour de n8n

1. Coolify > Service n8n > **Pull Latest Image**
2. **Redeploy**
3. Verifier que le workflow est toujours actif

### Export des workflows n8n

Avant toute mise a jour majeure:
1. Ouvrir n8n
2. Exporter le workflow en JSON
3. Sauvegarder dans `n8n/workflows/`
4. Commit dans le repo

---

## Commandes utiles

```bash
# Generer une cle N8N_ENCRYPTION_KEY
openssl rand -base64 32

# Tester la connection PostgreSQL
psql postgresql://clothify_user:<password>@<hostname>:5432/clothify

# Voir les jobs en attente
psql -c "SELECT id, status, created_at FROM jobs ORDER BY created_at DESC LIMIT 10;"

# Stats de la queue
psql -c "SELECT * FROM get_queue_stats();"
```
