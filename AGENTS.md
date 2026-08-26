# Clothify — instructions pour agents

Bot Discord qui génère des visuels produit e-commerce : l'utilisateur envoie la
photo d'un vêtement, reçoit en retour une image d'un mannequin le portant.

## Le point le plus important

**L'appel au modèle d'image n'est PAS dans le code Python.** Le bot ne fait
qu'écrire un job en base ; c'est un workflow **n8n** qui appelle l'API d'image.
Chercher `openrouter` ou un nom de modèle dans `bot/` ne donnera rien.

```
Discord → bot (Python) → INSERT public.jobs + NOTIFY → n8n → OpenRouter
                                    ↑                          ↓
                        bot poll status='done'  ←  UPDATE jobs + fichier PNG
```

Pour modifier le modèle, le prompt ou le format de requête :
voir `docs/IMAGE_GENERATION.md` et `n8n/workflows/`.

## Arborescence

| Chemin | Rôle |
|---|---|
| `bot/` | Bot Discord (Python 3.11, discord.py, asyncpg) |
| `bot/handlers/` | `message.py` (upload), `views.py` (UI), `tasks.py` (polling + envoi) |
| `bot/database.py` | Accès PostgreSQL — c'est ici qu'est le contrat de statut |
| `Database/` | Schéma : `clothify_schema.sql` (réel, exporté), `.dbml` (diagramme) |
| `n8n/workflows/` | Export JSON des workflows n8n — **la logique de génération** |
| `docs/` | Documentation technique |
| `docker-compose.yml` | Stack locale : PostgreSQL + n8n + bot |

## Cycle de vie d'un job

`pending` → `processing` → `done` → `sent`, avec `error` en sortie de secours.

- `pending` : posé par le bot à l'upload
- `processing` : posé par n8n en début de traitement
- `done` : posé par n8n avec `output_file_path` renseigné
- `sent` : posé par le bot après envoi sur Discord

Le bot ne détecte la fin qu'avec `WHERE status = 'done'` (`bot/database.py:172`).
Tout ce qui écrase ce statut casse la livraison en silence.

## Commandes

```bash
# Stack complète en local
docker compose up -d

# Bot seul (nécessite PostgreSQL + n8n joignables)
pip install -r bot/requirements.txt
python -m bot.main

# Test de connectivité (PostgreSQL, Discord, volume, n8n)
python bot/tests/connectivity_test.py

# Test bout en bout SANS Discord — insère un job et attend le résultat
# ⚠ consomme du crédit API (~0,05 $ par exécution)
bash scripts/e2e_test.sh <image_source> <garment> <genre> <size> <timeout_s>

# Changer de modèle d'image (à lancer sur l'hôte Docker)
sudo python3 scripts/switch_model.py --list
sudo python3 scripts/switch_model.py gpt-5-image-mini
```

## Variables d'environnement

Noms uniquement — les valeurs sont dans `.env` (jamais versionné).

| Variable | Utilisée par |
|---|---|
| `DISCORD_TOKEN`, `DISCORD_GUILD_ID`, `DISCORD_CHANNEL_NAME` | bot |
| `DATABASE_URL`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | bot, n8n |
| `SHARED_VOLUME_PATH` | bot, n8n (volume d'images partagé) |
| `N8N_ENCRYPTION_KEY` | n8n |

La clé OpenRouter n'est **pas** une variable d'environnement : elle est stockée
comme credential chiffrée dans n8n (`OpenRouter Clothify`, type `httpHeaderAuth`).
n8n bloque `$env` dans les nœuds par défaut — ne pas tenter d'y revenir.

## Volume partagé

Bot et n8n partagent `/clothify_shared` :
`input_image/` (uploads) et `output_image/` (générations `<nom>_generated.png`).
Les chemins stockés en base sont **absolus côté conteneur**.

## Contraintes à respecter

- **n8n déployé est en 1.119.2.** Ne pas relever le `typeVersion` d'un nœud
  au-delà de ce que cette version connaît (`httpRequest` : 4.2) — l'activation
  échoue sur `Cannot read properties of undefined (reading 'execute')`.
- **`executionTimeout` du workflow production : 600 s.** La génération prend
  50-100 s ; en dessous de ~150 s l'appel est annulé en vol et **facturé sans
  résultat**.
- Dans les nœuds Code, préférer `$('Nom Du Nœud')` à `$input` : `$input` casse
  silencieusement dès qu'on modifie le câblage amont.
- Après toute modification d'un workflow n8n : réexporter dans `n8n/workflows/`
  (`n8n export:workflow --all`), sinon la logique n'est plus versionnée.

## Définition de « terminé »

Une modification de la chaîne de génération n'est terminée que si un test bout
en bout produit un job en statut `done` **et** un fichier PNG non vide dans
`output_image/`. Le statut seul ne suffit pas, le fichier seul non plus.

## Déploiement

Production sur Coolify (serveur auto-hébergé). Voir `docs/PRODUCTION_DEPLOYMENT.md`.
Les workflows n8n se déploient par `n8n import:workflow`, puis
`n8n update:workflow --id=<id> --active=true`, puis **redémarrage du conteneur**
(l'activation n'est prise en compte qu'au démarrage).
