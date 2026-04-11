# ⚡ Quick Start - Présentation 15 Min

**TL;DR - Faire la présentation en 5 min:**

## Installation (Une seule fois)

```bash
# Installer python-pptx
pip install python-pptx

# Générer les slides PowerPoint
python generate_slides_v2.py
# ✅ Crée: Puls-Events-RAG-Presentation-v2.pptx
```

## Lecture (Jour de la présentation)

1. **Ouvrir les fichiers:**
   - Slides: `Puls-Events-RAG-Presentation-v2.pptx` (présentation)
   - Script: `ORAL_SCRIPT_V2.md` (ce que lire)
   - Guide: `HOWTO_PRESENTATION.md` (aide complète)

2. **Pratiquer le timing:**
   ```
   - Slide 1-7: ~9 minutes (script oral)
   - Demo: +2 minutes (optionnel)
   - Q&A: +5 minutes
   = 15 minutes total
   ```

3. **Jour de la présentation:**
   ```bash
   # Démarrer services
   docker-compose up
   
   # Ouvrir PowerPoint
   # Lire script sur moniteur secondaire
   # Cliquer → Next slide
   # Garder le timing!
   ```

## 7 Slides - Vue d'ensemble

| # | Titre | Type | Durée |
|---|-------|------|-------|
| 1 | Puls-Events RAG | Titre | 0:30 |
| 2 | Le Problème | Contenu (5 points) | 1:30 |
| 3 | La Solution: RAG | Contenu (9 points) | 2:00 |
| 4 | Architecture | 2 colonnes | 1:45 |
| 5 | Tech Stack | 2 colonnes | 1:00 |
| 6 | Résultats & Metrics | Contenu (8 points) | 1:30 |
| 7 | Conclusion | Contenu (5 points) | 1:00 |

## ✨ Ce Qui Impressionne

**Sur Slide 6 - Optionnel Live Demo (30 sec):**
```
Ouvrir: http://localhost:8501
Cliquer: Onglet "Chatbot"
Poser: "Quels événements demain à Paris?"
→ IA répond avec vraies données!
```

## 📚 Tous les Fichiers Fournis

```
generate_slides_v2.py      ← Script pour générer slides PowerPoint
ORAL_SCRIPT_V2.md          ← Texte à lire (slide par slide)
HOWTO_PRESENTATION.md      ← Guide complet + Q&A + checklist
PRESENTATION_QUICKSTART.md ← Ce fichier (TL;DR)
```

## ❓ Questions Fréquentes

**Q: Combien de temps?**
A: 15 minutes exactement (9 min présentation + 6 min Q&A)

**Q: Slides modifiables?**
A: Oui! `generate_slides_v2.py` est du code Python facile à modifier

**Q: Besoin de demo live?**
A: Non, mais c'est cool! Les résultats parlent d'eux-mêmes

**Q: Script peut être modifié?**
A: Oui! `ORAL_SCRIPT_V2.md` est un modèle, adaptez-le

**Q: Où les slides?**
A: Repo root: `Puls-Events-RAG-Presentation-v2.pptx` (après génération)

---

**Ready? Let's Go! 🚀**
