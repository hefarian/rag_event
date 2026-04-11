# 📊 Présentation Puls-Events RAG - 15 Minutes

Guide complet pour préparer et faire la présentation professionnelle du projet Puls-Events RAG.

## 📁 Fichiers Fournis

### 1. `generate_slides_v2.py`
**Script Python** pour générer les slides PowerPoint automatiquement.

```bash
# Installation (une seule fois)
pip install python-pptx

# Générer les slides
python generate_slides_v2.py

# Output: Puls-Events-RAG-Presentation-v2.pptx
```

**Contient:**
- 7 slides professionnels
- Couleurs et typo cohérentes
- Contenu pré-remplissage
- Prêt pour présentation

### 2. `ORAL_SCRIPT_V2.md`
**Script à lire** pendant la présentation - une par slide.

**Utilisation:**
- Lire sur un moniteur secondaire
- Ou imprimer sur papier
- Chaque section = durée approximative
- Total: ~9 minutes + 5-6 min Q&A = 15 min

---

## ⏱️ Structure de la Présentation

| # | Slide | Durée | Points Clés |
|---|-------|-------|------------|
| 1 | **Titre** | 0:30 | Intro + contexte |
| 2 | **Problème** | 1:30 | 50k événements = complexe |
| 3 | **Solution RAG** | 2:00 | Recherche + IA = magie |
| 4 | **Architecture** | 1:45 | Pipeline indexation & requête |
| 5 | **Tech Stack** | 1:00 | Backend (FastAPI, FAISS, Mistral) + Frontend (Streamlit) |
| 6 | **Résultats** | 1:30 | Metrics: 50k vecteurs, <1s, 89% accuracy |
| 7 | **Conclusion** | 1:00 | Cases, prochaines étapes, Q&A |
| | **TOTAL** | **~9:15** | + 5-6 min Q&A |

---

## 🚀 Avant la Présentation

### Jour 1-2: Préparation
```bash
# 1. Générer les slides
python generate_slides_v2.py
# Vérifier: Puls-Events-RAG-Presentation-v2.pptx créé

# 2. Lire le script oral
cat ORAL_SCRIPT_V2.md

# 3. Pratiquer le timing
# - Lire chaque section en parlant lentement
# - Objectif: 9 minutes sans démo, 15 avec Q&A
```

### Jour de la Présentation
```bash
# 1. Démarrer les services
docker-compose up &

# 2. Vérifier Streamlit
# http://localhost:8501 → Chatbot tab

# 3. Ouvrir PowerPoint
# Ouvrir: Puls-Events-RAG-Presentation-v2.pptx

# 4. Préparer le script
# Sur un moniteur secondaire ou imprimé

# 5. Test technique
# - Micro/Audio OK?
# - Projecteur connecté?
# - WiFi stable? (pour démo Streamlit)
```

---

## 💡 Guide de Présentation

### Avant chaque slide
- [ ] Lire le script correspondant dans ORAL_SCRIPT_V2.md
- [ ] Mémoriser les 3-4 points clés (ne pas lire le slide!)
- [ ] Regarder l'audience, pas l'écran

### Points clés par slide

**Slide 1 - Titre:**
- Sourire, établir le contact
- Dire: "Puls-Events RAG en 15 minutes"
- Créer de la curiosité

**Slide 2 - Problème:**
- Gesticuler: "Imaginez 50,000 événements..."
- Faire une pause avant: "Comment faire?"
- Maintenir le suspense

**Slide 3 - Solution:**
- C'est le CŒUR! Parler lentement
- Pointer: "Étape 1, Étape 2, Étape 3"
- Dire: "C'est simple mais puissant!"

**Slide 4 - Architecture:**
- Pointer colonne gauche: "Pipeline d'indexation - une seule fois"
- Pointer colonne droite: "Pipeline de requête - à chaque question"
- Dire: "Déconnecté mais synchronisé"

**Slide 5 - Tech Stack:**
- Brièvement: "FastAPI, FAISS, Mistral..."
- Dire: "Tout open-source, tout scalable"
- Ne pas s'attarder

**Slide 6 - Résultats:**
- Montrer les chiffres: "50k vecteurs, <1s, 89% accuracy"
- **[OPTIONNEL] LIVE DEMO:**
  - Ouvrir http://localhost:8501
  - Onglet "Chatbot"
  - Poser: "Quels événements demain à Paris?"
  - Attendre la réponse
  - Dire: "Et ça c'est de la VRAIE IA!"
  - Ça prend 30-45 secondes
  
- Si problème: "Pas internet? Pas grave, les tests passent 100%!"

**Slide 7 - Conclusion:**
- Récapituler: "RAG = Recherche + Génération"
- Dire: "Cases d'usage: Documentation, FAQ, Support..."
- Inviter questions: "Des questions? Je suis prêt!"

---

## 📺 LIVE DEMO (Optionnel mais IMPACTANT)

Ajoutez 30-45 secondes sur Slide 6 pour montrer le chatbot en action.

### Avant
```bash
# Préparer dans une autre fenêtre
cd /path/to/PROJET09
docker-compose up

# Attendre que tout démarre (~30 sec)
```

### Pendant la présentation (Slide 6)
```
"Vous voulez voir ça en action? Voilà!"
[Ouvrir http://localhost:8501]
[Aller à l'onglet "Chatbot"]
[Poser une question: "Quels événements demain à Paris?"]
[Attendre ~2 sec]
[La réponse s'affiche avec événements réels!]

"Voilà! Recherche + Génération = Réponse pertinente en français naturel."
```

### Plan B (si Internet/Docker crash)
```
"Pas internet en ce moment, mais tous les tests passent 100%.
Vous pouvez voir la démo après sur github.com/hefarian/rag_event"
```

---

## ❓ Questions Attendues

**Q: Pourquoi pas ChatGPT?**
```
A: ChatGPT n'a pas les données OpenAgenda (knowledge cutoff avril 2024).
   RAG résout ça: données fraîches + IA générative.
```

**Q: C'est compliqué?**
```
A: Oui! Mais chaque partie est simple:
   - FAISS: moteur de recherche
   - Mistral: IA générative
   - Ensemble: résultat impressionnant
```

**Q: Performance?**
```
A: <1 seconde par requête. 50k vecteurs indexés.
   89% accuracy selon notre évaluation.
```

**Q: Scalabilité?**
```
A: FAISS supporte 1 million+ vecteurs.
   Mistral API illimitée.
   Docker pour horizontal scaling.
```

**Q: Coût?**
```
A: FAISS et Streamlit: GRATUIT
   Mistral API: ~$0.15 par 1M tokens (très pas cher)
   Total: ~$50/mois à production scale
```

**Q: Où le code?**
```
A: github.com/hefarian/rag_event
   - 9 fichiers Python
   - 20+ tests
   - Docker ready
   - 10+ documents dans /doc
```

---

## 📝 Fiche Personnelle

À personnaliser avant présentation:

```markdown
**Votre Nom:** ____________________
**Date présentation:** ____________________
**Audience:** ____________________
**Durée réelle (après pratique):** ____________________

**Timing pratique:**
- Slide 1: __:__ (target 0:30)
- Slide 2: __:__ (target 1:30)
- Slide 3: __:__ (target 2:00)
- Slide 4: __:__ (target 1:45)
- Slide 5: __:__ (target 1:00)
- Slide 6: __:__ (target 1:30 ou +0:45 avec demo)
- Slide 7: __:__ (target 1:00)
**Total:** __:__ (target 9-15 min)

**Points personnels à ajouter:**
- [ ] Pourquoi ce projet?
- [ ] Personal win?
- [ ] Prochaines étapes?
```

---

## 📦 Fichiers Complémentaires

Dans le repo:
- `COMMENT_LIRE_LE_CODE.md` - Architecture globale
- `GUIDE_FICHIERS_DETAILLE.md` - Code détaillé
- `GUIDE_TESTS.md` - Tests et debugging
- `doc/ARCHITECTURE_DETAILLEE.md` - Diagrammes UML

[Tous disponibles pour approfondir après la présentation]

---

## ✅ Checklist Finale

Avant présentation:
- [ ] `generate_slides_v2.py` exécuté
- [ ] `Puls-Events-RAG-Presentation-v2.pptx` créé
- [ ] `ORAL_SCRIPT_V2.md` lu et mémorisé
- [ ] Timing pratiqué (9-15 minutes)
- [ ] Docker testé (`docker-compose up`)
- [ ] Streamlit accessible (`localhost:8501`)
- [ ] Micro/Audio testé
- [ ] Projecteur testé
- [ ] WiFi testé
- [ ] Slides PDF en backup sur USB
- [ ] Confiance + Énergie ✨

---

## 🎬 C'est Parti!

Vous avez tout ce qu'il faut pour faire une présentation professionnelle et impressionnante! 

**Durée:** 15 minutes ✅
**Content:** 7 slides couvrant problème → solution → résultats ✅
**Script:** Oral complet à lire × 2 (une fois, puis les slides) ✅
**Demo:** Optionnel mais impactant ✅

Prêt pour faire du bruit! 🚀
