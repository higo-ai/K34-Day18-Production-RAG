from __future__ import annotations

"""
Module 5: Enrichment Pipeline
==============================
Làm giàu chunks TRƯỚC khi embed: Summarize, HyQA, Contextual Prepend, Auto Metadata.

Test: pytest tests/test_m5.py
"""

import os, sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import OPENAI_API_KEY


@dataclass
class EnrichedChunk:
    """Chunk đã được làm giàu."""
    original_text: str
    enriched_text: str
    summary: str
    hypothesis_questions: list[str]
    auto_metadata: dict
    method: str  # "contextual", "summary", "hyqa", "full"


# ─── Technique 1: Chunk Summarization ────────────────────


def call_llm(system_prompt: str, user_prompt: str, max_tokens: int = 300, json_mode: bool = False) -> str:
    import os
    import time
    from openai import OpenAI

    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()

    is_gemini = False
    active_key = ""
    if gemini_key:
        is_gemini = True
        active_key = gemini_key
    elif openai_key and openai_key.startswith("AQ."):
        is_gemini = True
        active_key = openai_key

    if not openai_key and not gemini_key:
        raise ValueError("No API Key configured.")

    if is_gemini:
        client = OpenAI(
            api_key=active_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        model = "gemini-3.5-flash-lite"
    else:
        client = OpenAI(api_key=openai_key)
        model = "gpt-4o-mini"

    for attempt in range(4):
        try:
            kwargs = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": max_tokens,
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            resp = client.chat.completions.create(**kwargs)
            if is_gemini:
                time.sleep(4.5)
            return resp.choices[0].message.content.strip()
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "rate_limit" in err_msg.lower() or "quota" in err_msg.lower() or "limit" in err_msg.lower():
                sleep_time = 10 * (attempt + 1)
                print(f"  ⚠️ Quá giới hạn API (429/Quota), đang ngủ {sleep_time} giây trước khi thử lại (lần {attempt+1})...", flush=True)
                time.sleep(sleep_time)
            else:
                raise e
    raise RuntimeError("API rate limit exceeded after maximum retries.")


def summarize_chunk(text: str) -> str:
    """
    Tạo summary ngắn cho chunk.
    Embed summary thay vì (hoặc cùng với) raw chunk → giảm noise.
    """
    try:
        system_prompt = "Tóm tắt đoạn văn sau trong 2-3 câu ngắn gọn bằng tiếng Việt."
        return call_llm(system_prompt, text, max_tokens=150)
    except Exception:
        import re
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+|\n\n', text) if s.strip()]
        return ". ".join(sentences[:2]) + "." if sentences else text


# ─── Technique 2: Hypothesis Question-Answer (HyQA) ─────


def generate_hypothesis_questions(text: str, n_questions: int = 3) -> list[str]:
    """
    Generate câu hỏi mà chunk có thể trả lời.
    Index cả questions lẫn chunk → query match tốt hơn (bridge vocabulary gap).
    """
    try:
        system_prompt = f"Dựa trên đoạn văn, tạo {n_questions} câu hỏi mà đoạn văn có thể trả lời. Trả về mỗi câu hỏi trên 1 dòng."
        res = call_llm(system_prompt, text, max_tokens=200)
        questions = res.split("\n")
        return [q.strip().lstrip("0123456789.-) ") for q in questions if q.strip()][:n_questions]
    except Exception:
        import re
        sentences = [s.strip() for s in re.split(r'[.!?\n]', text) if len(s.strip()) > 10]
        return [f"{s.rstrip('.')}?" for s in sentences[:n_questions]]


# ─── Technique 3: Contextual Prepend (Anthropic style) ──


def contextual_prepend(text: str, document_title: str = "") -> str:
    """
    Prepend context giải thích chunk nằm ở đâu trong document.
    Anthropic benchmark: giảm 49% retrieval failure (alone).
    """
    try:
        system_prompt = "Viết 1 câu ngắn mô tả đoạn văn này nằm ở đâu trong tài liệu và nói về chủ đề gì. Chỉ trả về 1 câu."
        user_prompt = f"Tài liệu: {document_title}\n\nĐoạn văn:\n{text}"
        context = call_llm(system_prompt, user_prompt, max_tokens=80)
        return f"{context}\n\n{text}"
    except Exception:
        prefix = f"Trích từ {document_title}. " if document_title else ""
        return f"{prefix}{text}"


# ─── Technique 4: Auto Metadata Extraction ──────────────


def extract_metadata(text: str) -> dict:
    """
    LLM extract metadata tự động: topic, entities, date_range, category.
    """
    import json as _json
    try:
        system_prompt = 'Trích xuất metadata từ đoạn văn. Trả về JSON: {"topic": "...", "entities": ["..."], "category": "policy|hr|it|finance", "language": "vi|en"}'
        res = call_llm(system_prompt, text, max_tokens=150, json_mode=True)
        return _json.loads(res)
    except Exception:
        return {"topic": "general", "entities": [], "category": "policy", "language": "vi"}


# ─── Combined Single-Call Mode ───────────────────────────


def _enrich_single_call(text: str, source: str) -> dict:
    """Single LLM call to get summary + questions + context + metadata.

    ⚠️ Cost optimization: 1 API call thay vì 4 calls riêng lẻ.
    """
    import json as _json
    try:
        system_prompt = """Phân tích đoạn văn và trả về JSON:
{
  "summary": "tóm tắt 2-3 câu",
  "questions": ["câu hỏi 1", "câu hỏi 2", "câu hỏi 3"],
  "context": "1 câu mô tả đoạn văn nằm ở đâu trong tài liệu",
  "metadata": {"topic": "...", "entities": ["..."], "category": "policy|hr|it|finance", "language": "vi|en"}
}"""
        user_prompt = f"Tài liệu: {source}\n\nĐoạn văn:\n{text}"
        res = call_llm(system_prompt, user_prompt, max_tokens=400, json_mode=True)
        return _json.loads(res)
    except Exception:
        return {}


# ─── Full Enrichment Pipeline ────────────────────────────


def enrich_chunks(
    chunks: list[dict],
    methods: list[str] | None = None,
) -> list[EnrichedChunk]:
    """
    Chạy enrichment pipeline trên danh sách chunks. (Đã implement sẵn — dùng functions ở trên)

    Có 2 chế độ:
    - methods cụ thể (["summary"], ["contextual"]...): gọi từng function riêng (tốt cho học/debug)
    - methods=["combined"] hoặc None: 1 API call duy nhất cho tất cả (tốt cho production)

    Args:
        chunks: List of {"text": str, "metadata": dict}
        methods: Default None → combined mode (1 call/chunk).
                 Options: "summary", "hyqa", "contextual", "metadata", "combined"
    """
    if methods is None:
        methods = ["combined"]

    use_combined = "combined" in methods

    enriched = []
    for i, chunk in enumerate(chunks):
        text = chunk["text"]
        source = chunk.get("metadata", {}).get("source", "")

        if use_combined:
            result = _enrich_single_call(text, source)
            summary = result.get("summary", "")
            questions = result.get("questions", [])
            context_line = result.get("context", "")
            enriched_text = f"{context_line}\n\n{text}" if context_line else text
            auto_meta = result.get("metadata", {})
        else:
            summary = summarize_chunk(text) if "summary" in methods else ""
            questions = generate_hypothesis_questions(text) if "hyqa" in methods else []
            enriched_text = contextual_prepend(text, source) if "contextual" in methods else text
            auto_meta = extract_metadata(text) if "metadata" in methods else {}

        enriched.append(EnrichedChunk(
            original_text=text,
            enriched_text=enriched_text,
            summary=summary,
            hypothesis_questions=questions,
            auto_metadata={**chunk.get("metadata", {}), **auto_meta},
            method="+".join(methods),
        ))

        if (i + 1) % 10 == 0 or (i + 1) == len(chunks):
            print(f"  Enriched {i + 1}/{len(chunks)} chunks...", flush=True)

    return enriched


# ─── Main ────────────────────────────────────────────────

if __name__ == "__main__":
    sample = "Nhân viên chính thức được nghỉ phép năm 12 ngày làm việc mỗi năm. Số ngày nghỉ phép tăng thêm 1 ngày cho mỗi 5 năm thâm niên công tác."

    print("=== Enrichment Pipeline Demo ===\n")
    print(f"Original: {sample}\n")

    s = summarize_chunk(sample)
    print(f"Summary: {s}\n")

    qs = generate_hypothesis_questions(sample)
    print(f"HyQA questions: {qs}\n")

    ctx = contextual_prepend(sample, "Sổ tay nhân viên VinUni 2024")
    print(f"Contextual: {ctx}\n")

    meta = extract_metadata(sample)
    print(f"Auto metadata: {meta}")
