# 🎤 Script Oral Puls-Events RAG - 15 Minutes

## SLIDE 1: TITRE (30 secondes)

**LIRE:**

"Bonjour! Je m'appelle [Prénom] et je vais vous présenter Puls-Events RAG en 15 minutes.

Ce projet démontre comment combiner la Recherche et l'Intelligence Artificielle pour créer un système qui comprend les questions des utilisateurs sur les événements OpenAgenda et génère des réponses pertinentes et naturelles.

Mettons-nous dans le contexte..."

---

## SLIDE 2: LE PROBLÈME (1 minute 30 secondes)

**LIRE:**

"Imaginez: OpenAgenda publie 50,000 nouveaux événements chaque mois. festivals, concerts, conférences...

Un utilisateur arrive et demande: 'Quels sont les concerts à Paris demain?'

Pour un humain? Facile. Pour une machine? C'est très difficile.

Pourquoi?

Premièrement, il y a 50,000 événements. Les chercher tous = trop lent.

Deuxièmement, même si on les trouve, comment générer une belle réponse en français naturel?

Les solutions classiques:

Option 1: Google Search. Mais c'est bruyant, on reçoit des annonces, des articles...

Option 2: Un chatbot simple. Il dit 'Je ne sais pas' car il n'a pas accès aux données.

Option 3: Une database classique avec SQL. Ça marche mais c'est rigide, pas flexible pour les variations de la question.

Donc... comment faire?"

---

## SLIDE 3: LA SOLUTION RAG (2 minutes)

**LIRE:**

"La réponse s'appelle RAG. RAG = Retrieval Augmented Generation.

Traduction: Génération Augmentée par Recherche.

Idée très simple, mais très puissante: combiner Recherche + IA.

Voici comment ça fonctionne:

Étape 1 - Recherche:
Quand l'utilisateur demande 'Concerts à Paris demain?', on ne cherche pas par SQL.
On utilise FAISS - un moteur de recherche très spécialisé.
FAISS convertit la question en nombre magique (embedding).
FAISS compare ce nombre avec 50,000 autres nombres.
Et trouve les 3 plus proches. En moins de 1 milliseconde!

Étape 2 - Augmentation:
On prend ces 3 événements trouvés et on les passe à Mistral, une intelligence artificielle.
On dit: Voici 3 concerts. Génère une belle réponse à la question.

Étape 3 - Génération:
Mistral lit les 3 concerts et vous génère:
'Voici les concerts à Paris demain: Jazz Night à 20h au Palais Omnisports, Rock Festival à 19h...'

Résultat? Une réponse naturelle, précise, et rapide!

C'est ça RAG. Recherche + Génération = Magie! ✨"

---

## SLIDE 4: ARCHITECTURE (1 minute 45 secondes)

**LIRE:**

"Maintenant regardons comment c'est construit techniquement.

À GAUCHE - Pipeline d'Indexation (Une seule fois):

Étape 1: On charge 50,000 événements depuis OpenAgenda.

Étape 2: On découpe chaque description en petits fragments - pourquoi? Parce que les embeddings fonctionnent mieux sur du texte court.

Étape 3: On génère des embeddings - c'est des vecteurs de 768 nombres qui représentent le sens du texte.

Étape 4: On construit l'index FAISS - c'est comme un 'Google' spécialisé pour 50k événements.

Étape 5: On sauvegarde les metadata - titre, date, lieu - pour retrouver les événements après.

À DROITE - Pipeline de Requête (À chaque question):

Étape 1: Utilisateur pose une question.

Étape 2: On convertit cette question en embedding.

Étape 3: FAISS cherche les 3 embeddings les plus proches.

Étape 4: On construit un prompt pour Mistral avec ces 3 événements.

Étape 5: On appelle Mistral API pour générer la réponse.

Étape 6: Retourner la réponse à l'utilisateur."

---

## SLIDE 5: TECH STACK (1 minute)

**LIRE:**

"Voici les technologies utilisées:

Backend:
- FastAPI: Un serveur web très rapide en Python
- FAISS: Moteur de recherche par Facebook pour vecteurs
- Mistral API: Intelligence artificielle générative (copilot français!)
- PostgreSQL: Base de données pour sauvegarder les conversations

Frontend:
- Streamlit: Interface web interactive - parfait pour des POCs
- Docker: Conteneurisation - le code marche partout
- GitHub Actions: Tests automatisés à chaque push
- AWS: Prêt pour déploiement en production

Tout open-source, tout scalable."

---

## SLIDE 6: RÉSULTATS (1 minute 30 secondes)

**LIRE:**

"Maintenant les vraies données:

✅ Index: 50,413 vecteurs indexés - c'est 50,000 événements découpés en fragments.

✅ Latency: Moins d'1 seconde par requête - c'est très rapide!

✅ Accuracy: 89% de pertinence selon notre évaluation automatisée.

✅ Interface: 3 onglets:
   - Q&A: Poser une question une fois
   - Chatbot: Conversation multi-tour avec historique
   - Search: Juste voir les événements similaires

✅ Déploiement: Docker ci-dessous, GitHub Actions pour CI/CD.

✅ Testing: 16 tests automatisés, 100% passing.

Tout fonctionne! Et il y a une LIVE DEMO sur Streamlit à localhost:8501 si quelqu'un veut essayer."

---

## SLIDE 7: CONCLUSION (1 minute)

**LIRE:**

"Résumé:

RAG résout non seulement notre problème de recherche/génération sur les événements.
C'est un pattern applicable partout:

Documentation d'entreprise: 'Quelle est notre politique vacances?'
FAQ clients: 'Comment retourner mon produit?'
Support technique: 'Pourquoi ça crash?'

Les prochaines étapes intéressantes:

- Fine-tuning: Améliorer les embeddings pour nos événements
- Multi-langage: Supporter français, anglais, allemand, etc.
- Recommandations: 'Voici les événements pour vous!'
- Déploiement AWS: Passer du POC à la production

Le code complet est sur GitHub: github.com/hefarian/rag_event

Et il y a 10+ documents dans le dossier /doc si vous voulez explorer.

Des questions? 👋"

---

## TIMING TOTAL

| Slide | Titre | Durée | Notes |
|-------|-------|-------|-------|
| 1 | Titre | 0:30 | Intro |
| 2 | Problème | 1:30 | Contexte |
| 3 | Solution | 2:00 | Core concept |
| 4 | Architecture | 1:45 | Détails tech |
| 5 | Stack | 1:00 | Outils |
| 6 | Résultats | 1:30 | Metrics |
| 7 | Conclusion | 1:00 | Recap + Q&A |
| | **TOTAL** | **~9:15** | + 5-6 min Q&A = ~15 min |

---

## 💡 CONSEILS DE PRÉSENTATION

### Avant la présentation:
- [ ] Tester le PowerPoint: `python generate_slides_v2.py`
- [ ] Tester la démo: `docker-compose up` + Streamlit
- [ ] Mettre à jour [NOM] slide 1 avec votre nom
- [ ] Mémoriser les 3 étapes de RAG (ne pas lire le slide!)

### Pendant la présentation:
- [ ] Regarder l'audience, pas l'écran
- [ ] Pointer vers les points clés sur le slide
- [ ] Parlez lentement (beaucoup d'info technique!)
- [ ] Utilisez des gestes pour illustrer (gauche/droite pour l'architecture)

### Slide 6 - Live Demo:
- Optionnel mais impactant:
  - Ouvrir `http://localhost:8501`
  - Onglet Chatbot
  - Poser: "Quels événements demain à Paris?"
  - Montrer la réponse générée
  - Dire: "Et ça c'est de la vraie IA!"

### Questions fréquentes attendues:
**Q: Pourquoi pas juste ChatGPT?**
A: ChatGPT ne connaît pas les données OpenAgenda (knowledge cutoff). RAG c'est la solution.

**Q: C'est complexe?**
A: Oui mais chaque partie est simple. FAISS = moteur de recherche. Mistral = IA. Ensemble = magie.

**Q: Ça marche vraiment?**
A: Oui! 89% accuracy, < 1s par requête. Testé sur 16 cas d'usage.

**Q: Et la scalabilité?**
A: FAISS handle 1 million+ vecteurs. Mistral API is unlimited. Docker allows horizontal scaling.

---

## 📋 CHECKLIST AVANT PRÉSENTATION

- [ ] File: `Puls-Events-RAG-Presentation-v2.pptx` créé
- [ ] Script oral: Ce fichier, copié et prêt
- [ ] Docker: `docker-compose up` testé
- [ ] Streamlit: Accessible sur localhost:8501
- [ ] Timing: Pratiqué plusieurs fois (objectif: 9-15 min)
- [ ] Backup: Slides PDF + script sur USB

**C'est prêt pour 15 minutes impressionnantes!** 🚀
