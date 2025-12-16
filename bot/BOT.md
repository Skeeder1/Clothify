# Clothify Bot - Guide d'utilisation

## Présentation

Clothify Bot est un bot Discord interactif qui génère des images professionnelles de produits e-commerce à partir de vos photos.

---

## Comment utiliser le bot

### Étape 1 : Envoyer une image

Uploadez simplement une image dans le canal Discord (JPG, PNG ou WebP). Pas besoin de renommer le fichier !

```
[Vous uploadez: mon_image.jpg]
```

### Étape 2 : Sélectionner le type de vêtement

Le bot répond avec un **menu déroulant**. Cliquez dessus et sélectionnez le type de vêtement.

```
🧥 Quel type de vêtement ?

┌─────────────────────────────┐
│ Sélectionnez un vêtement ▼  │
└─────────────────────────────┘
```

### Étape 3 : Choisir la taille du visuel

Le bot affiche des **boutons** pour choisir la taille du visuel.

```
📏 Quelle taille ?

[1 - Petit]  [2 - Standard]  [3 - Moyen]  [4 - Grand]
```

### Étape 4 : Confirmation

Le bot confirme la création du job :

```
✅ Job créé avec succès !

ID: ABC123
Vêtement: Pull
Taille: Standard

⏳ Traitement en cours...
```

### Étape 5 : Recevoir le résultat

Une fois le traitement terminé, le bot répond avec l'image générée et ajoute une réaction ✅.

---

## Commandes disponibles

| Commande | Description |
|----------|-------------|
| `!help` | Affiche l'aide du bot |
| `!status` | Montre le statut du bot et vos statistiques |

---

## Types de vêtements disponibles

| Emoji | Vêtement |
|-------|----------|
| 🧣 | Écharpe |
| 🧥 | Pull |
| 👕 | T-shirt |
| 👔 | Chemise |
| 🧥 | Veste |
| 🧥 | Manteau |
| 👖 | Pantalon |
| 👖 | Jean |
| 🩳 | Short |
| 👗 | Jupe |
| 👗 | Robe |
| 🧢 | Bonnet |
| 🧢 | Casquette |
| 👜 | Sac |
| ❓ | Autre |

---

## Tailles de visuel

| Taille | Description |
|--------|-------------|
| **1 - Petit** | Gros plan sur le produit |
| **2 - Standard** | Vue classique e-commerce |
| **3 - Moyen** | Produit avec contexte |
| **4 - Grand** | Vue d'ensemble |

---

## Ajouter un prompt personnalisé

Vous pouvez ajouter du texte avec votre image pour personnaliser la génération :

```
[Upload: image.jpg]
Message: "Fond blanc minimaliste, éclairage studio"
```

Le texte sera utilisé comme instruction supplémentaire pour l'IA.

---

## Réactions du bot

| Réaction | Signification |
|----------|---------------|
| ⏳ | Job créé, traitement en cours |
| ✅ | Traitement terminé, image envoyée |
| ❌ | Erreur (fichier invalide, échec sauvegarde) |

---

## Formats d'image acceptés

- `.jpg` / `.jpeg`
- `.png`
- `.webp`

---

## FAQ

### Le bot ne répond pas après mon upload ?

Vérifiez que :
1. Le bot est en ligne (`!status`)
2. Votre image est dans un format supporté (JPG, PNG, WebP)
3. Vous êtes dans un canal où le bot a accès

### Ma session a expiré ?

Si vous ne complétez pas la sélection dans les **5 minutes**, la session expire. Renvoyez simplement votre image.

### Puis-je envoyer plusieurs images ?

Oui ! Envoyez plusieurs images dans le même message. Elles seront toutes associées au même job.

### Où sont stockées mes images ?

- Images d'entrée : `./images/input/`
- Images générées : `./images/output/`

### Comment voir mes jobs en attente ?

Tapez `!status` pour voir le nombre de jobs en attente et vos statistiques personnelles.

### Combien de temps prend le traitement ?

Le temps dépend de la charge du serveur. En général, entre 30 secondes et 2 minutes.
