# n8n Workflows - Export Manuel

Ce dossier contient les exports JSON des workflows n8n utilisés par Clothify.

## Comment exporter un workflow

1. Ouvrir n8n (http://localhost:5678 en local ou votre URL Coolify)
2. Aller dans le workflow à exporter
3. Cliquer sur les 3 points (menu) > **Download**
4. Sauvegarder le fichier JSON dans ce dossier

## Comment importer un workflow

1. Ouvrir n8n
2. Cliquer sur **Add Workflow** > **Import from file**
3. Sélectionner le fichier JSON

## Workflows disponibles

| Fichier | Description |
|---------|-------------|
| `clothify-image-generation.json` | Workflow principal de génération d'images |

## Credentials à reconfigurer après import

Les credentials ne sont **PAS** exportés avec les workflows. Après import, vous devez reconfigurer :

1. **PostgreSQL** - Connection à la base Clothify
   - Host: `<hostname-interne-coolify>` ou `localhost`
   - Database: `clothify`
   - User/Password: vos credentials

2. **Google AI (Gemini)** - Clé API pour la génération d'images
   - Type: API Key
   - Key: votre `GOOGLE_AI_API_KEY`

## Configuration PostgreSQL LISTEN

Le workflow utilise le trigger PostgreSQL NOTIFY. Vérifiez que :
- Le node PostgreSQL écoute le channel `n8n_jobs_channel`
- Le trigger `trg_n8n_new_job` est actif dans la base

```sql
-- Vérifier le trigger
SELECT * FROM pg_trigger WHERE tgname = 'trg_n8n_new_job';

-- Tester manuellement
LISTEN n8n_jobs_channel;
```

## Notes importantes

- Toujours versionner les workflows après modification
- Tester le workflow après import avant mise en production
- Les paths d'images dans n8n : `/files/input/` et `/files/output/`
