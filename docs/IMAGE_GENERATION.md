# Chaîne de génération d'images

Référence technique du chemin qui transforme la photo d'un vêtement en visuel
produit. Tout ce qui est décrit ici a été vérifié sur l'instance de production
le 9 août 2026.

> **À lire d'abord si vous cherchez « où est appelé le modèle ».**
> Pas dans `bot/`. Le bot Python n'appelle aucune API d'image : il écrit un job
> en base et attend. L'appel vit dans le workflow n8n `production-Clothify-n8n`.

---

## 1. Vue d'ensemble

```
Discord                bot (Python)              PostgreSQL              n8n                 OpenRouter
   │                       │                          │                   │                      │
   │── upload image ──────▶│                          │                   │                      │
   │                       │── INSERT jobs ──────────▶│                   │                      │
   │                       │   (status=pending)       │── NOTIFY ────────▶│                      │
   │                       │                          │                   │── POST /chat/... ───▶│
   │                       │                          │                   │◀── image base64 ─────│
   │                       │                          │◀── UPDATE done ───│                      │
   │                       │── poll status='done' ───▶│   + fichier PNG   │                      │
   │◀── envoi image ───────│                          │                   │                      │
```

Le découplage passe par la base : ni le bot ni n8n ne s'appellent directement.
Conséquence pratique — **changer de fournisseur d'IA ne touche pas une ligne du
bot**. Contrepartie : la logique métier est répartie entre du code versionné et
un workflow stocké dans la base de n8n, d'où l'export obligatoire dans
`n8n/workflows/`.

## 2. Le workflow n8n

Deux workflows existent, **tous deux branchés sur la même table `public.jobs`** :

| Workflow | id | État attendu |
|---|---|---|
| `production-Clothify-n8n` | `Qdtp2SCgNQ1SUE6K` | **actif** |
| `test-clothify-n8n` | `emFvQESqlf4RPN6Q` | **inactif** |

> ⚠️ Les deux actifs simultanément = chaque job traité deux fois = **coût
> doublé**. Toujours n'en activer qu'un.

### Chaîne de nœuds (production)

```
Postgres Trigger → 🔍 Filter Pending → 📝 Update Processing → 🏷️ Parse Job Data
  → ✨ Generate Prompt → 📷 Read Image → 📦 Prepare API Body
  → 🎨 OpenRouter Image → 🖼️ Extract Image → 💾 Save Output
  → ✅ Update Done → 📊 Summary
```

La chaîne est **strictement séquentielle**. Ce n'était pas le cas historiquement :
`📝 Update Processing` et `🏷️ Parse Job Data` partaient en parallèle de
`🔍 Filter Pending`. n8n dépilant les branches en LIFO, la branche terminale
`📝 Update Processing` s'exécutait **en dernier** et réécrivait `processing`
par-dessus le `done` posé par `✅ Update Done`. Le bot ne cherchant que
`status = 'done'`, l'image n'était jamais livrée. Ne pas rétablir le parallélisme.

### Rôle des nœuds à connaître

| Nœud | Ce qu'il fait | Piège |
|---|---|---|
| `Postgres Trigger` | écoute `NOTIFY n8n_jobs_channel` sur `public.jobs` | le trigger SQL `trg_n8n_new_job` doit exister en base |
| `🔍 Filter Pending` | ne laisse passer que `payload.status == 'pending'` | validation de type stricte |
| `🏷️ Parse Job Data` | normalise taille/type, calcule les chemins absolus | lit `$('Postgres Trigger')`, **pas** `$input` |
| `📦 Prepare API Body` | construit le corps OpenRouter | produit `$json.apiBody` |
| `🎨 OpenRouter Image` | l'appel HTTP | auth par credential, jamais `$env` |
| `🖼️ Extract Image` | décode le base64 en binaire n8n | conserve le contrat `json` + `binary.data` |

## 3. Contrat de l'API OpenRouter

Endpoint : `POST https://openrouter.ai/api/v1/chat/completions`

### Requête

```json
{
  "model": "openai/gpt-5-image-mini",
  "modalities": ["image", "text"],
  "messages": [{
    "role": "user",
    "content": [
      { "type": "text", "text": "<prompt>" },
      { "type": "image_url",
        "image_url": { "url": "data:image/png;base64,<b64>", "detail": "high" } }
    ]
  }]
}
```

- `modalities` est ce qui déclenche la sortie image. Le champ n'apparaît pas
  dans les `supported_parameters` renvoyés par `/api/v1/models` — c'est un
  paramètre transverse, vérifié fonctionnel à l'usage.
- L'image d'entrée est un **data URI complet**, préfixe MIME inclus, sans
  retour à la ligne dans le base64.
- `detail` accepte `auto`, `low`, `high`, `original`.

### Réponse

L'image est dans `choices[0].message.images[0].image_url.url`, sous forme de
**data URI préfixé** (`data:image/png;base64,...`) et non de base64 nu.

La spec précise « URL *or* base64-encoded data » : le code teste donc le préfixe
et lève une erreur explicite si une URL distante est renvoyée, plutôt que
d'écrire un fichier corrompu.

### Authentification

Header `Authorization: Bearer <clé>`, fourni par la credential n8n
**`OpenRouter Clothify`** (type `httpHeaderAuth`, id `openrouterClothify01`).

Ne pas revenir à `$env.OPENROUTER_API_KEY` : n8n bloque l'accès aux variables
d'environnement dans les nœuds (`N8N_BLOCK_ENV_ACCESS_IN_NODE`), et le
débloquer exposerait **toutes** les variables à **tous** les workflows. La
credential reste chiffrée et n'est lisible que par les nœuds qui la référencent.

## 4. Coûts

Mesurés sur des appels réels, image d'entrée 1024 px, sortie 1024×1024 :

| Modèle | Tokens image | Coût / image | Latence |
|---|---|---|---|
| `openai/gpt-5-image-mini` **(actuel)** | ~7 000 | **~0,05 $** | 50-60 s |
| `openai/gpt-5.4-image-2` | 7 024 | 0,232 $ | ~100 s |

Le tarif par token est trompeur : une image générée pèse ~7 000 tokens de
sortie, soit 5 à 6 fois plus qu'une estimation naïve à 1 290 tokens. **Toujours
mesurer sur un appel réel avant de dimensionner un budget.**

Qualité constatée : rendu réaliste et fidèle sur les matières et les coupes.
`mini` déforme parfois les petits textes brodés — visible sur un logo, pas sur
un aplat de couleur.

### Changer de modèle

Une seule ligne, dans le nœud `📦 Prepare API Body` :

```js
const apiBody = {
  model: 'openai/gpt-5-image-mini',   // ← ici
  modalities: ['image', 'text'],
  ...
};
```

Puis réimporter et réactiver (voir §6). Les modèles disponibles se listent avec :

```bash
curl -s https://openrouter.ai/api/v1/models \
  | jq -r '.data[] | select(.architecture.output_modalities[]? == "image") | .id'
```

## 5. Modes de défaillance connus

Cinq causes réelles rencontrées en production, avec leur signature exacte.

| Symptôme | Cause | Correctif |
|---|---|---|
| `Cannot read properties of undefined (reading 'execute')` à l'activation | `typeVersion` du nœud supérieur à ce que connaît n8n 1.119.2 | rester en `httpRequest` **4.2** |
| `access to env vars denied` | usage de `$env` dans un nœud | passer par une credential |
| `401 — No cookie auth credentials found` | `nodeCredentialType` employé au lieu de `genericAuthType` | `genericAuthType: "httpHeaderAuth"` |
| Statut bloqué à `processing`, fichier pourtant écrit | course entre `Update Processing` et `Update Done` | chaîne séquentielle (§2) |
| Exécution `canceled` à exactement 60 s | `executionTimeout: 60` dans les réglages du workflow | relever à **600 s** |

Le dernier est le plus coûteux : l'appel est annulé **après** facturation, donc
chaque échec consomme du crédit sans produire d'image.

`nodeCredentialType` et `genericAuthType` méritent une note : les deux existent
sur le nœud HTTP Request, mais chacun n'est lu que si `authentication` vaut la
valeur correspondante (`predefinedCredentialType` pour le premier,
`genericCredentialType` pour le second). Se tromper ne produit aucune erreur de
validation — le paramètre est ignoré, n8n retombe sur l'auth par cookie, et
l'échec apparaît bien plus loin sous forme d'un 401 trompeur.

## 6. Déployer une modification de workflow

```bash
# 1. Exporter l'état courant (sauvegarde + versionnement)
docker exec <n8n> n8n export:workflow --all --output=/tmp/wf.json

# 2. Modifier le JSON, puis réimporter
docker exec <n8n> n8n import:workflow --input=/tmp/wf.json

# 3. L'import DESACTIVE les workflows : les réactiver explicitement
docker exec <n8n> n8n update:workflow --id=emFvQESqlf4RPN6Q --active=false
docker exec <n8n> n8n update:workflow --id=Qdtp2SCgNQ1SUE6K --active=true

# 4. Redémarrer — l'activation n'est prise en compte qu'au démarrage
docker restart <n8n>

# 5. Vérifier
docker logs --since 2m <n8n> | grep "Activated workflow"
```

Puis rejouer un test bout en bout (§7) et réexporter dans `n8n/workflows/`.

## 7. Tester sans Discord

`scripts/e2e_test.sh` insère **un seul** job et observe la base et le disque :

```bash
bash scripts/e2e_test.sh /data/clothify_shared/input_image/exemple.png pull woman 2 420
```

Il vérifie l'enchaînement `pending → processing → done`, l'existence du fichier
de sortie, sa taille et ses magic bytes. Verdict `PASS` / `FAIL` explicite.

Chaque exécution réussie consomme un appel API (~0,05 $) — c'est un test de
recette, pas un test de non-régression à lancer en boucle.

Pour observer une exécution en échec, l'historique n8n donne le nœud fautif :

```sql
-- dans la base SQLite de n8n
SELECT id, status, startedAt, stoppedAt FROM execution_entity ORDER BY id DESC LIMIT 5;
```

Le détail de l'erreur est dans `execution_data`, sérialisé au format `flatted`
(les références y sont des index sous forme de chaîne — il faut les résoudre
pour lire le message).
