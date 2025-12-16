#!/usr/bin/env python3
"""
Clothify Image Processor
Genere des images de vetements sur modele via Google Gemini API.

Usage:
  python main.py              # Traite 1 image aleatoire
  python main.py --all        # Traite toutes les images
  python main.py image.jpg    # Traite une image specifique
"""

import argparse
import base64
import random
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
import os

# Charger les variables d'environnement
load_dotenv(Path(__file__).parent.parent / ".env")

# Configuration
INPUT_DIR = Path(__file__).parent.parent / "images" / "input"
OUTPUT_DIR = Path(__file__).parent.parent / "images" / "output"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-image-preview:generateContent"

# Mapping des tailles
SIZE_MAPPING = {
    "1": {
        "code": "XS",
        "label": "Extra Small",
        "bodyDescription": "petite slim build, 155-160cm, delicate frame",
        "fit": "fitted close to body",
    },
    "2": {
        "code": "S/M",
        "label": "Small/Medium",
        "bodyDescription": "average build, balanced proportions, 165-170cm",
        "fit": "regular fit",
    },
    "3": {
        "code": "L",
        "label": "Large",
        "bodyDescription": "athletic build, broader shoulders, 175-180cm",
        "fit": "comfortable fit",
    },
    "4": {
        "code": "XL",
        "label": "Extra Large",
        "bodyDescription": "plus size, full figured, 170-175cm",
        "fit": "relaxed fit",
    },
}

# Mapping des types de vetements
TYPE_MAPPING = {
    "echarpe": {
        "category": "accessory",
        "placement": "draped around neck and shoulders",
        "focus": "texture and pattern",
    },
    "pull": {
        "category": "top",
        "placement": "worn on upper body",
        "focus": "knit texture, shoulder fit",
    },
    "tshirt": {
        "category": "top",
        "placement": "casual on upper body",
        "focus": "fabric drape, neckline",
    },
    "chemise": {
        "category": "top",
        "placement": "buttoned, collar visible",
        "focus": "collar, buttons, fabric",
    },
    "veste": {
        "category": "outerwear",
        "placement": "worn open",
        "focus": "structure, lapels",
    },
    "manteau": {
        "category": "outerwear",
        "placement": "full length",
        "focus": "silhouette, material",
    },
    "pantalon": {
        "category": "bottom",
        "placement": "full length lower body",
        "focus": "waist fit, leg line",
    },
    "jean": {
        "category": "bottom",
        "placement": "casual stance",
        "focus": "denim texture, fit",
    },
    "short": {
        "category": "bottom",
        "placement": "thigh length",
        "focus": "fit and proportion",
    },
    "jupe": {
        "category": "bottom",
        "placement": "movement captured",
        "focus": "flow, silhouette",
    },
    "robe": {
        "category": "dress",
        "placement": "full body elegant",
        "focus": "silhouette, fabric flow",
    },
    "bonnet": {
        "category": "accessory",
        "placement": "on head",
        "focus": "fit and texture",
    },
    "casquette": {
        "category": "accessory",
        "placement": "on head front",
        "focus": "shape and design",
    },
    "sac": {
        "category": "accessory",
        "placement": "held or shoulder",
        "focus": "shape, material",
    },
}

# Mapping des types MIME
MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def list_input_images() -> list[Path]:
    """Liste toutes les images valides dans le dossier input."""
    if not INPUT_DIR.exists():
        print(f"Erreur: Le dossier {INPUT_DIR} n'existe pas.")
        sys.exit(1)

    images = [
        f
        for f in INPUT_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    ]

    if not images:
        print(f"Erreur: Aucune image trouvee dans {INPUT_DIR}")
        sys.exit(1)

    return sorted(images)


def parse_filename(filename: str) -> dict:
    """
    Parse le nom de fichier au format: nom-type-taille.ext
    Exemple: echarpe_burberry-echarpe-2.jpg
    """
    name_without_ext = Path(filename).stem
    extension = Path(filename).suffix.lower()
    parts = name_without_ext.split("-")

    if len(parts) < 3:
        print(f"Avertissement: Format invalide pour {filename}. Attendu: nom-type-taille.ext")
        # Valeurs par defaut si format invalide
        return {
            "fileName": filename,
            "nameWithoutExt": name_without_ext,
            "extension": extension,
            "mimeType": MIME_TYPES.get(extension, "image/jpeg"),
            "productName": name_without_ext,
            "garmentType": "clothing",
            "sizeCode": "2",
            "sizeInfo": SIZE_MAPPING["2"],
            "typeInfo": {
                "category": "clothing",
                "placement": "worn appropriately",
                "focus": "fit and texture",
            },
        }

    size_code = parts[-1]
    garment_type = parts[-2]
    product_name = "-".join(parts[:-2])

    size_info = SIZE_MAPPING.get(size_code, SIZE_MAPPING["2"])
    type_info = TYPE_MAPPING.get(
        garment_type.lower(),
        {"category": "clothing", "placement": "worn appropriately", "focus": "fit and texture"},
    )

    return {
        "fileName": filename,
        "nameWithoutExt": name_without_ext,
        "extension": extension,
        "mimeType": MIME_TYPES.get(extension, "image/jpeg"),
        "productName": product_name,
        "garmentType": garment_type,
        "sizeCode": size_code,
        "sizeInfo": size_info,
        "typeInfo": type_info,
    }


def generate_prompt(metadata: dict) -> str:
    """Genere le prompt optimise pour Gemini."""
    product_name = metadata["productName"].replace("_", " ")
    garment_type = metadata["garmentType"]
    size_info = metadata["sizeInfo"]
    type_info = metadata["typeInfo"]

    prompt = f"""Transform this product photo into a professional e-commerce image.

TASK: Place this {garment_type} ({product_name}) on a realistic human model.

MODEL REQUIREMENTS:
- Body type: {size_info['bodyDescription']}
- Size: {size_info['label']}
- Natural, relaxed pose
- Photorealistic human appearance

GARMENT DISPLAY:
- {type_info['placement']}
- Emphasize: {type_info['focus']}
- The garment must be clearly recognizable from the input image
- Perfect fit, no wrinkles

PHOTOGRAPHY STYLE:
- Professional studio lighting (soft, even)
- Clean white or light gray seamless background
- High-resolution, sharp fabric details
- Luxury e-commerce aesthetic (like NET-A-PORTER, SSENSE)
- Commercial product photography quality

IMPORTANT: Keep the original garment design, colors, and details exactly as shown in the input image."""

    return prompt


def read_image_as_base64(image_path: Path) -> tuple[str, str]:
    """Lit une image et retourne son contenu en base64 avec le type MIME."""
    with open(image_path, "rb") as f:
        image_data = f.read()

    base64_data = base64.b64encode(image_data).decode("utf-8")
    mime_type = MIME_TYPES.get(image_path.suffix.lower(), "image/jpeg")

    return base64_data, mime_type


def call_gemini_api(prompt: str, image_b64: str, mime_type: str) -> str:
    """Appelle l'API Gemini pour generer l'image."""
    api_key = os.getenv("GOOGLE_AI_API_KEY")
    if not api_key:
        print("Erreur: GOOGLE_AI_API_KEY non defini dans .env")
        sys.exit(1)

    url = f"{GEMINI_API_URL}?key={api_key}"

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": mime_type, "data": image_b64}},
                ]
            }
        ],
        "generationConfig": {"responseModalities": ["image", "text"], "temperature": 0.4},
        "safetySettings": [
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"}
        ],
    }

    print("  Appel API Gemini en cours (peut prendre jusqu'a 3 minutes)...")

    with httpx.Client(timeout=180.0) as client:
        response = client.post(url, json=payload)

    if response.status_code != 200:
        print(f"Erreur API: {response.status_code}")
        print(response.text[:1000])
        return None

    data = response.json()

    # Extraire l'image de la reponse
    if "candidates" in data and data["candidates"]:
        parts = data["candidates"][0].get("content", {}).get("parts", [])
        for part in parts:
            if "inlineData" in part and "data" in part["inlineData"]:
                return part["inlineData"]["data"]

    print("Erreur: Aucune image dans la reponse Gemini")
    print(str(data)[:1000])
    return None


def save_output_image(image_b64: str, output_path: Path) -> bool:
    """Sauvegarde l'image base64 dans un fichier."""
    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        image_data = base64.b64decode(image_b64)
        with open(output_path, "wb") as f:
            f.write(image_data)
        return True
    except Exception as e:
        print(f"Erreur lors de la sauvegarde: {e}")
        return False


def process_image(image_path: Path) -> dict:
    """Traite une seule image et retourne le resultat."""
    print(f"\n{'='*60}")
    print(f"Traitement: {image_path.name}")
    print(f"{'='*60}")

    # 1. Parser le nom de fichier
    metadata = parse_filename(image_path.name)
    print(f"  Produit: {metadata['productName']}")
    print(f"  Type: {metadata['garmentType']}")
    print(f"  Taille: {metadata['sizeInfo']['label']}")

    # 2. Generer le prompt
    prompt = generate_prompt(metadata)

    # 3. Lire l'image en base64
    image_b64, mime_type = read_image_as_base64(image_path)
    print(f"  Image lue: {len(image_b64)} caracteres base64")

    # 4. Appeler l'API Gemini
    result_b64 = call_gemini_api(prompt, image_b64, mime_type)

    if not result_b64:
        return {"success": False, "input": image_path.name, "error": "API call failed"}

    # 5. Sauvegarder l'image generee
    output_filename = f"{metadata['nameWithoutExt']}_generated.png"
    output_path = OUTPUT_DIR / output_filename

    if save_output_image(result_b64, output_path):
        print(f"  Image generee: {output_path}")
        return {
            "success": True,
            "input": image_path.name,
            "output": str(output_path),
            "product": metadata["productName"],
            "type": metadata["garmentType"],
            "size": metadata["sizeInfo"]["label"],
        }
    else:
        return {"success": False, "input": image_path.name, "error": "Save failed"}


def main():
    parser = argparse.ArgumentParser(
        description="Clothify - Generateur d'images de vetements sur modele"
    )
    parser.add_argument(
        "--all", action="store_true", help="Traiter toutes les images du dossier input"
    )
    parser.add_argument(
        "image", nargs="?", help="Nom de l'image specifique a traiter (optionnel)"
    )

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  CLOTHIFY - Image Processor")
    print("=" * 60)

    # Lister les images disponibles
    images = list_input_images()
    print(f"\nImages disponibles: {len(images)}")

    # Determiner quelles images traiter
    if args.image:
        # Image specifique
        image_path = INPUT_DIR / args.image
        if not image_path.exists():
            print(f"Erreur: Image '{args.image}' non trouvee dans {INPUT_DIR}")
            sys.exit(1)
        images_to_process = [image_path]
    elif args.all:
        # Toutes les images
        images_to_process = images
    else:
        # Une image aleatoire (defaut)
        images_to_process = [random.choice(images)]

    print(f"Images a traiter: {len(images_to_process)}")

    # Traiter les images
    results = []
    for image_path in images_to_process:
        result = process_image(image_path)
        results.append(result)

    # Resume final
    print("\n" + "=" * 60)
    print("  RESUME")
    print("=" * 60)

    success_count = sum(1 for r in results if r["success"])
    print(f"\nResultats: {success_count}/{len(results)} succes")

    for result in results:
        status = "OK" if result["success"] else "ERREUR"
        print(f"  [{status}] {result['input']}")
        if result["success"]:
            print(f"        -> {result['output']}")

    print()


if __name__ == "__main__":
    main()
