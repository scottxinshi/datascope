"""
verify_fix.py - Verify the Groq model-ID fix.

Groq decommissioned `llama-3.3-70b-versatile` on 2026-08-16, which broke every
agent in this project with a 404 `model_not_found`. The fix replaced eight
hardcoded model strings across four agents with a single env-configurable
`GROQ_MODEL`, so the next provider deprecation is a .env change rather than a
code change.

Usage (from the project root, using the project venv):
    .\.venv\Scripts\python.exe verify_fix.py
    .\.venv\Scripts\python.exe verify_fix.py --e2e   # also run a live agent call

Five checks, escalating from static analysis to a real API call. Each failure
reports the specific cause and what to do next.
"""
import os
import re
import sys

RESULTS = []

# Reasoning models (gpt-oss-*) spend tokens on internal reasoning before
# emitting any content, so a tiny budget can return an empty string on an
# otherwise successful call. Keep this generous enough to see real output.
SMOKE_TEST_MAX_TOKENS = 512

AGENTS = ["orchestrator.py", "sql_agent.py", "rag_agent.py", "web_agent.py"]
ROOT = os.path.dirname(os.path.abspath(__file__))
AGENT_DIR = os.path.join(ROOT, "agents")
DEPRECATED_MODEL = "llama-3.3-70b-versatile"


def check(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if detail:
        for line in str(detail).splitlines():
            print(f"        {line}")
    return ok


print("=" * 70)
print("datascope - model fix verification")
print("=" * 70)

# --- 1. Static: no live references to the decommissioned model ---------------
print("\n[1/5] Static scan: hardcoded model IDs")
leftovers = []
for fn in AGENTS:
    path = os.path.join(AGENT_DIR, fn)
    if not os.path.exists(path):
        leftovers.append(f"{fn}: file not found")
        continue
    for lineno, line in enumerate(open(path, encoding="utf-8"), 1):
        if DEPRECATED_MODEL in line and not line.strip().startswith("#"):
            leftovers.append(f"{fn}:{lineno}")
check(f"No live references to {DEPRECATED_MODEL} in agents/",
      not leftovers,
      "Found at: " + ", ".join(leftovers) if leftovers else "")

# --- 2. Static: every agent defines GROQ_MODEL -------------------------------
print("\n[2/5] Static scan: GROQ_MODEL definition")
problems = []
for fn in AGENTS:
    src = open(os.path.join(AGENT_DIR, fn), encoding="utf-8").read()
    defines = "GROQ_MODEL = os.getenv(" in src
    uses = bool(re.search(r"model\s*=\s*GROQ_MODEL", src))
    if uses and not defines:
        problems.append(f"{fn} (uses GROQ_MODEL but never defines it)")
    elif not defines:
        problems.append(f"{fn} (no definition)")
check("All four agents define GROQ_MODEL", not problems,
      "Problems: " + ", ".join(problems) if problems else "")

# --- 3. Environment ----------------------------------------------------------
print("\n[3/5] Environment")
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
check("GROQ_API_KEY is set", bool(api_key),
      f"Value: {api_key[:6]}...{api_key[-4:]}" if api_key
      else "Add GROQ_API_KEY to your .env file")

env_model = os.getenv("GROQ_MODEL")
print(f"        GROQ_MODEL in .env: {env_model or '(unset - falling back to the code default)'}")

# --- 4. Import and resolve ---------------------------------------------------
print("\n[4/5] Module import and model resolution")
sys.path.insert(0, ROOT)
resolved = {}
import_errors = []
for mod in ["sql_agent", "rag_agent", "web_agent", "orchestrator"]:
    try:
        module = __import__(f"agents.{mod}", fromlist=["GROQ_MODEL"])
        resolved[mod] = getattr(module, "GROQ_MODEL", None)
    except Exception as exc:
        import_errors.append(f"{mod}: {type(exc).__name__}: {exc}")

if import_errors:
    check("All four agent modules import cleanly", False, "\n".join(import_errors))
else:
    check("All four agent modules import cleanly", True,
          "\n".join(f"{k:<14} -> {v}" for k, v in resolved.items()))
    distinct = set(resolved.values())
    check("All four modules resolve the same model", len(distinct) == 1,
          f"Mismatch: {resolved}" if len(distinct) != 1 else "")

# --- 5. Live API call --------------------------------------------------------
print("\n[5/5] Live Groq call")
if not api_key:
    check("Groq API is reachable", False, "Skipped - no API key")
elif not resolved:
    check("Groq API is reachable", False, "Skipped - module import failed")
else:
    model = next(iter(resolved.values()))
    try:
        from groq import Groq
        response = Groq(api_key=api_key).chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
            max_tokens=SMOKE_TEST_MAX_TOKENS,
        )
        content = (response.choices[0].message.content or "").strip()
        usage = getattr(response, "usage", None)
        detail = f"Response: {content!r}"
        if usage:
            detail += f"\nTokens - prompt: {usage.prompt_tokens}, completion: {usage.completion_tokens}"
        if not content:
            detail += ("\nWARNING: the call succeeded but returned empty content. "
                       "Reasoning models can consume the whole token budget "
                       "internally. Raise SMOKE_TEST_MAX_TOKENS and retry.")
        check(f"Model {model} responds", bool(content), detail)
    except Exception as exc:
        message = str(exc)
        hint = ""
        if "model_not_found" in message or "does not exist" in message:
            hint = ("This model is unavailable too. Check "
                    "https://console.groq.com/docs/models for the current list, "
                    "then set GROQ_MODEL=<new-model> in .env. No code change needed.")
        elif "401" in message or "invalid_api_key" in message:
            hint = "The API key is invalid or expired. Regenerate it in the Groq console."
        elif "rate" in message.lower():
            hint = "Rate limited. Wait a moment and retry."
        check(f"Model {model} responds", False,
              message[:200] + ("\n" + hint if hint else ""))

# --- Optional end-to-end -----------------------------------------------------
if "--e2e" in sys.argv and api_key and resolved:
    print("\n[extra] End-to-end: sql_agent.ask()")
    try:
        from agents.sql_agent import ask, generate_sql
        sql = generate_sql("How many orders are there in total?",
                           "orders(orderID, customerID, employeeID, orderDate)")

        # A reasoning model may wrap its answer in fences or prefix it with
        # prose even when the prompt forbids both, which breaks the DuckDB call.
        upper = sql.upper()
        issues = []
        if "```" in sql:
            issues.append("wrapped in markdown fences")
        if "SELECT" not in upper:
            issues.append("no SELECT statement found")
        for phrase in ("HERE IS", "HERE'S", "THIS QUERY", "THE FOLLOWING", "SURE,"):
            if phrase in upper:
                issues.append(f"prose detected: {phrase!r}")
        check("generate_sql returns bare SQL (no markdown or prose)",
              not issues,
              (("Issues: " + "; ".join(issues) + "\n") if issues else "")
              + f"Generated:\n{sql}")

        answer = ask("How many orders are there in total?", silent=True)
        check("sql_agent.ask() returns an answer",
              bool(answer) and "couldn't run" not in answer,
              str(answer)[:300])
    except Exception as exc:
        check("sql_agent end-to-end", False, f"{type(exc).__name__}: {exc}")

# --- Summary -----------------------------------------------------------------
print("\n" + "=" * 70)
passed = sum(1 for _, ok, _ in RESULTS if ok)
total = len(RESULTS)
print(f"Result: {passed}/{total} checks passed")
if passed == total:
    print("\nVerification passed.")
    print("Next: restart the Claude desktop app so the MCP server reloads the code.")
    print("Python imports modules once at process start, so an unrestarted server")
    print("keeps serving the old module from memory.")
else:
    print("\nSome checks failed - see the detail under each one above.")
print("=" * 70)
