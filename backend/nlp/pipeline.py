"""
Pipeline NLP — cœur de MeetingMind.

Étapes :
1. Transcription avec OpenAI Whisper
2. Diarisation (qui parle quand) avec pyannote.audio
3. Résumé automatique (BART via HuggingFace)
4. Extraction décisions + action items (Claude API)
5. Analyse de sentiment par speaker (transformers)
6. Détection de topics (BERTopic)
"""

import time
import re
from dataclasses import dataclass, field
from pathlib import Path

import whisper
import torch
from transformers import pipeline as hf_pipeline
from bertopic import BERTopic
import anthropic

from core.config import settings
import os
FFMPEG = r"C:\Users\nouha\miniconda3\envs\meetingmind\Library\bin\ffmpeg.exe"
os.environ["PATH"] = r"C:\Users\nouha\miniconda3\envs\meetingmind\Library\bin" + os.pathsep + os.environ.get("PATH", "")


# ---------------------------------------------------------------------------
# Dataclasses de résultat
# ---------------------------------------------------------------------------

@dataclass
class SpeakerSegment:
    speaker: str
    start: float
    end: float
    text: str


@dataclass
class ActionItem:
    task: str
    owner: str
    deadline: str = "non précisé"


@dataclass
class Decision:
    text: str
    speaker: str


@dataclass
class NLPResult:
    transcript: str
    segments: list[SpeakerSegment]
    summary: str
    decisions: list[Decision]
    action_items: list[ActionItem]
    topics: list[dict]
    sentiment_by_speaker: dict
    speakers: list[dict]
    minutes_report: str
    processing_time_s: float


# ---------------------------------------------------------------------------
# Chargement lazy des modèles (évite de recharger à chaque appel)
# ---------------------------------------------------------------------------

_whisper_model = None
_summarizer = None
_sentiment_analyzer = None


def _get_whisper():
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = whisper.load_model(settings.whisper_model)
    return _whisper_model


def _get_summarizer():
    global _summarizer
    if _summarizer is None:
        _summarizer = hf_pipeline(
            "summarization",
            model="facebook/bart-large-cnn",
            device=0 if torch.cuda.is_available() else -1,
        )
    return _summarizer


def _get_sentiment():
    global _sentiment_analyzer
    if _sentiment_analyzer is None:
        _sentiment_analyzer = hf_pipeline(
            "sentiment-analysis",
            model="cardiffnlp/twitter-roberta-base-sentiment-latest",
            device=0 if torch.cuda.is_available() else -1,
        )
    return _sentiment_analyzer


# ---------------------------------------------------------------------------
# Étape 1 : Transcription Whisper
# ---------------------------------------------------------------------------

def transcribe(audio_path: str, language: str = "fr") -> dict:
    """Retourne le transcript brut Whisper avec timestamps par segment."""
    model = _get_whisper()
    import whisper.audio as _wa
    import subprocess
    _original_run = subprocess.run

    def _patched_run(cmd, **kwargs):
        if cmd and cmd[0] == "ffmpeg":
            cmd[0] = FFMPEG
        return _original_run(cmd, **kwargs)

    subprocess.run = _patched_run
    try:
        result = model.transcribe(
            audio_path,
            language=language,
            word_timestamps=True,
            verbose=False,
        )
    finally:
        subprocess.run = _original_run
    return result
  


# ---------------------------------------------------------------------------
# Étape 2 : Diarisation pyannote (qui parle quand)
# ---------------------------------------------------------------------------

def diarize(audio_path: str) -> list[dict]:
    """
    Retourne une liste de segments {speaker, start, end}.
    Nécessite un token HuggingFace acceptant les conditions pyannote.
    En dev, on peut stubber cette fonction.
    """
    try:
        from pyannote.audio import Pipeline as PyannotePipeline

        diar_pipeline = PyannotePipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=settings.hf_token if hasattr(settings, "hf_token") else None,
        )
        diarization = diar_pipeline(audio_path)

        segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append({"speaker": speaker, "start": turn.start, "end": turn.end})
        return segments

    except Exception:
        # Fallback en dev : un seul speaker
        return [{"speaker": "Speaker_0", "start": 0.0, "end": 99999.0}]


# ---------------------------------------------------------------------------
# Fusion transcript + diarisation
# ---------------------------------------------------------------------------

def merge_transcript_diarization(
    whisper_result: dict, diar_segments: list[dict]
) -> list[SpeakerSegment]:
    """Associe chaque segment Whisper au speaker diarisé le plus proche."""
    merged = []
    for seg in whisper_result["segments"]:
        seg_start = seg["start"]
        seg_end = seg["end"]
        seg_text = seg["text"].strip()

        # Trouver le speaker qui couvre le plus ce segment
        best_speaker = "Speaker_0"
        best_overlap = 0.0
        for d in diar_segments:
            overlap = min(seg_end, d["end"]) - max(seg_start, d["start"])
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = d["speaker"]

        merged.append(SpeakerSegment(
            speaker=best_speaker,
            start=seg_start,
            end=seg_end,
            text=seg_text,
        ))
    return merged


# ---------------------------------------------------------------------------
# Étape 3 : Résumé BART
# ---------------------------------------------------------------------------

def summarize(transcript: str, max_length: int = 300) -> str:
    summarizer = _get_summarizer()
    # BART a une limite de tokens — on tronque si besoin
    chunk = transcript[:3000]
    result = summarizer(chunk, max_length=max_length, min_length=80, do_sample=False)
    return result[0]["summary_text"]


# ---------------------------------------------------------------------------
# Étape 4 : Extraction décisions + action items via Claude
# ---------------------------------------------------------------------------

_EXTRACTION_PROMPT = """Analyse ce transcript de réunion et extrais les informations suivantes au format JSON strict.

TRANSCRIPT :
{transcript}

Réponds UNIQUEMENT avec un JSON valide, sans markdown, dans ce format exact :
{{
  "decisions": [
    {{"text": "décision prise", "speaker": "nom ou Speaker_X"}}
  ],
  "action_items": [
    {{"task": "tâche à faire", "owner": "responsable", "deadline": "date ou 'non précisé'"}}
  ]
}}

Règles :
- Ne retourne que des décisions explicitement prises, pas des opinions
- Les action items doivent avoir un verbe à l'infinitif
- Si aucune décision ni action, retourne des listes vides
"""


def extract_decisions_and_actions(transcript: str) -> tuple[list[Decision], list[ActionItem]]:
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    message = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": _EXTRACTION_PROMPT.format(transcript=transcript[:4000]),
        }],
    )

    import json
    raw = message.content[0].text.strip()
    # Nettoyage au cas où le modèle ajoute des backticks
    raw = re.sub(r"```json|```", "", raw).strip()
    data = json.loads(raw)

    decisions = [Decision(**d) for d in data.get("decisions", [])]
    actions = [ActionItem(**a) for a in data.get("action_items", [])]
    return decisions, actions


# ---------------------------------------------------------------------------
# Étape 5 : Sentiment par speaker
# ---------------------------------------------------------------------------

def analyze_sentiment_by_speaker(segments: list[SpeakerSegment]) -> dict:
    analyzer = _get_sentiment()

    speaker_texts: dict[str, list[str]] = {}
    for seg in segments:
        speaker_texts.setdefault(seg.speaker, []).append(seg.text)

    result = {}
    for speaker, texts in speaker_texts.items():
        combined = " ".join(texts)[:512]
        raw = analyzer(combined)[0]
        label = raw["label"].lower()  # positive / neutral / negative
        result[speaker] = {
            "label": label,
            "score": round(raw["score"], 3),
            "talk_ratio": round(len(combined) / max(sum(len(t) for t in speaker_texts.values()), 1), 3),
        }
    return result


# ---------------------------------------------------------------------------
# Étape 6 : Topics BERTopic
# ---------------------------------------------------------------------------

def detect_topics(segments: list[SpeakerSegment]) -> list[dict]:
    texts = [s.text for s in segments if len(s.text) > 20]
    if len(texts) < 5:
        return []

    try:
        model = BERTopic(language="multilingual", nr_topics=5, verbose=False)
        topics, _ = model.fit_transform(texts)
        topic_info = model.get_topic_info()

        result = []
        for _, row in topic_info.iterrows():
            if row["Topic"] == -1:
                continue
            result.append({
                "topic": row["Name"],
                "count": int(row["Count"]),
                "weight": round(row["Count"] / len(texts), 3),
            })
        return result[:5]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Étape 7 : Génération compte-rendu Claude
# ---------------------------------------------------------------------------

_MINUTES_PROMPT = """Tu es un assistant spécialisé en rédaction de comptes-rendus professionnels.

Génère un compte-rendu de réunion professionnel et structuré à partir des informations suivantes.
Langue demandée : {language}

RÉSUMÉ : {summary}

DÉCISIONS PRISES :
{decisions}

ACTIONS À RÉALISER :
{actions}

PARTICIPANTS IDENTIFIÉS : {speakers}

SUJETS ABORDÉS : {topics}

Rédige un compte-rendu clair, professionnel, en {language}. Structure :
1. En-tête (date, participants)
2. Points discutés
3. Décisions prises
4. Plan d'action (tableau si pertinent)
5. Prochaines étapes
"""


def generate_minutes(
    summary: str,
    decisions: list[Decision],
    action_items: list[ActionItem],
    speakers: list[str],
    topics: list[dict],
    language: str = "fr",
) -> str:
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    dec_str = "\n".join(f"- {d.text} ({d.speaker})" for d in decisions) or "Aucune décision formelle"
    act_str = "\n".join(f"- {a.task} → {a.owner} [{a.deadline}]" for a in action_items) or "Aucune action définie"
    topics_str = ", ".join(t["topic"] for t in topics) or "Non déterminé"
    lang_label = "français" if language == "fr" else "English"

    message = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": _MINUTES_PROMPT.format(
                language=lang_label,
                summary=summary,
                decisions=dec_str,
                actions=act_str,
                speakers=", ".join(speakers),
                topics=topics_str,
            ),
        }],
    )
    return message.content[0].text


# ---------------------------------------------------------------------------
# Pipeline complet
# ---------------------------------------------------------------------------

def run_pipeline(audio_path: str, language: str = "fr") -> NLPResult:
    start = time.time()

    # 1. Transcription
    whisper_result = transcribe(audio_path, language)
    transcript = whisper_result["text"]

    # 2. Diarisation
    diar_segments = diarize(audio_path)

    # 3. Fusion
    merged_segments = merge_transcript_diarization(whisper_result, diar_segments)

    # 4. Résumé
    summary = summarize(transcript)

    # 5. Décisions + actions
    decisions, action_items = extract_decisions_and_actions(transcript)

    # 6. Sentiment
    sentiment = analyze_sentiment_by_speaker(merged_segments)

    # 7. Topics
    topics = detect_topics(merged_segments)

    # 8. Speakers stats
    speakers_list = list(sentiment.keys())
    speakers_stats = [
        {"id": sp, "talk_ratio": sentiment[sp]["talk_ratio"]}
        for sp in speakers_list
    ]

    # 9. Compte-rendu
    minutes = generate_minutes(summary, decisions, action_items, speakers_list, topics, language)

    return NLPResult(
        transcript=transcript,
        segments=merged_segments,
        summary=summary,
        decisions=decisions,
        action_items=action_items,
        topics=topics,
        sentiment_by_speaker=sentiment,
        speakers=speakers_stats,
        minutes_report=minutes,
        processing_time_s=round(time.time() - start, 2),
    )
