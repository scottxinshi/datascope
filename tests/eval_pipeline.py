import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from groq import Groq
from agents.orchestrator import decide_route
from agents.sql_agent import ask as sql_ask
from agents.rag_agent import answer_from_docs
from agents.web_agent import search_web

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ── LLM-as-Judge ─────────────────────────────────────────────────────────────
# Instead of exact string matching, we ask the LLM to judge whether
# the actual answer correctly addresses the expected answer.

def llm_judge(question, expected, actual):
    """Returns PASS or FAIL."""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": """You are an evaluation judge for an AI system.
Given a question, an expected answer keyword or phrase, and the actual answer produced by the system,
decide if the actual answer correctly addresses the expected answer.
Be lenient — if the actual answer contains the key information, it PASSES.
Reply with ONLY one word: PASS or FAIL."""
            },
            {
                "role": "user",
                "content": f"Question: {question}\nExpected: {expected}\nActual: {actual}"
            }
        ]
    )
    return response.choices[0].message.content.strip().upper()


# ── Main Eval Runner ──────────────────────────────────────────────────────────

def run_eval():
    dataset_path = os.path.join(BASE_DIR, "data", "golden_dataset.json")
    with open(dataset_path) as f:
        dataset = json.load(f)

    results = []

    print(f"\n{'='*70}")
    print(f"  DataScope Evaluation Pipeline")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")

    for item in dataset:
        question = item["question"]
        expected_route = item["expected_route"]
        expected_answer = item["expected_answer"]

        # Step 1 — Routing check
        actual_route = decide_route(question)
        route_correct = actual_route == expected_route

        # Step 2 — Get answer from the actual route
        if actual_route == "SQL":
            actual_answer = sql_ask(question, silent=True)
        elif actual_route == "RAG":
            actual_answer = answer_from_docs(question)
        elif actual_route == "WEB":
            actual_answer = search_web(question)
        else:
            actual_answer = "Out of scope"

        # Step 3 — Judge answer quality
        if expected_route == "NEITHER":
            # For NEITHER, just check if routing was correct
            judge_result = "PASS" if route_correct else "FAIL"
        elif not expected_answer:
            # No expected answer provided — skip answer judging
            judge_result = "SKIP"
        else:
            judge_result = llm_judge(question, expected_answer, actual_answer)

        results.append({
            "id": item["id"],
            "question": question,
            "expected_route": expected_route,
            "actual_route": actual_route,
            "route_correct": route_correct,
            "judge_result": judge_result,
            "actual_answer": actual_answer[:200]  # truncate for report
        })

        route_icon = "✅" if route_correct else "❌"
        answer_icon = "✅" if judge_result == "PASS" else ("⏭️" if judge_result == "SKIP" else "❌")
        print(f"[{item['id']:02d}] {route_icon} Route: {expected_route}→{actual_route} | {answer_icon} Answer: {judge_result}")
        print(f"      Q: {question[:65]}")
        print()

    # ── Summary ───────────────────────────────────────────────────────────────
    total = len(results)
    route_accuracy = sum(1 for r in results if r["route_correct"]) / total * 100
    judged = [r for r in results if r["judge_result"] != "SKIP"]
    answer_accuracy = sum(1 for r in judged if r["judge_result"] == "PASS") / len(judged) * 100 if judged else 0

    print(f"{'='*70}")
    print(f"  EVALUATION SUMMARY")
    print(f"{'='*70}")
    print(f"  Total questions : {total}")
    print(f"  Route accuracy  : {route_accuracy:.1f}%")
    print(f"  Answer accuracy : {answer_accuracy:.1f}%  (judged {len(judged)}/{total})")
    print(f"{'='*70}\n")

    # ── Save report ───────────────────────────────────────────────────────────
    report = {
        "timestamp": datetime.now().isoformat(),
        "total": total,
        "route_accuracy": route_accuracy,
        "answer_accuracy": answer_accuracy,
        "results": results
    }

    report_path = os.path.join(BASE_DIR, "data", "eval_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=4)

    print(f"  Report saved → data/eval_report.json\n")


if __name__ == "__main__":
    run_eval()
