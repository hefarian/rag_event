"""Interface Streamlit pour le système RAG Puls-Events.

Permet aux utilisateurs de :
- Poser des questions via une interface intuitive
- Voir les résultats de recherche de similarité
- Reconstruire l'index FAISS
- Consulter la documentation de l'API

Lancer avec: streamlit run streamlit_app.py
S'attend à ce que l'API FastAPI soit accessible à http://api:8000
"""

import streamlit as st
import requests
import json
from datetime import datetime
from typing import Optional

# ============================================================================
# CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Puls-Events RAG",
    page_icon="🎭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# URL de l'API (défaut pour Docker: http://api:8000)
API_BASE_URL = "http://api:8000"

# Initialisation session state
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None
if "conversation_messages" not in st.session_state:
    st.session_state.conversation_messages = []

# ============================================================================
# STYLES CSS
# ============================================================================

st.markdown("""
<style>
    .main-title {
        text-align: center;
        color: #1f77b4;
        margin-bottom: 30px;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .source-item {
        background-color: #e8f4f8;
        padding: 15px;
        border-left: 4px solid #1f77b4;
        margin: 10px 0;
        border-radius: 5px;
        color: #1a1a1a !important;
        font-size: 14px;
    }
    .source-item strong {
        color: #0d47a1 !important;
    }
    .answer-box {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 5px;
        margin: 15px 0;
        color: #1a1a1a !important;
    }
    .answer-box h3, .answer-box h4, .answer-box h5 {
        color: #0d47a1 !important;
        margin-top: 10px;
        margin-bottom: 8px;
    }
    .answer-box ol, .answer-box ul {
        color: #1a1a1a !important;
        margin-left: 20px;
    }
    .warning-box {
        background-color: #fff2cc;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# UTILITAIRES (Fonctions helper pour communiquer avec l'API)
# ============================================================================
# Ces fonctions font le "glue" entre Streamlit (interface) et FastAPI (backend)
# Elles envoient des requêtes HTTP et gèrent les erreurs

@st.cache_resource
def get_session_state():
    """Initialise l'état de session.
    
    @st.cache_resource = Cache le résultat. Si on récharge la page,
    Streamlit ne recalcule pas cette fonction, elle retourne la valeur en cache.
    """
    return st.session_state

def check_api_health() -> bool:
    """Vérifie que l'API est accessible.
    
    POURQUOI?
    Avant de poser une question, s'assurer que le serveur FastAPI répond
    
    RETOUR:
    - True si API répond avec code 200
    - False si erreur connexion/timeout
    """
    try:
        # Envoyer une requête GET /health à l'API
        response = requests.get(f"{API_BASE_URL}/health", timeout=2)
        # Code 200 = OK
        return response.status_code == 200
    except Exception as e:
        st.error(f"⚠️ Erreur de connexion à l'API: {e}")
        return False

def ask_question(question: str, top_k: int = 3) -> Optional[dict]:
    """Envoie une question à l'API RAG et récupère la réponse.
    
    ÉTAPES:
    1. Prendre la question "Concerts à Paris?"
    2. Envoyer POST /ask à FastAPI
    3. API cherche dans FAISS + appelle Mistral
    4. Retourner la réponse {'answer': '...', 'sources': [...]}
    
    ARGS:
    - question: Texte de la question
    - top_k: Nombre de sources à retourner (défaut 3)
    
    RETOUR:
    - dict avec 'answer' et 'sources' si succès
    - None si erreur
    """
    try:
        # Préparer la requête HTTP
        response = requests.post(
            f"{API_BASE_URL}/ask",
            # Envoy json: {"question": "...", "top_k": 3}
            json={"question": question, "top_k": top_k},
            # Attendre max 30 secondes pour la réponse
            timeout=30
        )
        
        if response.status_code == 200:
            # Succès! Retourner la réponse JSON
            return response.json()
        else:
            # Erreur API (ex: 400 = question invalide, 500 = crash serveur)
            st.error(f"Erreur API: {response.status_code} - {response.text}")
            return None
    
    except requests.exceptions.Timeout:
        # Dépass de délai (> 30 sec) = requête trop longue
        st.error("⏱️ Délai d'attente dépassé. Veuillez réessayer.")
        return None
    except requests.exceptions.ConnectionError:
        # Impossible de se connecter = serveur pas démarré
        st.error("🔌 Impossible de se connecter à l'API. Vérifiez que le service est en cours d'exécution.")
        return None
    except Exception as e:
        st.error(f"❌ Erreur: {e}")
        return None

def search_documents(query: str, top_k: int = 5) -> Optional[list]:
    """Effectue une recherche de similarité simple.
    
    DIFFÉRENCE AVEC ask_question:
    - ask_question: /ask = Require FAISS + LLM (Mistral)
    - search_documents: /search = Juste FAISS (no LLM)
    
    USAGE:
    Quand on veut juste voir les événements similaires sans réponse textuelle
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/search",
            json={"question": query, "top_k": top_k},
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Erreur: {response.status_code}")
            return None
    
    except Exception as e:
        st.error(f"Erreur de recherche: {e}")
        return None

def clean_html(text: str) -> str:
    """Convertit les balises HTML en Markdown lisible pour Streamlit.
    
    POURQUOI?
    OpenAgenda retourne des descriptions en HTML:
    <p>Concert musical</p> → Pas beau dans Streamlit
    
    SOLUTION:
    Convertir en Markdown:
    <p>Concert musical</p> → Concert musical (plus beau!)
    """
    if not text:
        return ""
    # Remplacer les balises HTML par du Markdown équivalent
    text = text.replace("<h3>", "### ").replace("</h3>", "")
    text = text.replace("<h4>", "#### ").replace("</h4>", "")
    text = text.replace("<h5>", "##### ").replace("</h5>", "")
    text = text.replace("<strong>", "**").replace("</strong>", "**")
    text = text.replace("<b>", "**").replace("</b>", "**")
    text = text.replace("<i>", "*").replace("</i>", "*")
    text = text.replace("<br>", "\n").replace("<br/>", "\n")
    text = text.replace("<p>", "").replace("</p>", "")
    text = text.replace("<li>", "- ").replace("</li>", "")
    return text.strip()

def rebuild_index():
    """Lance la reconstruction de l'index FAISS via l'API.
    
    CÀ SERT À QUOI?
    - Charger les nouvelles données OpenAgenda
    - Recréer l'index FAISS depuis zéro
    - Utile si les données OpenAgenda changent
    
    ÉTAPES:
    1. Envoyer POST /rebuild à l'API
    2. API appelle scripts/build_index.py
    3. Index est recréé
    4. Retourner le statut
    """
    try:
        # Afficher un spinner pendant que l'index se reconstruit
        with st.spinner("📊 Lancement de la reconstruction..."):
            # Envoyer la requête, attendre max 10 secondes
            response = requests.post(f"{API_BASE_URL}/rebuild", timeout=10)
            
            if response.status_code == 200:
                # Succès!
                data = response.json()
                st.success(f"✅ {data.get('message', 'Reconstruction lancée')}")
                return True
            else:
                # Erreur (ex: 500 = index construction failed)
                st.error(f"Erreur: {response.status_code}")
                return False
    
    except Exception as e:
        st.error(f"Erreur: {e}")
        return False

# ============================================================================
# EN-TÊTE & NAVIGATION
# ============================================================================
# Afficher le titre et créer les onglets de navigation

st.markdown("<h1 class='main-title'>🎭 Puls-Events RAG Interface</h1>", unsafe_allow_html=True)

# Vérifier que l'API FastAPI est accessible
api_ok = check_api_health()
if api_ok:
    st.success("✅ API opérationnelle")
else:
    st.warning("⚠️ API non accessible - certaines fonctionnalités peuvent être indisponibles")

# Créer 5 onglets pour les différentes fonctionnalités
# Les utilisateurs peuvent cliquer sur chaque onglet pour changer de vue
tab_qna, tab_chatbot, tab_search, tab_admin, tab_docs = st.tabs(
    ["💬 Q&A RAG", "🤖 Chatbot Conversationnel", "🔍 Recherche", "⚙️ Administration", "📚 Documentation"]
)

# ============================================================================
# ONGLET 1 : Q&A RAG (Requêtes Une-off)
# ============================================================================
# Poser UNE question, obtenir UNE réponse (pas d'historique)

with tab_qna:
    st.header("Chat RAG - Posez vos questions")
    st.write("Posez une question sur les événements OpenAgenda et recevez une réponse générée par Mistral.")
    
    # Layout: 80% pour la question, 20% pour le bouton
    col1, col2 = st.columns([4, 1])
    
    with col1:
        # Input text pour poser la question
        question = st.text_input(
            "Question",
            placeholder="Ex: Quels concerts jazz à Paris cette semaine ?",
            label_visibility="collapsed"
        )
    
    with col2:
        top_k = st.slider("Top-K", 1, 10, 3, label_visibility="collapsed")
    
    if st.button("🚀 Poser la question", use_container_width=True, type="primary"):
        if question.strip():
            with st.spinner("⏳ Traitement de votre question..."):
                result = ask_question(question, top_k)
            
            if result:
                # Afficher la réponse générée avec nettoyage HTML
                st.subheader("✨ Réponse générée")
                answer = result.get("answer", "Pas de réponse")
                cleaned_answer = clean_html(answer)
                st.markdown(cleaned_answer)
                
                # Afficher les sources
                st.subheader("📋 Sources et contexte")
                sources = result.get("sources", [])
                
                if sources:
                    for i, source in enumerate(sources, 1):
                        score = source.get('score', 0)
                        metadata = source.get('metadata', {})
                        title = metadata.get('title', 'Sans titre')
                        date = metadata.get('date', 'Date inconnue')
                        location = metadata.get('location', 'Lieu inconnu')
                        content = source.get('content', 'Pas de contenu')
                        event_id = metadata.get('event_id', 'N/A')
                        
                        # Afficher chaque source avec styling
                        st.markdown(f"""
                        <div class='source-item'>
                            <strong>📌 Source {i}</strong> | Similarité: <strong>{score:.1%}</strong><br>
                            <strong>Événement:</strong> {title}<br>
                            <strong>Date:</strong> {date}<br>
                            <strong>Lieu:</strong> {location}<br>
                            <strong>Description:</strong> {content[:300]}...<br>
                            <em style='color: #555; font-size: 12px;'>ID Événement: {event_id}</em>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("ℹ️ Aucune source trouvée")
                
                # Afficher les métadonnées de la réponse
                col1, col2 = st.columns(2)
                with col1:
                    st.caption(f"⏰ Généré: {result.get('timestamp', 'N/A')}")
                with col2:
                    response_time = result.get('response_time_ms', 'N/A')
                    st.caption(f"⚡ Temps de réponse: {response_time}ms")
        else:
            st.warning("Veuillez entrer une question")

# ============================================================================
# ONGLET 2 : CHATBOT CONVERSATIONNEL
# ============================================================================

with tab_chatbot:
    st.header("🤖 Chatbot Conversationnel")
    st.write("Discutez avec l'assistant IA - il garde l'historique de votre conversation!")
    
    # Sidebar pour gestion des conversations
    with st.sidebar:
        st.subheader("💾 Gérer les conversations")
        
        # Récupérer / créer la conversation
        if "conversation_id" not in st.session_state:
            st.session_state.conversation_id = None
        
        # Option 1: Nouvelle conversation
        if st.button("➕ Nouvelle conversation"):
            try:
                response = requests.post(f"{API_BASE_URL}/chat/start", json={})
                if response.status_code == 200:
                    data = response.json()
                    st.session_state.conversation_id = data["conversation_id"]
                    st.session_state.conversation_messages = []
                    st.success(f"✓ Nouvelle conversation créée!")
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Erreur: {e}")
        
        # Option 2: Charger une conversation
        try:
            response = requests.get(f"{API_BASE_URL}/chat/list")
            if response.status_code == 200:
                conversations = response.json()["conversations"]
                
                if conversations:
                    st.write("**Conversations récentes:**")
                    for conv in conversations[:10]:
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            if st.button(f"{conv['id'][:6]}... ({conv['message_count']} msgs)", key=f"conv_{conv['id']}"):
                                st.session_state.conversation_id = conv["id"]
                                st.rerun()
                        with col2:
                            if st.button("❌", key=f"del_{conv['id']}", help="Supprimer"):
                                requests.delete(f"{API_BASE_URL}/chat/{conv['id']}")
                                st.rerun()
        except Exception as e:
            st.warning(f"Erreur chargement conversations: {e}")
    
    # Main chat interface
    if not st.session_state.conversation_id:
        st.info("👈 Créez ou chargez une conversation dans la sidebar pour commencer!")
    else:
        st.success(f"💬 Conversation: `{st.session_state.conversation_id}`")
        
        # Afficher l'historique
        try:
            response = requests.get(f"{API_BASE_URL}/chat/history/{st.session_state.conversation_id}")
            if response.status_code == 200:
                conversation = response.json()
                
                # Historique
                if conversation["messages"]:
                    st.subheader("📜 Historique")
                    for msg in conversation["messages"]:
                        if msg["role"] == "user":
                            st.chat_message("user").write(msg["content"])
                        else:
                            st.chat_message("assistant").write(msg["content"])
                else:
                    st.info("Aucun message encore. Commencez la conversation!")
        except Exception as e:
            st.error(f"Erreur chargement historique: {e}")
        
        # Form pour nouveau message
        st.markdown("---")
        col1, col2 = st.columns([4, 1])
        with col1:
            user_message = st.text_input("Votre message:", placeholder="Posez une question sur les événements...")
        with col2:
            send_button = st.button("📤 Envoyer", use_container_width=True)
        
        if send_button and user_message.strip():
            # Afficher le message utilisateur
            st.chat_message("user").write(user_message)
            
            # Appeler l'API
            try:
                with st.spinner("⏳ Assistant réfléchit..."):
                    response = requests.post(
                        f"{API_BASE_URL}/chat/message",
                        json={
                            "conversation_id": st.session_state.conversation_id,
                            "message": user_message
                        },
                        timeout=30
                    )
                
                if response.status_code == 200:
                    data = response.json()
                    st.chat_message("assistant").write(data["assistant_response"])
                    st.success(f"✓ Message #{data['messages_count']}")
                    st.rerun()
                else:
                    st.error(f"❌ Erreur API: {response.status_code}")
            except Exception as e:
                st.error(f"❌ Erreur: {e}")


# ============================================================================
# ONGLET 3 : RECHERCHE
# ============================================================================

with tab_search:
    st.header("🔍 Recherche de similarité")
    st.write("Recherchez des documents similaires sans génération.")
    
    col1, col2 = st.columns([4, 1])
    
    with col1:
        search_query = st.text_input(
            "Requête de recherche",
            placeholder="Entrez votre requête...",
            label_visibility="collapsed"
        )
    
    with col2:
        search_top_k = st.slider("Résultats", 1, 20, 5, label_visibility="collapsed")
    
    if st.button("🔎 Rechercher", use_container_width=True):
        if search_query.strip():
            with st.spinner("Recherche en cours..."):
                results = search_documents(search_query, search_top_k)
            
            if results:
                st.success(f"✅ {len(results)} résultat(s) trouvé(s)")
                
                for i, result in enumerate(results, 1):
                    score = result.get("score", 0)
                    progress = score if 0 <= score <= 1 else score / 100
                    
                    with st.expander(f"Résultat {i} (score: {score:.2%})"):
                        st.write(result.get("content", "Pas de contenu"))
                        st.json(result.get("metadata", {}))
                        st.progress(progress)
            else:
                st.warning("Aucun résultat trouvé")
        else:
            st.warning("Veuillez entrer une requête")

# ============================================================================
# ONGLET 4 : ADMINISTRATION
# ============================================================================

with tab_admin:
    st.header("⚙️ Administration")
    
    # Section Reconstruction
    st.subheader("🔄 Reconstruction de l'index")
    st.write("""
    L'index FAISS contient les vecteurs d'embeddings des événements OpenAgenda.
    Reconstruisez-le si vous avez ajouté ou modifié des données source.
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Reconstruire l'index", use_container_width=True, type="secondary"):
            rebuild_index()
    
    with col2:
        if st.button("📞 Vérifier l'état", use_container_width=True):
            try:
                response = requests.get(f"{API_BASE_URL}/")
                if response.status_code == 200:
                    status = response.json()
                    st.json(status)
                else:
                    st.error(f"Erreur: {response.status_code}")
            except Exception as e:
                st.error(f"Erreur: {e}")
    
    # Section Configuration
    st.subheader("⚙️ Configuration")
    
    with st.form("config_form"):
        api_url = st.text_input("URL de l'API", value=API_BASE_URL)
        timeout = st.slider("Délai d'attente (s)", 1, 60, 30)
        
        submitted = st.form_submit_button("✅ Appliquer", use_container_width=True)
        
        if submitted:
            st.info(f"Configuration mise à jour: API={api_url}, Timeout={timeout}s")

# ============================================================================
# ONGLET 5 : DOCUMENTATION
# ============================================================================

with tab_docs:
    st.header("📚 Documentation API")
    
    st.write("""
    ## 🎯 Endpoints disponibles
    
    L'API expose 10 endpoints pour gérer les requêtes RAG et les conversations.
    
    ---
    
    ### 🏗️ Endpoints d'état
    
    #### 1. **GET /**
    Endpoint racine - retourne le statut global de l'API.
    
    **Réponse:**
    ```json
    {
        "status": "operational",
        "index_exists": true,
        "message": "API Puls-Events RAG opérationnelle"
    }
    ```
    
    #### 2. **GET /health**
    Vérification de l'état de santé (health check) pour les conteneurs.
    
    **Usage:** Déploiement Docker/Kubernetes
    
    **Réponse:**
    ```json
    {
        "status": "healthy",
        "index_exists": true,
        "message": "✓ API en bonne santé"
    }
    ```
    
    ---
    
    ### 🔍 Endpoints RAG (Requête unique)
    
    #### 3. **POST /ask**
    Poser une question au système RAG - obtient une réponse générée par Mistral avec sources.
    
    **Body:**
    ```json
    {
        "question": "Quels concerts jazz à Paris cette semaine ?",
        "top_k": 3
    }
    ```
    
    **Réponse:**
    ```json
    {
        "question": "...",
        "answer": "Voici les événements trouvés...",
        "sources": [
            {
                "content": "...",
                "metadata": {
                    "title": "...",
                    "date": "...",
                    "location": "..."
                }
            }
        ],
        "timestamp": "2026-04-12T10:30:00"
    }
    ```
    
    **Paramètres:**
    - `question` (str): Question sur les événements
    - `top_k` (int): Nombre de sources à retourner (défaut: 3)
    
    #### 4. **POST /search**
    Recherche de similarité pure dans l'index FAISS (sans génération LLM).
    
    **Body:**
    ```json
    {
        "question": "Concerts jazz",
        "top_k": 5
    }
    ```
    
    **Réponse:** Liste de documents similaires avec scores.
    
    **Utilisation:** Pour explorer l'index sans appel à Mistral.
    
    ---
    
    ### 🔄 Endpoints d'administration
    
    #### 5. **POST /rebuild**
    Lance la reconstruction asynchrone de l'index FAISS.
    
    **Note:** Fonctionne en arrière-plan (non-bloquant).
    
    **Réponse:**
    ```json
    {
        "status": "queued",
        "index_exists": false,
        "message": "Reconstruction de l'index en cours (background)..."
    }
    ```
    
    **Quand l'utiliser:**
    - Après l'ajout de nouvelles données OpenAgenda
    - Pour actualiser les vecteurs
    
    ---
    
    ### 💬 Endpoints Chatbot (Conversationnel)
    
    #### 6. **POST /chat/start**
    Démarre une nouvelle conversation (avec historique).
    
    **Body:**
    ```json
    {
        "initial_message": "Coucou !"
    }
    ```
    
    **Réponse:**
    ```json
    {
        "conversation_id": "conv_xyz123",
        "created_at": "2026-04-12T10:30:00",
        "message": "Conversation créée (ID: conv_xyz123)..."
    }
    ```
    
    **Retourne:** Un `conversation_id` à utiliser pour les messages suivants.
    
    #### 7. **POST /chat/message**
    Envoie un message dans une conversation existante.
    
    **Body:**
    ```json
    {
        "conversation_id": "conv_xyz123",
        "message": "Quels spectacles ce weekend ?"
    }
    ```
    
    **Réponse:**
    ```json
    {
        "conversation_id": "conv_xyz123",
        "user_message": "Quels spectacles ce weekend ?",
        "assistant_response": "Voici les spectacles...",
        "timestamp": "2026-04-12T10:35:00",
        "messages_count": 4
    }
    ```
    
    **À savoir:**
    - L'API maintient l'historique des messages
    - Mistral reçoit le contexte des messages précédents
    - Les événements FAISS sont trouvés pour chaque message
    
    #### 8. **GET /chat/history/{conversation_id}**
    Récupère l'historique complet d'une conversation.
    
    **Exemple:**
    ```bash
    GET /chat/history/conv_xyz123
    ```
    
    **Réponse:**
    ```json
    {
        "conversation_id": "conv_xyz123",
        "created_at": "2026-04-12T10:30:00",
        "messages": [
            {"role": "user", "content": "Coucou !", "timestamp": "..."},
            {"role": "assistant", "content": "Bonjour!", "timestamp": "..."}
        ]
    }
    ```
    
    #### 9. **GET /chat/list**
    Liste toutes les conversations en cours.
    
    **Réponse:**
    ```json
    {
        "conversations": [
            {"conversation_id": "conv_xyz123", "created_at": "...", "message_count": 4},
            {"conversation_id": "conv_abc456", "created_at": "...", "message_count": 2}
        ],
        "total": 2
    }
    ```
    
    #### 10. **DELETE /chat/{conversation_id}**
    Supprime une conversation et son historique.
    
    **Exemple:**
    ```bash
    DELETE /chat/conv_xyz123
    ```
    
    **Réponse:**
    ```json
    {
        "message": "Conversation supprimée"
    }
    ```
    
    ---
    
    ### 📖 Documentation interactive
    
    Pour explorer l'API en détail avec Swagger UI:
    """)
    
    st.subheader("🔗 Liens utiles")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📖 Swagger UI", use_container_width=True):
            st.info(f"[Ouvrir Swagger]({API_BASE_URL}/docs)")
    
    with col2:
        if st.button("📘 ReDoc", use_container_width=True):
            st.info(f"[Ouvrir ReDoc]({API_BASE_URL}/redoc)")
    
    with col3:
        if st.button("🏠 API Root", use_container_width=True):
            try:
                response = requests.get(f"{API_BASE_URL}/")
                st.json(response.json())
            except Exception as e:
                st.error(f"Erreur: {e}")
    
    st.divider()
    
    st.subheader("📊 Résumé des endpoints")
    
    endpoints_summary = """
    | Endpoint | Méthode | Usage | Bloquant |
    |----------|---------|-------|----------|
    | `/` | GET | État API | ✓ |
    | `/health` | GET | Health check | ✓ |
    | `/ask` | POST | RAG (requête unique) | ✓ |
    | `/search` | POST | Recherche FAISS pure | ✓ |
    | `/rebuild` | POST | Reconstruire index | ✗ (async) |
    | `/chat/start` | POST | Démarrer conversation | ✓ |
    | `/chat/message` | POST | Envoyer message | ✓ |
    | `/chat/history/{id}` | GET | Historique conversation | ✓ |
    | `/chat/list` | GET | Lister conversations | ✓ |
    | `/chat/{id}` | DELETE | Supprimer conversation | ✓ |
    """
    
    st.markdown(endpoints_summary)

# ============================================================================
# PIED DE PAGE
# ============================================================================

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.caption(f"API URL: {API_BASE_URL}")

with col2:
    st.caption(f"Version: 1.0.0")

with col3:
    st.caption(f"Dernière mise à jour: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: gray;'>Puls-Events RAG POC © 2025</p>",
    unsafe_allow_html=True
)
