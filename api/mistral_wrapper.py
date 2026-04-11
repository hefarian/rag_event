"""Wrapper simple pour l'API Mistral via HTTP requests"""
import os
import requests
import logging
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

def call_mistral(user_message: str, system_message: str = "", messages_history: List[Dict] = None) -> Optional[str]:
    """
    Appelle l'API Mistral directement via HTTP requests.
    Pas de dépendances SDK complexes, juste de l'HTTP.
    
    Args:
        user_message: Message utilisateur
        system_message: Message système optionnel
        messages_history: Historique complet de la conversation (pour chatbot)
                         Format: [{"role": "user/assistant", "content": "..."}, ...]
        
    Returns:
        La réponse du modèle, ou None si erreur
    """
    try:
        api_key = os.environ.get("MISTRAL_API_KEY")
        if not api_key:
            logger.warning("❌ MISTRAL_API_KEY not set")
            return None
        
        # Construire les messages
        messages = []
        
        if system_message:
            messages.append({
                "role": "system",
                "content": system_message
            })
        
        # Ajouter l'historique si fourni
        if messages_history:
            messages.extend(messages_history)
        
        # Ajouter le nouveau message utilisateur
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        # Payload pour l'API Mistral
        payload = {
            "model": "mistral-small-latest",
            "messages": messages,
            "temperature": 0.7,
            "top_p": 1.0,
            "max_tokens": 1024
        }
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        logger.info("🔗 Appel Mistral API...")
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=15
        )
        
        if response.status_code != 200:
            logger.error(f"❌ Mistral {response.status_code}: {response.text[:200]}")
            return None
        
        result = response.json()
        answer = result["choices"][0]["message"]["content"]
        logger.info(f"✓ Mistral OK ({len(answer)} chars)")
        return answer
        
    except Exception as e:
        logger.error(f"❌ Mistral call failed: {type(e).__name__}: {e}")
        return None
