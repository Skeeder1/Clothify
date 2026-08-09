# Configuration Architecture

Clothify utilise une **architecture hybride à 2 fichiers** pour séparer les configurations universelles des secrets spécifiques à l'environnement.

---

## 📦 Structure

```
clothify/
├── config.yaml          # ✅ Configurations universelles (commité dans Git)
├── .env                 # 🔐 Secrets et chemins (ignoré par Git)
└── bot/config.py        # 🔧 Charge automatiquement les 2 fichiers
```

---

## 📄 config.yaml - Configurations Universelles

**Ce fichier contient toutes les configurations métier identiques en LOCAL et PRODUCTION.**

### Sections :

#### 1. Bot Behavior
```yaml
bot:
  poll_interval_seconds: 5        # Intervalle de polling
  watch_timeout_seconds: 120      # Timeout max pour un job
  watch_interval_seconds: 5       # Intervalle de vérification
  discord_channel_name: "bot_clothify"  # Canal Discord cible
  supported_extensions: [".jpg", ".jpeg", ".png", ".webp"]
```

#### 2. Database Schema
```yaml
database:
  valid_garments: ["echarpe", "pull", "tshirt", ...]
  valid_sizes: ["1", "2", "3", "4"]
```

#### 3. Path Mapping
```yaml
paths:
  docker:
    input_prefix: "/files/input/"
    output_prefix: "/files/output/"
  host:
    input_prefix: "images/input/"
    output_prefix: "images/output/"
```

#### 4. Discord UI
```yaml
discord:
  view_timeout: 300              # Timeout des Select/Button (5 min)
  pending_upload_ttl: 300        # TTL des sessions d'upload
```

#### 5. n8n Configuration
```yaml
n8n:
  timezone: "Europe/Paris"
  port: 5678
```

#### 6. Job Settings
```yaml
jobs:
  max_attempts: 3                # Tentatives max avant échec
  stale_timeout_minutes: 5       # Timeout pour jobs bloqués
```

**🔹 Avantages :**
- ✅ Versionné dans Git (traçabilité des changements)
- ✅ Modifications déployées automatiquement avec `git pull`
- ✅ Aucun secret sensible exposé
- ✅ Centralisation des configs métier

---

## 🔐 .env - Secrets et Chemins Spécifiques

**Ce fichier contient UNIQUEMENT les variables qui diffèrent selon l'environnement.**

### Variables :

#### Discord Secrets
```bash
DISCORD_TOKEN=your-discord-bot-token
DISCORD_GUILD_ID=your-guild-id
```

#### Database Connection (varie LOCAL/PROD)
```bash
# LOCAL:
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/clothify

# PRODUCTION:
DATABASE_URL=postgresql://postgres:StrongPassword@postgres:5432/clothify

POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=clothify
```

#### File Paths (varie LOCAL/PROD)
```bash
# LOCAL:
INPUT_IMAGES_PATH=./images/input
OUTPUT_IMAGES_PATH=./images/output

# PRODUCTION:
INPUT_IMAGES_PATH=/app/images/input
OUTPUT_IMAGES_PATH=/app/images/output
```

#### API Keys
```bash
# Note : la clé du modèle d'image n'est PAS une variable d'environnement.
# Elle est stockée comme credential chiffrée dans n8n (« OpenRouter Clothify »).
# Voir docs/IMAGE_GENERATION.md §3.
N8N_ENCRYPTION_KEY=your-n8n-encryption-key
```

**🔹 Sécurité :**
- ❌ **NON commité dans Git** (dans `.gitignore`)
- 🔐 Contient des secrets sensibles
- 📝 Template disponible : `.env.example`

---

## 🔧 Comment ça fonctionne ?

### bot/config.py

Le module `bot/config.py` charge automatiquement les 2 sources :

```python
import os
import yaml
from dotenv import load_dotenv

# 1. Charge .env (secrets)
load_dotenv(".env")

# 2. Charge config.yaml (configs universelles)
with open("config.yaml", 'r') as f:
    yaml_config = yaml.safe_load(f)

class Config:
    # Secrets depuis .env
    DISCORD_BOT_TOKEN = os.getenv("DISCORD_TOKEN")
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    # Configs depuis config.yaml
    WATCH_TIMEOUT = yaml_config['bot']['watch_timeout_seconds']
    DISCORD_CHANNEL_NAME = yaml_config['bot']['discord_channel_name']
```

**Utilisation dans le code :**

```python
from bot.config import config

# Accès transparent
timeout = config.WATCH_TIMEOUT_SECONDS
channel = config.DISCORD_CHANNEL_NAME
db_url = config.DATABASE_URL
```

---

## 🚀 Workflow de Déploiement

### LOCAL → PRODUCTION

#### 1. Modifications de Configuration Métier (config.yaml)

```bash
# Modifier le timeout par exemple
vim config.yaml  # watch_timeout_seconds: 120 → 180

git add config.yaml
git commit -m "feat: augmente timeout jobs à 180s"
git push origin main
```

**Sur le serveur :**
```bash
git pull origin main
# Redémarrage automatique (selon config Coolify)
```

✅ **Changement déployé automatiquement !**

---

#### 2. Modifications des Secrets (.env)

**Via Coolify UI :**
1. Services → Bot → Environment Variables
2. Modifier `DATABASE_URL`, `INPUT_IMAGES_PATH`, etc.
3. Redeploy

❌ **Jamais commiter le .env dans Git**

---

## 📋 Checklist Premier Déploiement

### LOCAL
```bash
# 1. Cloner le repo
git clone https://github.com/Skeeder1/Clothify.git
cd Clothify

# 2. Créer .env depuis template
cp .env.example .env
nano .env  # Éditer avec vos secrets

# 3. config.yaml est déjà présent (commité)
# Pas besoin de le créer

# 4. Installer dépendances
pip install -r bot/requirements.txt

# 5. Démarrer
docker-compose up -d
python bot/main.py
```

### PRODUCTION (Coolify)
```bash
# 1. config.yaml est automatiquement récupéré via git pull
# 2. Configurer .env dans Coolify UI avec adaptations :

# Adapter ces 4 variables :
DATABASE_URL=postgresql://postgres:StrongPassword@postgres:5432/clothify
INPUT_IMAGES_PATH=/app/images/input
OUTPUT_IMAGES_PATH=/app/images/output
POSTGRES_PASSWORD=StrongPassword123!

# Garder identiques :
DISCORD_TOKEN=<identique>
# (clé du modèle d'image : credential n8n, pas de variable ici)
N8N_ENCRYPTION_KEY=<identique>

# 3. Deploy
```

---

## 🔄 Cas d'Usage Courants

### Changer le nom du canal Discord

**Avant :** Hardcodé dans le code → Modification + commit + deploy  
**Après :** Dans `config.yaml` → Modification + commit + deploy

```yaml
# config.yaml
bot:
  discord_channel_name: "bot_clothify_prod"  # Changé
```

```bash
git add config.yaml
git commit -m "feat: utilise canal prod pour bot"
git push
```

✅ Déployé automatiquement sur `git pull`

---

### Augmenter le timeout des jobs

```yaml
# config.yaml
bot:
  watch_timeout_seconds: 300  # 5 minutes au lieu de 2
```

Commit → Push → Pull → Redeploy automatique

---

### Changer l'API Key (secret)

**Via Coolify UI uniquement** (ou `.env` en local) :
```bash
# (rotation de la clé image : se fait dans la credential n8n)
```

Redeploy → Appliqué immédiatement

---

## 📊 Comparaison Avant/Après

| Aspect | AVANT (.env seul) | APRÈS (config.yaml + .env) |
|--------|-------------------|----------------------------|
| **Secrets** | Mélangés avec configs | Isolés dans .env |
| **Configs métier** | Non versionnées | Versionnées (Git) |
| **Déploiement** | Recopier toutes les variables | Automatique pour configs |
| **Clarté** | 93 lignes mélangées | 49 lignes secrets + 88 lignes configs |
| **Historique** | Aucun | Git log pour configs |
| **Duplication** | Valeurs universelles dupliquées | Centralisées |

---

## ✅ Validation

### Tester la configuration

```python
# Test de chargement
python3 -c "from bot.config import config; print('✅ Config OK')"

# Vérifier les valeurs
python3 << EOF
from bot.config import config
print(f"Canal Discord: {config.DISCORD_CHANNEL_NAME}")
print(f"Timeout: {config.WATCH_TIMEOUT_SECONDS}s")
print(f"Database: {config.DATABASE_URL[:40]}...")
EOF
```

---

## 🆘 Troubleshooting

### Erreur : "FileNotFoundError: config.yaml"

**Solution :** Le fichier `config.yaml` doit être à la racine du projet.

```bash
# Vérifier
ls -la config.yaml

# Si absent, récupérer depuis Git
git checkout main config.yaml
```

---

### Erreur : "ModuleNotFoundError: No module named 'yaml'"

**Solution :** Installer PyYAML.

```bash
pip install pyyaml>=6.0.0
```

---

### Variables d'environnement non chargées

**Solution :** Vérifier que `.env` existe et contient les valeurs.

```bash
# Créer depuis template
cp .env.example .env
nano .env
```

---

## 📚 Documentation Associée

- **Architecture complète :** `docs/SYSTEM_ARCHITECTURE.md`
- **Guide déploiement :** `docs/PRODUCTION_DEPLOYMENT.md`
- **Instructions Copilot :** `.github/copilot-instructions.md`
- **Changelog :** `CHANGELOG_ENV_PORTABILITY.md`

---

**Dernière mise à jour :** 6 janvier 2026  
**Architecture validée :** ✅ LOCAL + PRODUCTION
