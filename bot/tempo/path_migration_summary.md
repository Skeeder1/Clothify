# Migration des chemins: /files → /clothify_shared

## Changement effectué
Tous les chemins ont été migrés de `/files` vers `/clothify_shared` pour correspondre à la configuration Coolify en production.

## Fichiers modifiés

### Configuration
- **bot/config.py**: `SHARED_VOLUME_PATH` default value `/files` → `/clothify_shared`
- **.env**: `SHARED_VOLUME_PATH=/clothify_shared`
- **.env.example**: `SHARED_VOLUME_PATH=/clothify_shared`

### Docker
- **docker-compose.yml**: 
  - n8n volume mount: `clothify_shared:/clothify_shared`
  - bot volume mount: `clothify_shared:/clothify_shared`
  - bot env var: `SHARED_VOLUME_PATH=/clothify_shared`
  
- **bot/Dockerfile**: `mkdir /clothify_shared/input_image /clothify_shared/output_image`

### Tests
- **bot/connectivity_test.py**: Default path `/files` → `/clothify_shared`
- **bot/tests/connectivity_test.py**: Utilise déjà `Config.INPUT_DIR` (✅ correct)

## Structure résultante

```
/clothify_shared/
├── input_image/   (uploads Discord)
└── output_image/  (résultats IA)
```

## Chemins dérivés automatiquement
```python
SHARED_VOLUME_PATH = "/clothify_shared"
INPUT_DIR  = "/clothify_shared/input_image"
OUTPUT_DIR = "/clothify_shared/output_image"
```

## Actions à faire sur Coolify

1. **Vérifier la variable d'environnement:**
   ```
   SHARED_VOLUME_PATH=/clothify_shared
   ```

2. **Vérifier le montage du volume:**
   - Le volume persistant doit être monté à `/clothify_shared` dans le container

3. **Rebuild le container:**
   ```bash
   # Coolify va rebuild automatiquement avec le nouveau Dockerfile
   ```

4. **Activer les logs DEBUG (optionnel):**
   ```
   LOG_LEVEL=DEBUG
   ```

## Vérification post-déploiement

```bash
# Vérifier le montage
docker inspect <container_bot> | grep -A 10 Mounts

# Tester l'écriture
docker exec -it <container_bot> bash
touch /clothify_shared/input_image/test.txt
ls -la /clothify_shared/input_image/
```
