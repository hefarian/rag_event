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
# UTILITAIRES
# ============================================================================

@st.cache_resource
def get_session_state():
    """Initialise l'état de session."""
    return st.session_state

def check_api_health() -> bool:
    """Vérifie que l'API est accessible."""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=2)
        return response.status_code == 200
    except Exception as e:
        st.error(f"⚠️ Erreur de connexion à l'API: {e}")
        return False

def ask_question(question: str, top_k: int = 3) -> Optional[dict]:
    """Envoie une question à l'API RAG."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/ask",
            json={"question": question, "top_k": top_k},
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Erreur API: {response.status_code} - {response.text}")
            return None
    
    except requests.exceptions.Timeout:
        st.error("⏱️ Délai d'attente dépassé. Veuillez réessayer.")
        return None
    except requests.exceptions.ConnectionError:
        st.error("🔌 Impossible de se connecter à l'API. Vérifiez que le service est en cours d'exécution.")
        return None
    except Exception as e:
        st.error(f"❌ Erreur: {e}")
        return None

def search_documents(query: str, top_k: int = 5) -> Optional[list]:
    """Effectue une recherche de similarité."""
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
    """Convertit les balises HTML en Markdown lisible pour Streamlit."""
    if not text:
        return ""
    # Remplacer les balises HTML par du Markdown
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
    """Lance la reconstruction de l'index FAISS."""
    try:
        with st.spinner("📊 Lancement de la reconstruction..."):
            response = requests.post(f"{API_BASE_URL}/rebuild", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                st.success(f"✅ {data.get('message', 'Reconstruction lancée')}")
                return True
            else:
                st.error(f"Erreur: {response.status_code}")
                return False
    
    except Exception as e:
        st.error(f"Erreur: {e}")
        return False

# ============================================================================
# EN-TÊTE & NAVIGATION
# ============================================================================

st.markdown("<h1 class='main-title'>🎭 Puls-Events RAG Interface</h1>", unsafe_allow_html=True)

# Vérifier la connexion à l'API
api_ok = check_api_health()
if api_ok:
    st.success("✅ API opérationnelle")
else:
    st.warning("⚠️ API non accessible - certaines fonctionnalités peuvent être indisponibles")

# Barre de navigation
tab_chat, tab_search, tab_admin, tab_docs = st.tabs(
    ["💬 Chat RAG", "🔍 Recherche", "⚙️ Administration", "📚 Documentation"]
)

# ============================================================================
# ONGLET 1 : CHAT RAG
# ============================================================================

with tab_chat:
    st.header("Chat RAG - Posez vos questions")
    st.write("Posez une question sur les événements OpenAgenda et recevez une réponse générée par Mistral.")
    
    col1, col2 = st.columns([4, 1])
    
    with col1:
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
# ONGLET 2 : RECHERCHE
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
# ONGLET 3 : ADMINISTRATION
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
# ONGLET 4 : DOCUMENTATION
# ============================================================================

with tab_docs:
    st.header("📚 Documentation API")
    
    st.write("""
    ## Endpoints disponibles
    
    ### 1. **GET /health**
    Vérifie l'état de santé de l'API.
    
    ```bash
    curl http://api:8000/health
    ```
    
    ### 2. **POST /ask**
    Poser une question au système RAG.
    
    ```json
    {
        "question": "Quels sont les événements à Paris ?",
        "top_k": 3
    }
    ```
    
    ### 3. **POST /search**
    Recherche de similarité sur l'index FAISS.
    
    ```json
    {
        "question": "Concerts jazz",
        "top_k": 5
    }
    ```
    
    ### 4. **POST /rebuild**
    Lance la reconstruction asynchrone de l'index.
    
    ```bash
    curl -X POST http://api:8000/rebuild
    ```
    
    ### 5. **GET /docs**
    Accédez à la documentation Swagger interactive.
    
    ```
    http://api:8000/docs
    ```
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
