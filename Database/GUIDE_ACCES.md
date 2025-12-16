# Guide d'accès - Base de données Clothify

## Démarrage rapide

```bash
# Depuis la racine du projet
make start      # Démarrer PostgreSQL + n8n
make stop       # Arrêter tous les services
make status     # Voir l'état des services
```

---

## Informations de connexion

### Depuis l'hôte (Discord Bot, psql, etc.)

| Paramètre | Valeur |
|-----------|--------|
| **Host** | `localhost` |
| **Port** | `5432` |
| **Database** | `clothify` |
| **Username** | `postgres` |
| **Password** | `postgres` |

```
postgresql://postgres:postgres@localhost:5432/clothify
```

### Depuis n8n (réseau Docker interne)

| Paramètre | Valeur |
|-----------|--------|
| **Host** | `postgres` |
| **Port** | `5432` |
| **Database** | `clothify` |
| **Username** | `postgres` |
| **Password** | `postgres` |

> **Note :** Dans n8n, utiliser `postgres` comme host car les services sont dans le même réseau Docker.

---

## Schéma de la base

### Tables

| Table | Description |
|-------|-------------|
| `users` | Utilisateurs Discord |
| `jobs` | Tâches de génération d'images |
| `job_logs` | Historique des statuts des jobs |

### Enums

| Enum | Valeurs |
|------|---------|
| `job_status` | pending, processing, done, error, sent |
| `garment_type` | echarpe, pull, tshirt, chemise, veste, manteau, pantalon, jean, short, jupe, robe, bonnet, casquette, sac, other |
| `size_code` | 1, 2, 3, 4 |

---

## Commandes Makefile

Toutes les commandes s'exécutent depuis la **racine du projet** :

### Services Docker

| Commande | Description |
|----------|-------------|
| `make start` | Démarrer PostgreSQL + n8n |
| `make stop` | Arrêter tous les services |
| `make restart` | Redémarrer les services |
| `make status` | Voir l'état des services |
| `make logs` | Voir les logs (tous les services) |

### Discord Bot

| Commande | Description |
|----------|-------------|
| `make bot` | Lancer le bot Discord |
| `make setup` | Installer les dépendances |

---

## Connexion via psql

```bash
# Directement
psql -h localhost -U postgres -d clothify

# Ou via Docker
docker exec -it clothify_postgres psql -U postgres -d clothify
```

### Commandes psql utiles

```sql
\dt              -- Lister les tables
\d users         -- Structure de la table users
\d jobs          -- Structure de la table jobs
\d job_logs      -- Structure de la table job_logs
\dT+             -- Lister les enums
\l               -- Lister les databases
\q               -- Quitter
```

---

## Structure des fichiers

```
Clothify/
├── .env                      # Variables d'environnement
├── docker-compose.yml        # PostgreSQL + n8n (unifié)
├── Makefile                  # Commandes principales
├── bot/                      # Code du bot Discord
└── Database/
    ├── GUIDE_ACCES.md        # Ce fichier
    ├── Shema.md              # Schéma DBML original
    └── scripts/
        └── init/
            ├── 01-schema.sql         # Schéma initial
            └── 02-add-channel-id.sql # Migration channel_id
```

---

## Réinitialiser la database

Si tu dois tout recréer :

```bash
# Depuis la racine du projet
make stop                           # Arrêter les services
docker volume rm clothify_postgres-data  # Supprimer les données
make start                          # Recréer depuis zéro
```

---

## Services disponibles

| Service | URL | Description |
|---------|-----|-------------|
| PostgreSQL | `localhost:5432` | Base de données |
| n8n | `http://localhost:5678` | Workflow automation |
