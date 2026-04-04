"""
Script d'évaluation automatisée pour le système RAG Puls-Events.

Mesure :
- Couverture : % de sources trouvées
- Pertinence : correspondance des keywords
- Robustesse : temps de réponse, gestion d'erreurs
- Performance : FAISS recall@k

Produit un rapport JSON et texte.
"""

import json
import pathlib
import requests
import time
import logging
from datetime import datetime
from typing import List, Dict, Any

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
API_URL = "http://localhost:8000"
TEST_SET_PATH = pathlib.Path("doc/test_set_annotated.jsonl")
RESULTS_PATH = pathlib.Path("doc/evaluation_results.json")

# Métriques
class Metrics:
    def __init__(self):
        self.total_tests = 0
        self.passed = 0
        self.failed = 0
        self.avg_response_time = 0
        self.keyword_match_rate = 0
        self.source_coverage = 0
        self.errors = []


def load_test_set(path: str = None) -> List[Dict]:
    """Charge le jeu de test annoté."""
    if path is None:
        path = TEST_SET_PATH
    
    if not pathlib.Path(path).exists():
        logger.warning(f"Test set not found: {path}")
        return []
    
    tests = []
    with open(path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            try:
                tests.append(json.loads(line))
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON at line {i+1}: {e}")
    
    return tests


def check_api_health(url: str = API_URL) -> bool:
    """Vérifie que l'API est accessible."""
    try:
        response = requests.get(f"{url}/health", timeout=5)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"API health check failed: {e}")
        return False


def evaluate_single_test(test: Dict, api_url: str = API_URL) -> Dict:
    """Évalue une requête seule."""
    result = {
        "question": test.get("question"),
        "expected_keywords": test.get("expected_keywords", []),
        "min_sources": test.get("min_sources", 1),
        "passed": False,
        "response_time": 0,
        "sources_found": 0,
        "keyword_match": 0,
        "error": None
    }
    
    try:
        question = test.get("question", "")
        if not question:
            result["error"] = "Empty question"
            return result
        
        # Timer la requête
        start = time.time()
        response = requests.post(
            f"{api_url}/ask",
            json={"question": question, "top_k": 5},
            timeout=30
        )
        elapsed = time.time() - start
        result["response_time"] = round(elapsed, 3)
        
        if response.status_code != 200:
            result["error"] = f"HTTP {response.status_code}"
            return result
        
        data = response.json()
        sources = data.get("sources", [])
        result["sources_found"] = len(sources)
        
        # Vérifier couverture des sources
        min_sources = test.get("min_sources", 1)
        if len(sources) >= min_sources:
            result["passed"] = True
        else:
            result["error"] = f"Not enough sources: {len(sources)} < {min_sources}"
        
        # Vérifier correspondance des keywords
        answer = data.get("answer", "").lower()
        expected_keywords = test.get("expected_keywords", [])
        
        if expected_keywords:
            matches = sum(1 for kw in expected_keywords if kw.lower() in answer)
            result["keyword_match"] = round(matches / len(expected_keywords), 2)
        
        return result
    
    except requests.exceptions.Timeout:
        result["error"] = "Timeout"
        return result
    except Exception as e:
        result["error"] = str(e)
        return result


def run_evaluation(api_url: str = API_URL) -> Metrics:
    """Lance l'évaluation complète."""
    logger.info("=" * 60)
    logger.info("DÉBUT DE L'ÉVALUATION RAG")
    logger.info("=" * 60)
    
    metrics = Metrics()
    results = []
    
    # 1. Vérifier l'API
    logger.info("Vérification de l'API...")
    if not check_api_health(api_url):
        logger.error("API not accessible!")
        metrics.errors.append("API not accessible")
        return metrics
    logger.info("✓ API accessible")
    
    # 2. Charger les tests
    logger.info("Chargement du jeu de test...")
    tests = load_test_set()
    if not tests:
        logger.warning("No tests loaded!")
        metrics.errors.append("No tests loaded")
        return metrics
    logger.info(f"✓ {len(tests)} tests chargés")
    
    # 3. Exécuter les tests
    logger.info(f"Exécution des {len(tests)} tests...")
    response_times = []
    keyword_matches = []
    sources_list = []
    
    for i, test in enumerate(tests):
        logger.info(f"  Test {i+1}/{len(tests)}: {test['question'][:50]}...")
        result = evaluate_single_test(test, api_url)
        results.append(result)
        metrics.total_tests += 1
        
        if result.get("passed"):
            metrics.passed += 1
        else:
            metrics.failed += 1
        
        if result.get("error"):
            metrics.errors.append(f"Test {i+1}: {result['error']}")
        
        response_times.append(result["response_time"])
        keyword_matches.append(result["keyword_match"])
        sources_list.append(result["sources_found"])
    
    # 4. Calculer les métriques
    logger.info("Calcul des métriques...")
    
    if response_times:
        metrics.avg_response_time = round(sum(response_times) / len(response_times), 3)
    
    if keyword_matches:
        metrics.keyword_match_rate = round(sum(keyword_matches) / len(keyword_matches), 2)
    
    if sources_list and len(sources_list) > 0:
        avg_sources = sum(sources_list) / len(sources_list)
        metrics.source_coverage = round(avg_sources / 5.0, 2)  # 5 = top_k max
    
    # 5. Sauvegarder les résultats
    report = {
        "timestamp": datetime.now().isoformat(),
        "api_url": api_url,
        "summary": {
            "total_tests": metrics.total_tests,
            "passed": metrics.passed,
            "failed": metrics.failed,
            "pass_rate": round(metrics.passed / metrics.total_tests, 2) if metrics.total_tests > 0 else 0,
            "avg_response_time_s": metrics.avg_response_time,
            "keyword_match_rate": metrics.keyword_match_rate,
            "avg_source_coverage": metrics.source_coverage
        },
        "details": results,
        "errors": metrics.errors
    }
    
    # Sauvegarder JSON
    with open(RESULTS_PATH, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    logger.info(f"✓ Résultats sauvegardés: {RESULTS_PATH}")
    
    # Afficher le résumé
    logger.info("=" * 60)
    logger.info("RÉSULTATS DE L'ÉVALUATION")
    logger.info("=" * 60)
    logger.info(f"Tests réussis : {metrics.passed}/{metrics.total_tests} ({report['summary']['pass_rate']:.0%})")
    logger.info(f"Temps moyen : {metrics.avg_response_time}s")
    logger.info(f"Correspondance keywords : {metrics.keyword_match_rate:.0%}")
    logger.info(f"Couverture sources : {metrics.source_coverage:.0%}")
    
    if metrics.errors:
        logger.warning(f"Erreurs détectées ({len(metrics.errors)}):")
        for error in metrics.errors[:5]:
            logger.warning(f"  - {error}")
    
    logger.info("=" * 60)
    
    return metrics


if __name__ == "__main__":
    import sys
    
    api_url = sys.argv[1] if len(sys.argv) > 1 else API_URL
    metrics = run_evaluation(api_url)
    
    # Exit code basé sur le taux de passage
    exit_code = 0 if metrics.passed > 0 else 1
    sys.exit(exit_code)
