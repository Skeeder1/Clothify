# Workflows n8n

Ce dossier contient l'export JSON des workflows n8n de Clothify. **Ils sont la
logique de génération d'images** — le bot Python n'appelle aucune API d'image.

Les workflows vivent normalement dans la base interne de n8n et ne sont donc pas
versionnés. Ces exports comblent ce trou : sans eux, la moitié du système
n'existerait que dans un conteneur.

| Fichier | id | État |
|---|---|---|
| `production-Clothify-n8n.json` | `Qdtp2SCgNQ1SUE6K` | actif |
| `test-clothify-n8n.json` | `emFvQESqlf4RPN6Q` | inactif |

> ⚠️ Les deux écoutent la **même** table `public.jobs`. Les activer simultanément
> fait traiter chaque job deux fois, et **double le coût**. Un seul actif à la fois.

## Exporter (après toute modification dans l'UI)

```bash
docker exec <conteneur_n8n> n8n export:workflow --all --output=/tmp/wf.json
docker cp <conteneur_n8n>:/tmp/wf.json ./wf.json
# puis découper par workflow dans ce dossier
```

L'export depuis l'interface (menu ⋯ → *Download*) fonctionne aussi, workflow par
workflow.

## Importer

```bash
docker cp wf.json <conteneur_n8n>:/tmp/wf.json
docker exec <conteneur_n8n> n8n import:workflow --input=/tmp/wf.json

# L'import DESACTIVE les workflows importés : les réactiver explicitement
docker exec <conteneur_n8n> n8n update:workflow --id=Qdtp2SCgNQ1SUE6K --active=true

# L'activation n'est prise en compte qu'au démarrage
docker restart <conteneur_n8n>
```

Vérifier ensuite : `docker logs --since 2m <conteneur_n8n> | grep "Activated workflow"`.

## Credentials

Les credentials ne sont **pas** incluses dans ces exports (elles sont chiffrées
avec `N8N_ENCRYPTION_KEY`). Après un import sur une nouvelle instance, il faut
les recréer :

| Nom | Type | Usage |
|---|---|---|
| `Postgres Serveur` | `postgres` | trigger + mises à jour de statut |
| `OpenRouter Clothify` | `httpHeaderAuth` | `Authorization: Bearer <clé OpenRouter>` |

Les nœuds référencent ces credentials par id. Si vous en recréez une avec un id
différent, mettez à jour la référence dans le JSON du nœud concerné.

## Compatibilité

Ces exports ciblent **n8n 1.119.2**. Le nœud HTTP Request y est en `typeVersion`
**4.2** : le relever casse l'activation avec
`Cannot read properties of undefined (reading 'execute')`.

Documentation complète de la chaîne : [../../docs/IMAGE_GENERATION.md](../../docs/IMAGE_GENERATION.md).
