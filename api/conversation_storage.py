"""Gestion simple des conversations en JSON"""
import json
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
import uuid

logger = logging.getLogger(__name__)

# Use relative path that works both in Docker and CI
# In Docker: /app/data/conversations is volume-mounted
# In CI/local: data/conversations is created locally
CONVERSATIONS_DIR = Path(os.environ.get("CONVERSATIONS_DIR", "data/conversations"))

def _ensure_conversations_dir():
    """Crée le répertoire de conversations s'il n'existe pas."""
    try:
        CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)
    except (PermissionError, FileNotFoundError) as e:
        logger.warning(f"Could not create conversations directory: {e}")
        # Continue anyway, it might exist or be handled by Docker

_ensure_conversations_dir()

def generate_conversation_id() -> str:
    """Génère un ID unique pour une nouvelle conversation"""
    return str(uuid.uuid4())[:8]

def _get_conversation_file(conversation_id: str) -> Path:
    """Retourne le chemin du fichier de conversation"""
    return CONVERSATIONS_DIR / f"{conversation_id}.json"

def create_conversation(initial_message: str = "") -> str:
    """
    Crée une nouvelle conversation.
    
    Returns:
        L'ID de la conversation
    """
    _ensure_conversations_dir()
    conversation_id = generate_conversation_id()
    
    conversation = {
        "id": conversation_id,
        "created_at": datetime.now().isoformat(),
        "messages": []
    }
    
    if initial_message:
        conversation["messages"].append({
            "role": "user",
            "content": initial_message,
            "timestamp": datetime.now().isoformat()
        })
    
    file_path = _get_conversation_file(conversation_id)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(conversation, f, ensure_ascii=False, indent=2)
    
    logger.info(f"✓ Conversation créée: {conversation_id}")
    return conversation_id

def add_message(conversation_id: str, role: str, content: str) -> bool:
    """
    Ajoute un message à une conversation.
    
    Args:
        conversation_id: ID de la conversation
        role: 'user' ou 'assistant'
        content: Contenu du message
        
    Returns:
        True si succès, False sinon
    """
    file_path = _get_conversation_file(conversation_id)
    
    if not file_path.exists():
        logger.warning(f"Conversation {conversation_id} not found")
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            conversation = json.load(f)
        
        conversation["messages"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(conversation, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✓ Message ajouté à {conversation_id}")
        return True
    
    except Exception as e:
        logger.error(f"Erreur saving conversation: {e}")
        return False

def get_conversation(conversation_id: str) -> Optional[Dict]:
    """
    Récupère une conversation complète.
    
    Returns:
        Dict avec 'id', 'created_at', 'messages', ou None si pas trouvée
    """
    file_path = _get_conversation_file(conversation_id)
    
    if not file_path.exists():
        logger.warning(f"Conversation {conversation_id} not found")
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Erreur reading conversation: {e}")
        return None

def get_conversation_messages(conversation_id: str) -> List[Dict]:
    """
    Retourne juste la liste des messages pour l'historique Mistral.
    Format: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}, ...]
    """
    conversation = get_conversation(conversation_id)
    if not conversation:
        return []
    
    # Retourner juste role+content, sans timestamp
    return [
        {"role": msg["role"], "content": msg["content"]}
        for msg in conversation.get("messages", [])
    ]

def list_conversations() -> List[Dict]:
    """Liste toutes les conversations"""
    conversations = []
    
    for file_path in CONVERSATIONS_DIR.glob("*.json"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                conversations.append({
                    "id": data["id"],
                    "created_at": data["created_at"],
                    "message_count": len(data.get("messages", []))
                })
        except Exception as e:
            logger.warning(f"Erreur reading {file_path}: {e}")
    
    return sorted(conversations, key=lambda x: x["created_at"], reverse=True)

def delete_conversation(conversation_id: str) -> bool:
    """Supprime une conversation"""
    file_path = _get_conversation_file(conversation_id)
    
    if not file_path.exists():
        return False
    
    try:
        file_path.unlink()
        logger.info(f"✓ Conversation supprimée: {conversation_id}")
        return True
    except Exception as e:
        logger.error(f"Erreur deleting conversation: {e}")
        return False
