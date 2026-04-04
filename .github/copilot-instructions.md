# Instructions pour les agents IA (Puls-Events — POC RAG)

But : fournir aux agents IA les informations essentielles pour être immédiatement productifs sur ce dépôt POC RAG (OpenAgenda → FAISS → LangChain → Mistral).

**1. Vue d'ensemble :**
- **Architecture :** ingestion OpenAgenda → nettoyage & chunking (`scripts/`) → vectorisation (Mistral embeddings) → index FAISS (`vectors/`) → orchestration LangChain → génération Mistral via API (`api/`).
- **Flux de données :** événements bruts → DataFrame nettoyé (`data/events.parquet` ou `data/events.json`) → chunks texte + métadonnées → vecteurs + metadata → index FAISS + fichier metadata.

**2. Fichiers/chemins clés (attendus)**
- `README.md` : instructions de reproduction et commandes.
- `requirements.txt` : dépendances reproduisibles.
- `scripts/build_index.py` : script permettant de reconstruire l'index FAISS à partir des données OpenAgenda.
- `scripts/fetch_openagenda.py` : récupération et filtrage (ville, période 1 an).
- `api/app.py` ou `api/main.py` : FastAPI exposant les endpoints `/ask` (POST) et `/rebuild` (POST/GET).
- `vectors/` : stockage de l'index FAISS (`index.faiss`) et `metadata.jsonl`.
- `tests/` : tests unitaires (`test_indexing.py`, `test_api.py`, `evaluate_rag.py`).
- `Dockerfile` : image pour la démo locale.

**3. Environnement & vérifications rapides**
- Utiliser Python ≥ 3.8, virtualenv/venv ou conda. Préférer `faiss-cpu` pour portabilité.
- Commandes d'installation (exemple) :
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```
- Tests d'import rapides (doit réussir) :
```
python -c "import faiss; from langchain.vectorstores import FAISS; from langchain.embeddings import HuggingFaceEmbeddings; from mistral import MistralClient; print('ok')"
```

**4. Variables d'environnement**
- Nommez les clés : `MISTRAL_API_KEY`, `OPENAGENDA_API_KEY`.
- Ne jamais commit de `.env` contenant des clés ; préférez `.env.example`.

**5. Comportements attendus pour les contributions**
- Tests : ajouter/mettre à jour tests dans `tests/` pour toute modification du flux d'indexation ou des endpoints API.
- Index : `scripts/build_index.py` doit être idempotent et écrire `vectors/index.faiss` + `vectors/metadata.jsonl`.
- API : séparer la logique RAG (classe/objet réutilisable) du wrapper FastAPI. Endpoints minimum :
  - `POST /ask` {"question": "..."} → réponse textuelle augmentée
  - `POST /rebuild` -> déclenche `scripts/build_index.py` (protéger en production)

**6. Patterns et conventions spécifiques au projet**
- Chunking : découper descriptions en ~200–500 tokens et conserver `event_id`, `date`, `location` en metadata.
- Stocker metadata au format JSONL parallèle à l'index FAISS (permet récupération rapide des champs).
- Utiliser LangChain pour : 1) rechercher nearest-neighbors dans FAISS, 2) construire le prompt avec fragments, 3) appeler Mistral pour la génération.
- Logique d'assemblage du prompt : inclure uniquement N top-k passages (ex. 3–5), puis poser la question utilisateur + consignes de concision et factuel.

**7. Tests & évaluation**
- Fournir un jeu de tests annotés `tests/annotated_questions.jsonl` (question, reference_answer).
- Automatiser l'évaluation avec `evaluate_rag.py` (ex : Ragas ou calcul de similarité/token-match). Intégrer dans CI si présent.

**8. Docker & démo locale**
- `Dockerfile` doit exposer l'API et inclure un chemin pour charger `vectors/index.faiss` au démarrage.
- Commandes de démo locales (exemple) :
```
docker build -t puls-events-poc .
docker run -p 8000:8000 --env-file .env puls-events-poc
# puis tester : curl -X POST http://localhost:8000/ask -d '{"question":"Quels concerts jazz à Paris cette semaine ?"}'
```

**9. Ce qu'il faut éviter**
- Ne pas reconstruire l'index FAISS à chaque requête `/ask`.
- Ne pas commit de clés/API ni d'index volumineux (`vectors/` devrait être ignoré ou géré via release storage).

**10. Si tu es un agent IA et tu as un doute**
- Cherche d'abord dans `README.md`, `requirements.txt`, `scripts/`, `api/`, `tests/`.
- Si un fichier attendu manque, propose une implémentation minimale (ex : `scripts/build_index.py` stub) et demande validation.

---
Si des sections spécifiques sont manquantes ou si tu veux que j'intègre le contenu d'un fichier existant, dis-moi lesquels — je fusionnerai et itérerai.
