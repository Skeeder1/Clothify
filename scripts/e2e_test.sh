#!/usr/bin/env bash
# Test bout en bout de la génération d'image Clothify, SANS passer par Discord.
#
# Principe : le bot Discord ne fait qu'insérer une ligne dans public.jobs ; c'est
# le NOTIFY PostgreSQL qui réveille n8n. On court-circuite donc Discord en
# insérant nous-mêmes exactement UN job, puis on observe la base et le fichier
# de sortie.
#
# Coût : UN seul appel au modèle d'image (~0,06 $ avec gpt-5-image-mini).

set -uo pipefail

# Surchargeables : les valeurs par defaut correspondent au deploiement Coolify.
PG="${CLOTHIFY_PG_CONTAINER:-jkgk0go0kwc8c0w80kwg4ggw}"
N8N="${CLOTHIFY_N8N_CONTAINER:-n8n-cgs40kwkwg8owswoo0c08ssw}"
SHARED="${CLOTHIFY_SHARED_PATH:-/data/clothify_shared}"
SRC_IMAGE="${1:?usage: e2e_test.sh <image_source> [garment] [genre] [size] [timeout_s]}"
GARMENT="${2:-tshirt}"
GENRE="${3:-woman}"
SIZE="${4:-2}"
TIMEOUT_S="${5:-420}"

STAMP="e2e-$(date +%Y%m%d-%H%M%S)"
TEST_IMG="${STAMP}.png"
IN_HOST="$SHARED/input_image/$TEST_IMG"
OUT_HOST="$SHARED/output_image/${STAMP}_generated.png"
IN_CONTAINER="/clothify_shared/input_image/$TEST_IMG"

psql_q() { docker exec "$PG" sh -c "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -tAc \"$1\"" 2>/dev/null; }

echo "=========================================="
echo " Test E2E Clothify — sans Discord"
echo "=========================================="

# 1. Image d'entrée -----------------------------------------------------
if [ ! -f "$SRC_IMAGE" ]; then
  echo "FAIL : image source introuvable : $SRC_IMAGE"; exit 1
fi
cp "$SRC_IMAGE" "$IN_HOST" || { echo "FAIL : copie impossible vers $IN_HOST"; exit 1; }
chmod 644 "$IN_HOST"
echo "1/4  image de test  : $TEST_IMG ($(stat -c%s "$IN_HOST") octets)"

# 2. Insertion d'UN job -------------------------------------------------
USER_ID=$(psql_q "SELECT user_id FROM public.jobs WHERE user_id IS NOT NULL ORDER BY created_at DESC LIMIT 1;" | tr -d '[:space:]')
[ -z "$USER_ID" ] && USER_ID=$(psql_q "SELECT uuid_generate_v4();" | tr -d '[:space:]')

# L'UUID est généré côté client : `psql -tAc` avec INSERT ... RETURNING renvoie
# aussi la ligne de statut « INSERT 0 1 », qui se collait à l'identifiant.
JOB_ID=$(cat /proc/sys/kernel/random/uuid)
psql_q "INSERT INTO public.jobs (id, user_id, discord_message_id, input_file_paths, product_name, size, status, garment, genre, angle) VALUES ('$JOB_ID', '$USER_ID', '0', '[\\\"$IN_CONTAINER\\\"]', '$STAMP', '$SIZE', 'pending', '$GARMENT', '$GENRE', 'face');" >/dev/null

FOUND=$(psql_q "SELECT count(*) FROM public.jobs WHERE id='$JOB_ID';" | tr -d '[:space:]')
[ "$FOUND" != "1" ] && JOB_ID=""

if [ -z "$JOB_ID" ]; then
  echo "FAIL : insertion du job impossible"; rm -f "$IN_HOST"; exit 1
fi
echo "2/4  job insere     : $JOB_ID (garment=$GARMENT genre=$GENRE size=$SIZE)"

# 3. Attente du traitement ---------------------------------------------
echo "3/4  attente (timeout ${TIMEOUT_S}s)..."
STATUS=""
ELAPSED=0
while [ $ELAPSED -lt "$TIMEOUT_S" ]; do
  STATUS=$(psql_q "SELECT status FROM public.jobs WHERE id='$JOB_ID';" | tr -d '[:space:]')
  case "$STATUS" in
    done|error|sent) break ;;
  esac
  sleep 5
  ELAPSED=$((ELAPSED + 5))
  [ $((ELAPSED % 30)) -eq 0 ] && echo "     ${ELAPSED}s — statut: ${STATUS:-<vide>}"
done
echo "     statut final : ${STATUS:-<aucun>} apres ${ELAPSED}s"

# 4. Verdict ------------------------------------------------------------
if [ "$STATUS" = "error" ]; then
  echo "4/4  ECHEC — message d erreur en base :"
  psql_q "SELECT error_message FROM public.jobs WHERE id='$JOB_ID';" | head -5 | sed 's/^/     /'
  echo; echo "VERDICT : FAIL"; exit 1
fi

if [ "$STATUS" != "done" ] && [ "$STATUS" != "sent" ]; then
  echo "4/4  ECHEC — le job n a pas abouti (statut bloque a '${STATUS:-vide}')"
  echo "     derniers logs n8n :"
  docker logs --since 8m "$N8N" 2>&1 | grep -iE "error|fail" | tail -5 | sed 's/^/     /'
  echo; echo "VERDICT : FAIL"; exit 1
fi

OUT_DB=$(psql_q "SELECT output_file_path FROM public.jobs WHERE id='$JOB_ID';" | tr -d '[:space:]')
OUT_REAL="$SHARED/output_image/$(basename "$OUT_DB")"

if [ ! -f "$OUT_REAL" ]; then
  echo "4/4  ECHEC — fichier de sortie absent : $OUT_REAL"
  echo; echo "VERDICT : FAIL"; exit 1
fi

BYTES=$(stat -c%s "$OUT_REAL")
MAGIC=$(head -c 8 "$OUT_REAL" | od -An -tx1 | tr -d ' \n')
case "$MAGIC" in
  89504e47*) FMT="PNG" ;;
  ffd8ff*)   FMT="JPEG" ;;
  *)         FMT="INCONNU ($MAGIC)" ;;
esac

echo "4/4  sortie         : $OUT_REAL"
echo "     taille         : $BYTES octets"
echo "     format         : $FMT"

if [ "$BYTES" -lt 10000 ] || [ "$FMT" = "INCONNU ($MAGIC)" ]; then
  echo; echo "VERDICT : FAIL (fichier trop petit ou format invalide)"; exit 1
fi

echo
echo "VERDICT : PASS"
echo "  job    : $JOB_ID"
echo "  duree  : ${ELAPSED}s"
echo "  fichier: $OUT_REAL"
