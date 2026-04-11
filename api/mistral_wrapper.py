"""Wrapper simple pour l'API Mistral via HTTP requests.

POURQUOI UN WRAPPER?
- Mistral a un SDK officiel (mistral-sdk) mais c'est lourd
- Notre wrapper = juste requests + parsing JSON = plus léger
- Plus facile à maintenir dans un POC

COMMENT MISTRAL FONCTIONNE?
1. On envoie un message à https://api.mistral.ai/
2. Mistral lit le message + historique
3. Mistral génère une réponse
4. On reçoit la réponse JSON
"""
import os
import requests
import logging
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

def call_mistral(user_message: str, system_message: str = "", messages_history: List[Dict] = None) -> Optional[str]:
    """
    Appelle l'API Mistral directement via HTTP requests (pas de SDK).
    
    FLUX:
    user_message = "Quels sont ces 3 concerts?"
        ↓
    Construire payload JSON
        ↓
    POST https://api.mistral.ai/ avec clé API
        ↓
    Parser réponse JSON
        ↓
    Retourner le texte généré
    
    Args:
        user_message: Le message utilisateur à traiter ("Quels concerts?")
        system_message: Instructions système optionnelles ("Tu es un assistant...")
        messages_history: Historique complet pour chatbot multi-tour
                         Format: [{"role": "user", "content": "..."}, 
                                 {"role": "assistant", "content": "..."}, ...]
        
    Returns:
        Texte généré par Mistral, ou None si erreur
        
    EXEMPLE D'UTILISATION:
        answer = call_mistral(
            user_message="Décris ces 3 concerts",
            system_message="Tu es un expert en musique. Sois concis.",
            messages_history=[{"role": "user", "content": "Quels concerts?"}, 
                            {"role": "assistant", "content": "Voici 3 concerts..."}]
        )
    """
    try:
        # ========== ÉTAPE 1: RÉCUPÉRER LA CLÉ API ==========
        # MISTRAL_API_KEY = Variable d'environnement avec la clé d'authentification
        # Elle doit être définie dans .env ou via docker-compose
        api_key = os.environ.get("MISTRAL_API_KEY")
        if not api_key:
            logger.warning("❌ MISTRAL_API_KEY not set")
            return None
        
        # ========== ÉTAPE 2: CONSTRUIRE LES MESSAGES ==========
        # L'API Mistral attend une liste de messages avec roles:
        # [{"role": "system", "content": "..."}, 
        #  {"role": "user", "content": "..."}, 
        #  ...]
        messages = []
        
        # Ajouter le message système si fourni
        # C'est comme dire à Mistral "Tu dois faire ça"
        if system_message:
            messages.append({
                "role": "system",
                "content": system_message
            })
        
        # Ajouter l'historique de conversation si fourni
        # Utile pour le chatbot qui garde la mémoire des messages précédents
        if messages_history:
            messages.extend(messages_history)
        
        # Ajouter le nouveau message utilisateur
        # C'est le message qu'on veut que Mistral traite
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        # ========== ÉTAPE 3: PRÉPARER LE PAYLOAD ==========
        # Payload = Configuration + données à envoyer à Mistral
        payload = {
            "model": "mistral-small-latest",  # Version du modèle Mistral
            "messages": messages,              # Les messages (voir étape 2)
            "temperature": 0.7,                # Créativité (0=déterministe, 1=aléatoire)
            "top_p": 1.0,                      # Diversité (nucleus sampling)
            "max_tokens": 1024                 # Longueur max de réponse
        }
        
        # ========== ÉTAPE 4: PRÉPARER LES HEADERS HTTP ==========
        # Headers = Métadonnées pour la requête HTTP
        headers = {
            "Authorization": f"Bearer {api_key}",  # Authentification avec clé API
            "Content-Type": "application/json"     # Format: JSON
        }
        
        # ========== ÉTAPE 5: ENVOYER LA REQUÊTE ==========
        logger.info("🔗 Appel Mistral API...")
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",  # URL de l'API Mistral
            headers=headers,                                 # Les headers (avec clé API)
            json=payload,                                    # Le contenu (messages + config)
            timeout=15                                       # Attendre max 15 secondes
        )
        
        # ========== ÉTAPE 6: VÉRIFIER LA RÉPONSE ==========
        # Code 200 = succès, autres codes = erreur
        if response.status_code != 200:
            logger.error(f"❌ Mistral {response.status_code}: {response.text[:200]}")
            return None
        
        # ========== ÉTAPE 7: PARSER LA RÉPONSE JSON ==========
        # Mistral retourne: {"choices": [{"message": {"content": "....."}}]}
        # On extrait juste le contenu
        result = response.json()
        answer = result["choices"][0]["message"]["content"]
        logger.info(f"✓ Mistral OK ({len(answer)} chars)")
        return answer
        
    except Exception as e:
        logger.error(f"❌ Mistral call failed: {type(e).__name__}: {e}")
        return None
