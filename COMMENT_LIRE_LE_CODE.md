# 📖 Guide de Lecture du Code - Pour Débutants

Ce guide aide à comprendre l'architecture du projet **Puls-Events RAG**.

## 🎯 Vue d'Ensemble
**RAG = Retrieval Augmented Generation** (Génération Augmentée par Récupération)

Flux simplifié:
```
1. Événements OpenAgenda (JSON)
   ↓
2. Nettoyage + Découpage en fragments (chunks)
   ↓
3. Vectorisation (conversion en nombres)
   ↓
4. Index FAISS (recherche rapide)
   ↓
5. Requête utilisateur → Recherche dans FAISS → Mistral (IA)
   ↓
6. Réponse augmentée avec des événements réels
```

## 📁 Structure des Fichiers

### 🔧 Racine
- **init_index.py** : Initialisation rapide de l'index
- **streamlit_app.py** : Interface web (UI)

### 💻 API (api/)
- **app.py** : Serveur FastAPI avec endpoints
- **conversation_storage.py** : Sauvegarde des conversations en JSON  
- **mistral_wrapper.py** : Appel à l'API Mistral (IA générative)

### ⚙️ Scripts (scripts/)
- **build_index.py** : Crée l'index FAISS à partir des événements
- **clean_index_robust.py** : Nettoie les événements passés

### 🧪 Tests (tests/)
- **test_api.py** : Teste les endpoints FastAPI
- **test_indexing.py** : Teste la création d'index
- **test_rag_complete.py** : Teste le pipeline RAG complet

## 🔑 Concepts Clés

### 1. Événements (Events)
```json
{
  "title": "Concert Jazz",
  "date": "2026-04-15",
  "location": "Paris",
  "description": "Un concert de musique jazz..."
}
```

### 2. Chunks (Fragments de texte)
```
Texte original: "Concert Jazz à Paris le 15 avril - Un événement musical..."
Chunk 1: "Concert Jazz à Paris le 15 avril - Un"
Chunk 2: "Un événement musical..."
```
Pourquoi? FAISS recherche mieux sur des petites portions.

### 3. Embeddings (Vecteurs)
```
"Concert" → [0.12, -0.45, 0.89, ...]  (liste de nombres)
"Musique" → [0.10, -0.42, 0.87, ...]
```
Les vecteurs similaires sont proches en distance mathématique.

### 4. FAISS (Index de recherche)
```
Index FAISS = Base de données vectorielle ultra-rapide
Permet chercher les 5 événements les plus similaires en < 1ms
```

### 5. Mistral (IA générative)
```
Mistral = Modèle IA qui génère du texte
Reçoit: "Quels concerts à Paris?" + événements trouvés par FAISS
Retourne: "Voici les concerts recommandés: ..."
```

## 🚀 Flux Complet (du point de vue utilisateur)

**Étape 1: Démarrage**
```bash
cd PROJET09
docker-compose up
# API sur http://localhost:8000
# UI sur http://localhost:8501
```

**Étape 2: Indexation (une seule fois)**
```bash
python scripts/build_index.py
# Crée: vectors/index.faiss + vectors/metadata.jsonl
```

**Étape 3: Requête utilisateur (endpoint /ask)**
```
Utilisateur: "Quels concerts jazz?"
   ↓
1. Vectoriser la question → [0.11, -0.46, ...]
2. Chercher dans FAISS → Trouver les 5 plus proches
3. Récupérer détails via metadata.jsonl
4. Envoyer à Mistral: "Voici les événements: [...]. Réponds à: Quels concerts jazz?"
5. Mistral génère réponse naturelle
   ↓
Réponse: "J'ai trouvé 2 concerts jazz à Paris le 15 avril..."
```

## 📊 Fichiers de Données

### Entrée (DATAIN/)
- `evenements-publics-openagenda.json` : Les 50,000+ événements bruts

### Sortie (vectors/)
- `index.faiss` : Index de recherche binaire (391 MB)
- `metadata.jsonl` : Info des événements ligne par ligne (JSON Lines format)

## 🔄 Cycle de Développement

```
Code modifié
   ↓
   `git push origin dev`
   ↓
GitHub CI lance automatiquement:
   • Vérification syntaxe Python
   • Tests avec pytest
   • Linting (style de code)
   ↓
Si ✅ tous les tests passent → Merge ensuite possible
```

## 📝 Comment Lire le Code

### Pour Comprendre l'Initialisation
1. Lire: `scripts/build_index.py` → C'est le point d'entrée
2. Lire: `api/app.py` → C'est le serveur

### Pour Comprendre une Requête RAG
1. Chercher l'endpoint `/ask` dans `api/app.py`
2. Voir comment `search_in_faiss()` est appelée
3. Voir comment `call_mistral()` génère la réponse

### Pour Déboguer
1. Vérifier les logs: `docker logs puls-events-api`
2. Tester un endpoint: Utiliser Streamlit UI ou curl
3. Ajouter des prints/logs dans le code

## 🎓 Commandes Utiles

```bash
# Voir les logs API en temps réel
docker logs -f puls-events-api

# Tester un endpoint
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "concerts à Paris?"}'

# Reconstruire l'index
curl -X POST http://localhost:8000/rebuild

# Arrêter tout
docker-compose down
```

---

**Prochain pas**: Ouvrir `api/app.py` et suivre l'endpoint `/ask` étape par étape! 🚀
