# Guide d'accès - Base de données Clothify

## Démarrage rapide

```bash
cd Database
make start      # Démarrer PostgreSQL
make connect    # Se connecter à la database
make stop       # Arrêter PostgreSQL
```

---

## Informations de connexion

| Paramètre | Valeur |
|-----------|--------|
| **Host** | `localhost` |
| **Port** | `5432` |
| **Database** | `clothify` |
| **Username** | `postgres` |
| **Password** | `postgres` |

### String de connexion
```
postgresql://postgres:postgres@localhost:5432/clothify
```

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

### Commandes principales

| Commande | Description |
|----------|-------------|
| `make start` | Démarrer PostgreSQL |
| `make stop` | Arrêter PostgreSQL |
| `make restart` | Redémarrer PostgreSQL |
| `make status` | Voir l'état des services |
| `make connect` | Se connecter via psql |
| `make logs` | Voir les logs |
| `make help` | Afficher toutes les commandes |

### Outils

| Commande | Description |
|----------|-------------|
| `make launch-azure` | Lancer Azure Data Studio |
| `make stop-azure` | Arrêter Azure Data Studio |
| `make chartdb-start` | Démarrer ChartDB (http://localhost:5000) |
| `make chartdb-stop` | Arrêter ChartDB |

### Maintenance

| Commande | Description |
|----------|-------------|
| `make down` | Supprimer les conteneurs (garde les données) |
| `make clean` | **DANGER** - Tout supprimer (conteneurs + données) |

---

## Connexion via psql

```bash
# Via Makefile
make connect

# Ou directement
psql -h localhost -U postgres -d clothify
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
Database/
├── .env                      # Variables d'environnement
├── docker-compose.yml        # Configuration Docker
├── Makefile                  # Commandes
├── GUIDE_ACCES.md           # Ce fichier
├── Shema.md                  # Schéma DBML original
└── scripts/
    └── init/
        └── 01-schema.sql     # Script d'initialisation
```

---

## Réinitialiser la database

Si tu dois tout recréer :

```bash
cd Database
make clean      # Tape "yes" pour confirmer
make start      # Recrée tout depuis zéro
```
