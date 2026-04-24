"""
MLflow tracking — ce qu'on log pour MeetingMind :
- Métriques de performance du pipeline (temps, nb décisions, nb actions)
- Qualité des embeddings (distance moyenne des top-k résultats RAG)
- Paramètres du pipeline (modèle Whisper, modèle LLM, etc.)
- Artifacts : transcripts, résumés générés

Ouvre http://localhost:5000 pour le dashboard MLflow.
"""

import mlflow
import mlflow.sklearn
from datetime import datetime
from functools import wraps

from core.config import settings


def setup_mlflow():
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    mlflow.set_experiment(settings.mlflow_experiment)


def log_pipeline_run(nlp_result, meeting_id: str, meeting_title: str):
    """Log les métriques d'un run pipeline complet."""
    setup_mlflow()

    with mlflow.start_run(run_name=f"pipeline_{meeting_title[:30]}_{datetime.now().strftime('%Y%m%d_%H%M')}"):
        # Params
        mlflow.log_params({
            "whisper_model": settings.whisper_model,
            "anthropic_model": settings.anthropic_model,
            "meeting_id": str(meeting_id),
        })

        # Métriques
        mlflow.log_metrics({
            "processing_time_s": nlp_result.processing_time_s,
            "transcript_length_chars": len(nlp_result.transcript),
            "num_speakers": len(nlp_result.speakers),
            "num_decisions": len(nlp_result.decisions),
            "num_action_items": len(nlp_result.action_items),
            "num_topics": len(nlp_result.topics),
            "summary_length_chars": len(nlp_result.summary),
            "minutes_length_chars": len(nlp_result.minutes_report),
        })

        # Sentiment moyen
        if nlp_result.sentiment_by_speaker:
            scores = [v["score"] for v in nlp_result.sentiment_by_speaker.values()]
            mlflow.log_metric("avg_sentiment_score", sum(scores) / len(scores))

        # Artifact : transcript brut
        with open("/tmp/transcript.txt", "w") as f:
            f.write(nlp_result.transcript)
        mlflow.log_artifact("/tmp/transcript.txt", "transcripts")

        # Artifact : compte-rendu généré
        with open("/tmp/minutes.md", "w") as f:
            f.write(nlp_result.minutes_report)
        mlflow.log_artifact("/tmp/minutes.md", "minutes")


def log_rag_query(question: str, n_results: int, avg_relevance: float, latency_s: float):
    """Log les métriques d'une requête RAG."""
    setup_mlflow()

    with mlflow.start_run(run_name=f"rag_query_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
        mlflow.log_params({
            "question_length": len(question),
            "n_results": n_results,
        })
        mlflow.log_metrics({
            "avg_relevance": avg_relevance,
            "latency_s": latency_s,
        })
