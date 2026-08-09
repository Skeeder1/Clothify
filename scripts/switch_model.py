#!/usr/bin/env python3
"""Bascule le modèle de génération d'images du workflow n8n de production.

À exécuter sur l'hôte Docker (le script pilote n8n via `docker exec`).

    sudo python3 scripts/switch_model.py --list
    sudo python3 scripts/switch_model.py gpt-5-image-mini
    sudo python3 scripts/switch_model.py --dry-run gpt-5.4-image-2

Un preset décrit le contrat COMPLET d'un fournisseur, pas seulement un nom de
modèle : endpoint, credential, et — si le fournisseur change — le code qui
construit la requête et celui qui extrait l'image. Deux presets du même
fournisseur ne diffèrent que par `model`, donc la bascule y est immédiate.

Le script fait : export -> patch -> import -> réactivation -> redémarrage ->
vérification. L'activation n8n n'étant prise en compte qu'au démarrage, le
redémarrage n'est pas optionnel.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time

N8N = "n8n-cgs40kwkwg8owswoo0c08ssw"
PROD_ID = "Qdtp2SCgNQ1SUE6K"
TEST_ID = "emFvQESqlf4RPN6Q"
PROD_NAME = "production-Clothify-n8n"
REMOTE = "/tmp/switch_model_wf.json"

# Presets OpenRouter : même endpoint, même credential, même format ; seul
# l'identifiant de modèle change. Coûts et latences ci-dessous mesurés sur une
# comparaison réelle (même image, même prompt, 2026-08-09), pas estimés.
PRESETS = {
    "gpt-5.4-image-2": {
        "provider": "openrouter",
        "model": "openai/gpt-5.4-image-2",
        "cost": "0,230 $/image",
        "note": "DÉFAUT — meilleur rendu mesuré : plan complet, morphologie "
                "conforme, logo lisible. ~135 s de bout en bout.",
    },
    "gpt-5-image-mini": {
        "provider": "openrouter",
        "model": "openai/gpt-5-image-mini",
        "cost": "0,051 $/image",
        "note": "4,5x moins cher et 2x plus rapide ; déforme les petits textes "
                "brodés. Le bon choix si le volume prime sur la finition.",
    },
    "gpt-5-image": {
        "provider": "openrouter",
        "model": "openai/gpt-5-image",
        "cost": "0,224 $/image",
        "note": "prix équivalent à gpt-5.4-image-2 mais qualité inférieure sur "
                "notre test (logo illisible, morphologie hors consigne).",
    },
    "gemini-3-pro": {
        "provider": "openrouter",
        "model": "google/gemini-3-pro-image",
        "cost": "0,137 $/image",
        "note": "le plus rapide (~19 s) et superbe sur la matière, MAIS recopie "
                "le cadrage de l'image source — sur une capture d'app, il "
                "reproduit l'interface. À réserver aux entrées déjà détourées.",
    },
}

# Rappel affiché à la bascule : tous les modèles joignables via OpenRouter
# marquent leurs images (SynthID côté Google, C2PA + SynthID côté OpenAI).
WATERMARKED = {"openrouter"}


def docker(*args: str, capture: bool = True) -> str:
    cmd = ["docker", *args]
    r = subprocess.run(cmd, capture_output=capture, text=True)
    if r.returncode != 0 and capture:
        sys.exit(f"échec: {' '.join(cmd)}\n{r.stderr[-400:]}")
    return r.stdout if capture else ""


def load_workflows() -> list[dict]:
    docker("exec", N8N, "n8n", "export:workflow", "--all", f"--output={REMOTE}")
    raw = docker("exec", N8N, "cat", REMOTE)
    return json.loads(raw)


def current_model(workflows: list[dict]) -> str | None:
    for wf in workflows:
        if wf.get("name") != PROD_NAME:
            continue
        for node in wf["nodes"]:
            if node["name"] == "📦 Prepare API Body":
                m = re.search(r"model:\s*'([^']+)'", node["parameters"]["jsCode"])
                return m.group(1) if m else None
    return None


def apply_preset(workflows: list[dict], preset: dict) -> bool:
    changed = False
    for wf in workflows:
        if wf.get("name") != PROD_NAME:
            continue
        for node in wf["nodes"]:
            if node["name"] != "📦 Prepare API Body":
                continue
            code = node["parameters"]["jsCode"]
            new = re.sub(r"(model:\s*)'[^']+'", rf"\1'{preset['model']}'", code, count=1)
            if new != code:
                node["parameters"]["jsCode"] = new
                changed = True
    return changed


def deploy(workflows: list[dict]) -> None:
    payload = json.dumps(workflows, ensure_ascii=False)
    subprocess.run(["docker", "exec", "-i", N8N, "sh", "-c", f"cat > {REMOTE}"],
                   input=payload, text=True, check=True)
    docker("exec", N8N, "n8n", "import:workflow", f"--input={REMOTE}")
    # l'import désactive tout : on rétablit explicitement l'état voulu
    docker("exec", N8N, "n8n", "update:workflow", f"--id={TEST_ID}", "--active=false")
    docker("exec", N8N, "n8n", "update:workflow", f"--id={PROD_ID}", "--active=true")
    docker("exec", N8N, "rm", "-f", REMOTE)
    print("  redémarrage de n8n (l'activation n'est lue qu'au démarrage)...")
    docker("restart", N8N)


def wait_healthy(timeout: int = 180) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        state = docker("inspect", "--format", "{{.State.Health.Status}}", N8N).strip()
        if state == "healthy":
            return True
        time.sleep(4)
    return False


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("preset", nargs="?", help="nom du preset à appliquer")
    p.add_argument("--list", action="store_true", help="lister les presets et le modèle courant")
    p.add_argument("--dry-run", action="store_true", help="montrer le changement sans déployer")
    a = p.parse_args()

    workflows = load_workflows()
    now = current_model(workflows)

    if a.list or not a.preset:
        print(f"modèle courant : {now}\n")
        print("presets disponibles :")
        for name, cfg in PRESETS.items():
            mark = "  <- actuel" if cfg["model"] == now else ""
            print(f"  {name:<20} {cfg['model']:<32} {cfg['cost']:<16}{mark}")
            print(f"  {'':<20} {cfg['note']}")
        print("\nQwen / FLUX / HiDream ne sont PAS servis par OpenRouter (0 modèle")
        print("open-weight sur 400). Les ajouter suppose un second fournisseur")
        print("(fal.ai ou DeepInfra) et donc un preset avec son propre endpoint,")
        print("sa credential et son code de requête/extraction.")
        return 0

    if a.preset not in PRESETS:
        return p.error(f"preset inconnu: {a.preset!r} (voir --list)")

    preset = PRESETS[a.preset]
    if preset["model"] == now:
        print(f"déjà sur {preset['model']} — rien à faire.")
        return 0

    print(f"bascule : {now}  ->  {preset['model']}  ({preset['cost']})")
    if not apply_preset(workflows, preset):
        sys.exit("échec: nœud « 📦 Prepare API Body » ou clé `model:` introuvable")

    if a.dry_run:
        print("  --dry-run : aucun déploiement effectué.")
        return 0

    deploy(workflows)
    if not wait_healthy():
        sys.exit("échec: n8n n'est pas revenu en healthy")

    logs = docker("logs", "--since", "3m", N8N)
    ok = "Activated workflow" in logs and PROD_ID in logs
    print(f"  n8n healthy, workflow {'activé' if ok else 'NON activé — vérifier les logs'}")

    if preset["provider"] in WATERMARKED:
        print("  note : ce fournisseur marque ses images (SynthID / C2PA).")

    print("\nvérifier par un test réel (consomme du crédit) :")
    print("  bash scripts/e2e_test.sh <image> pull woman 2 420")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
