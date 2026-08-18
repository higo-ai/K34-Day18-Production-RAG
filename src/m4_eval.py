from __future__ import annotations

"""Module 4: RAGAS Evaluation — 4 metrics + failure analysis."""

import os, sys, json
from dataclasses import dataclass

# Mock missing VertexAI module in langchain_community to satisfy Ragas import
import types
_vx = types.ModuleType("langchain_community.chat_models.vertexai")
_vx.ChatVertexAI = type("ChatVertexAI", (object,), {})
sys.modules["langchain_community.chat_models.vertexai"] = _vx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TEST_SET_PATH


@dataclass
class EvalResult:
    question: str
    answer: str
    contexts: list[str]
    ground_truth: str
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float


def load_test_set(path: str = TEST_SET_PATH) -> list[dict]:
    """Load test set from JSON. (Đã implement sẵn)"""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_ragas_llm_and_embeddings():
    import os
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings

    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()

    # 1. Ưu tiên OpenAI
    if openai_key:
        llm = ChatOpenAI(model="gpt-4o-mini", api_key=openai_key)
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small", api_key=openai_key)
        return llm, embeddings
    # 2. Dự phòng Gemini
    elif gemini_key:
        from langchain_core.rate_limiters import InMemoryRateLimiter
        # Giới hạn 1 request mỗi 4.5 giây để tránh lỗi 15 RPM
        rate_limiter = InMemoryRateLimiter(requests_per_second=0.22, max_bucket_size=1)
        
        llm = ChatOpenAI(
            model="gemini-3.5-flash-lite",
            api_key=gemini_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            model_kwargs={"response_format": {"type": "json_object"}},
            rate_limiter=rate_limiter,
            timeout=600
        )
        # Sử dụng Local HuggingFace Embeddings để tránh lỗi 501 từ Google và tiết kiệm API requests
        from langchain_community.embeddings import HuggingFaceEmbeddings
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        return llm, embeddings
    else:
        return None, None


def evaluate_ragas(questions: list[str], answers: list[str],
                   contexts: list[list[str]], ground_truths: list[str]) -> dict:
    """Run RAGAS evaluation."""
    try:
        from ragas import evaluate
        from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
        from datasets import Dataset

        dataset = Dataset.from_dict({
            "question": questions,
            "answer": answers,
            "contexts": contexts,
            "ground_truth": ground_truths,
        })

        llm, embeddings = get_ragas_llm_and_embeddings()

        metrics_list = [faithfulness, answer_relevancy, context_precision, context_recall]
        if llm:
            for metric in metrics_list:
                metric.llm = llm
        if embeddings:
            for metric in metrics_list:
                if hasattr(metric, "embeddings"):
                    metric.embeddings = embeddings

        kwargs = {
            "dataset": dataset,
            "metrics": metrics_list
        }
        if llm and embeddings:
            kwargs["llm"] = llm
            kwargs["embeddings"] = embeddings
            
            import os
            openai_key = os.getenv("OPENAI_API_KEY", "").strip()
            gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
            
            # Chỉ kích hoạt RunConfig an toàn (max_workers=1) nếu chạy dự phòng Gemini (không có OpenAI key)
            if not openai_key and gemini_key:
                from ragas.run_config import RunConfig
                kwargs["run_config"] = RunConfig(max_workers=1, max_retries=10, timeout=600)

        result = evaluate(**kwargs)
        df = result.to_pandas()

        per_question = []
        for _, row in df.iterrows():
            # Tự động hỗ trợ cả schema mới (Ragas 0.4.0+) và schema cũ
            q = row.get("user_input", row.get("question", ""))
            a = row.get("response", row.get("answer", ""))
            c = row.get("retrieved_contexts", row.get("contexts", []))
            gt = row.get("reference", row.get("ground_truth", ""))
            
            per_question.append(EvalResult(
                question=q,
                answer=a,
                contexts=c,
                ground_truth=gt,
                faithfulness=float(row.get("faithfulness", 0.0)),
                answer_relevancy=float(row.get("answer_relevancy", 0.0)),
                context_precision=float(row.get("context_precision", 0.0)),
                context_recall=float(row.get("context_recall", 0.0))
            ))

        # Tính điểm trung bình an toàn từ DataFrame để tương thích 100% với mọi phiên bản Ragas
        faithfulness_score = float(df["faithfulness"].mean()) if "faithfulness" in df.columns else 0.0
        answer_relevancy_score = float(df["answer_relevancy"].mean()) if "answer_relevancy" in df.columns else 0.0
        context_precision_score = float(df["context_precision"].mean()) if "context_precision" in df.columns else 0.0
        context_recall_score = float(df["context_recall"].mean()) if "context_recall" in df.columns else 0.0

        return {
            "faithfulness": faithfulness_score,
            "answer_relevancy": answer_relevancy_score,
            "context_precision": context_precision_score,
            "context_recall": context_recall_score,
            "per_question": per_question
        }
    except Exception as e:
        print(f"  ⚠️  RAGAS evaluation failed: {e}")
        return {
            "faithfulness": 0.0,
            "answer_relevancy": 0.0,
            "context_precision": 0.0,
            "context_recall": 0.0,
            "per_question": []
        }


def failure_analysis(eval_results: list[EvalResult], bottom_n: int = 10) -> list[dict]:
    """Analyze bottom-N worst questions using Diagnostic Tree."""
    diagnostic_tree = {
        "faithfulness": ("LLM hallucinating", "Tighten prompt, lower temperature"),
        "context_recall": ("Missing relevant chunks", "Improve chunking or add BM25"),
        "context_precision": ("Too many irrelevant chunks", "Add reranking or metadata filter"),
        "answer_relevancy": ("Answer doesn't match question", "Improve prompt template"),
    }
    analyzed = []
    for r in eval_results:
        avg = (r.faithfulness + r.answer_relevancy + r.context_precision + r.context_recall) / 4.0
        metrics = {
            "faithfulness": r.faithfulness,
            "answer_relevancy": r.answer_relevancy,
            "context_precision": r.context_precision,
            "context_recall": r.context_recall
        }
        worst_metric = min(metrics, key=metrics.get)
        worst_score = metrics[worst_metric]
        diagnosis, suggested_fix = diagnostic_tree[worst_metric]
        analyzed.append({
            "question": r.question,
            "worst_metric": worst_metric,
            "score": float(worst_score),
            "diagnosis": diagnosis,
            "suggested_fix": suggested_fix,
            "avg_score": avg
        })
    sorted_failures = sorted(analyzed, key=lambda x: x["avg_score"])
    for f in sorted_failures:
        f.pop("avg_score")
    return sorted_failures[:bottom_n]


def save_report(results: dict, failures: list[dict], path: str = "ragas_report.json"):
    """Save evaluation report to JSON. (Đã implement sẵn)"""
    report = {
        "aggregate": {k: v for k, v in results.items() if k != "per_question"},
        "num_questions": len(results.get("per_question", [])),
        "failures": failures,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Report saved to {path}")


if __name__ == "__main__":
    test_set = load_test_set()
    print(f"Loaded {len(test_set)} test questions")
    print("Run pipeline.py first to generate answers, then call evaluate_ragas().")
