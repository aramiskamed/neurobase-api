"""
Flashcard parser for NeuroBase ingestion pipeline.
Handles multiple input formats → unified card schema.
"""
import json
import re
import hashlib
import uuid
from pathlib import Path
from typing import Optional


def parse_deck1_flashcard(card: dict) -> Optional[dict]:
    """Parse a Deck1 flashcard JSON into unified schema."""
    card_id = card.get("id", str(uuid.uuid4()))
    
    front = card.get("front", "").strip()
    back = card.get("back", "").strip()
    topic = card.get("topic", "MISC")
    
    if not front:
        return None
    
    # Build combined content for embedding
    if back:
        combined = f"Pergunta: {front}\nResposta: {back}"
    else:
        combined = front
    
    return {
        "id": card_id,
        "type": "flashcard",
        "content": combined,
        "question": front,
        "answer": back,
        "metadata": {
            "source": "deck1_neurobase",
            "topic": topic,
            "tags": _infer_tags(front, back),
            "language": "pt-BR",
            "difficulty": _estimate_difficulty(front, back),
        }
    }


def parse_sbn_question(entry: dict) -> Optional[dict]:
    """Parse a SBN/R1-R5 exam question entry."""
    q_id = entry.get("id", str(uuid.uuid4()))
    enunciado = entry.get("enunciado", "").strip()
    resposta = entry.get("resposta", "").strip()
    comentario = entry.get("comentario", "").strip()
    year = entry.get("year", 0)
    level = entry.get("level", "R1")
    source = entry.get("source", "SBN")
    
    if not enunciado or enunciado == "(incompleto no PDF)":
        return None
    
    # Combine question + answer for embedding
    combined = f"Pergunta: {enunciado}"
    if resposta:
        combined += f"\nResposta: {resposta}"
    if comentario:
        combined += f"\nComentário: {comentario[:500]}"
    
    return {
        "id": q_id,
        "type": "exam_question",
        "content": combined,
        "question": enunciado,
        "answer": resposta,
        "metadata": {
            "source": source,
            "year": year,
            "level": level,
            "commentary": comentario[:500] if comentario else "",
            "tags": [],
            "language": "pt-BR",
            "difficulty": "medium",
        }
    }


def parse_kt_mcq(entry: dict) -> Optional[dict]:
    """Parse a Knowledge Testing MCQ entry."""
    q_id = entry.get("id", str(uuid.uuid4()))
    stem = entry.get("stem", "").strip()
    choices = entry.get("choices", [])
    answer_text = entry.get("answer_text", "").strip()
    explanation = entry.get("explanation", "").strip()
    book = entry.get("book", "Unknown")
    
    if not stem:
        return None
    
    # Build question text with choices
    choices_text = "\n".join([f"  {c.get('letter','')}. {c.get('text','')}" for c in choices])
    combined = f"Question: {stem}\n\n{choices_text}\n\nAnswer: {answer_text}"
    if explanation:
        combined += f"\n\nExplanation: {explanation[:500]}"
    
    return {
        "id": q_id,
        "type": "mcq",
        "content": combined,
        "question": stem,
        "answer": answer_text,
        "metadata": {
            "source": book,
            "choices_count": len(choices),
            "explanation": explanation[:500] if explanation else "",
            "tags": [],
            "language": "en",
            "difficulty": _estimate_difficulty(stem, explanation or ""),
        }
    }


def _infer_tags(question: str, answer: str) -> list[str]:
    """Infer tags from card content (lightweight NLP)."""
    text = f"{question} {answer}".lower()
    tags = []
    
    keywords = {
        "neuroanatomia": ["córtex", "tálamo", "cápsula", "gânglio", "nervo", "tronco", "cerebelo"],
        "neuroftalmologia": ["pupila", "papila", "quiasma", "vírus", "campo visual", "óptico"],
        "neurovascular": ["aneurisma", "avc", "acidente vascular", "hemorragia", "trombose", "coil", "pipeline"],
        "neurocritical": ["icu", "ventilação", "pressão intracraniana", "hidrocefalia", "coma", "shunt"],
        "dbs": ["parkinson", "deep brain", "estimulação", "tálamo", "gp", "stn"],
        "radiologia": ["tomografia", "ressonância", "angiografia", "pet", "spect"],
        "neurooncologia": ["glioma", "meningioma", "tumor", "metástase", "radio", "quimio"],
        "neurotrauma": ["tce", "traumatismo", "fratura", "hemorragia epidural", "subdural"],
        "epilepsia": ["epilepsia", "crise", "convulsão", "tônico", "clônico", "status epilepticus"],
        "pediatria": ["pediátrico", "criança", "malformação", "hidrocefalia congênita"],
    }
    
    for tag, keywords_list in keywords.items():
        if any(kw in text for kw in keywords_list):
            tags.append(tag)
    
    return tags[:5]


def _estimate_difficulty(question: str, answer: str) -> str:
    """Estimate card difficulty based on content features."""
    text = f"{question} {answer}"
    word_count = len(text.split())
    
    hard_markers = ["raro", "atípico", "avançado", "cirurgia de", "mais comum", "tratamento de escolha"]
    medium_markers = ["qual", "diferença", "quando", "como"]
    
    if any(m in text.lower() for m in hard_markers):
        return "hard"
    elif any(m in text.lower() for m in medium_markers) or word_count > 80:
        return "medium"
    else:
        return "easy"


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> list[dict]:
    """Chunk large text for lecture/book ingestion."""
    words = text.split()
    chunks = []
    
    for i in range(0, len(words), chunk_size - overlap):
        chunk_words = words[i:i + chunk_size]
        chunk_text = " ".join(chunk_words)
        
        chunks.append({
            "id": f"chunk_{hashlib.md5(chunk_text.encode()).hexdigest()[:8]}",
            "type": "text_chunk",
            "content": chunk_text,
            "metadata": {
                "chunk_index": i // (chunk_size - overlap),
                "total_chunks": len(chunks),
                "word_count": len(chunk_words),
            }
        })
        
        if i + chunk_size >= len(words):
            break
    
    return chunks
