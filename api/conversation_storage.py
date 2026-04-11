"""Gestion simple des conversations en JSON.

POURQUOI JSON?
On aurait pu utiliser une database (PostgreSQL, MongoDB) mais JSON c'est:
- Plus simple pour un POC
- Fichiers lisibles = facile à déboguer
- Pas besoin d'installer une DB
- Parfait pour test/démo

STRUCTURE:
data/conversations/
├── 1a2b3c4d.json  (conversation 1: user + assistant messages)
├── 5e6f7g8h.json  (conversation 2)
└── ...

CONTENU D'UN FILE:
{
  "id": "1a2b3c4d",
  "created_at": "2026-04-11T14:30:00",
  "messages": [
    {"role": "user", "content": "Quels concerts?", "timestamp": "..."},
    {"role": "assistant", "content": "Voici les concerts...", "timestamp": "..."},
    ...
  ]
}
"""
import json
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
import uuid

logger = logging.getLogger(__name__)

# CHEMIN DE STOCKAGE:
# - Docker: /app/data/conversations (volume-mounted)
# - Local: data/conversations (crée localement)
# Cette approche permet au code de fonctionner partout!
CONVERSATIONS_DIR = Path(os.environ.get("CONVERSATIONS_DIR", "data/conversations"))

def _ensure_conversations_dir():
    """Crée le répertoire de conversations s'il n'existe pas.
    
    POURQUOI?
    Avant de sauvegarder un fichier JSON, s'assurer que le dossier existe
    Sinon: "FileNotFoundError: [Errno 2] No such file or directory"
    """
    try:
        # mkdir() = "make directory"
        # parents=True = créer les dossiers parents si nécessaire
        # exist_ok=True = ne pas crasher si le dossier existe déjà
        CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)
    except (PermissionError, FileNotFoundError) as e:
        logger.warning(f"Could not create conversations directory: {e}")
        # Continue anyway, it might exist or be handled by Docker

_ensure_conversations_dir()

def generate_conversation_id() -> str:
    """Génère un ID unique pour une nouvelle conversation.
    
    EXEMPLE:
    12345678-abcd-...-xxxx → "12345678"
    (UUID complet est trop long, on prend juste les 8 premiers chars)
    """
    return str(uuid.uuid4())[:8]

def _get_conversation_file(conversation_id: str) -> Path:
    """Retourne le chemin du fichier de conversation.
    
    EXEMPLE:
    conversation_id = "1a2b3c4d"
    Retourne: Path("data/conversations/1a2b3c4d.json")
    """
    return CONVERSATIONS_DIR / f"{conversation_id}.json"

def create_conversation(initial_message: str = "") -> str:
    """
    Crée une nouvelle conversation et sauvegarde dans un fichier JSON.
    
    ÉTAPES:
    1. Générer un ID unique pour la conversation
    2. Créer la structure JSON
    3. Si message initial fourni, l'ajouter
    4. Sauvegarder dans data/conversations/{id}.json
    5. Retourner l'ID
    
    Args:
        initial_message: Message utilisateur optionnel au démarrage
        
    Returns:
        L'ID de la conversation (8 chars)
        
    EXEMPLE:
    >>> conversation_id = create_conversation("Quels events?")
    >>> conversation_id
    '1a2b3c4d'
    >>> # Fichier créé: data/conversations/1a2b3c4d.json
    """
    _ensure_conversations_dir()
    conversation_id = generate_conversation_id()
    
    # Structure de la conversation (vide pour début)
    conversation = {
        "id": conversation_id,
        "created_at": datetime.now().isoformat(),  # Date de création
        "messages": []
    }
    
    # Si message initial fourni, l'ajouter
    if initial_message:
        conversation["messages"].append({
            "role": "user",
            "content": initial_message,
            "timestamp": datetime.now().isoformat()
        })
    
    # Sauvegarder dans un fichier JSON
    file_path = _get_conversation_file(conversation_id)
    with open(file_path, 'w', encoding='utf-8') as f:
        # ensure_ascii=False = accepter les accents (français!)
        # indent=2 = formater avec indentation pour lisibilité
        json.dump(conversation, f, ensure_ascii=False, indent=2)
    
    logger.info(f"✓ Conversation créée: {conversation_id}")
    return conversation_id

def add_message(conversation_id: str, role: str, content: str) -> bool:
    """
    Ajoute un message à une conversation existante.
    
    ÉTAPES:
    1. Chercher le fichier JSON de la conversation
    2. Le charger en mémoire
    3. Ajouter le nouveau message à la liste
    4. Re-sauvegarder le fichier
    
    Args:
        conversation_id: ID de la conversation (ex: "1a2b3c4d")
        role: 'user' ou 'assistant' - qui a écrit ce message
        content: Le texte du message
        
    Returns:
        True si succès, False sinon
        
    EXEMPLE:
    >>> add_message("1a2b3c4d", "user", "Concerts à Paris?")
    True
    >>> add_message("1a2b3c4d", "assistant", "Voici les concerts...")
    True
    """
    file_path = _get_conversation_file(conversation_id)
    
    if not file_path.exists():
        logger.warning(f"Conversation {conversation_id} not found")
        return False
    
    try:
        # Charger le fichier JSON existant
        with open(file_path, 'r', encoding='utf-8') as f:
            conversation = json.load(f)
        
        # Ajouter le nouveau message
        conversation["messages"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        # Re-sauvegarder le fichier (maintenant avec le nouveau message)
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
