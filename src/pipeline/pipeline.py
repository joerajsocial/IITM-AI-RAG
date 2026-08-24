"""Async batch pipeline — COMPLETED REFERENCE for Week 2.

Demonstrates the full Week 2 architecture:
  - Typed Settings (Pydantic v2) with field constraints
  - JSON logging to logs/pipeline.log via logging_config
  - CSV-driven input via load_questions
  - Async batched parallel calls (chunks of `batch_size`) with retry + backoff
  - RunSummary aggregation per execution
  - results.json output (summary + answers)
  - SQLite persistence via store (deferred import)
  - Switchable fake/real LLM via Settings.use_fake

Run with:
    python -m src.pipeline.pipeline
"""
from __future__ import annotations
import asyncio
import csv
import json
import time
from pathlib import Path

from .logging_config import get_logger
from .settings import Settings, RunSummary

#==================================================
# W4 included to calculate cost
#==================================================
from .calccost import calc_cost_in_usd


# ─────────────────────────────────────────────────────────────────────────────
# Logger — shared across the package
# ─────────────────────────────────────────────────────────────────────────────
log = get_logger()

#==============================================================================
# ─────────────────────────────────────────────────────────────────────────────
# Structured-output tool schema (W4) — the shape we force the model to fill
# ─────────────────────────────────────────────────────────────────────────────

ANSWER_TOOL = {
    "type": "function",
    "function": {
        "name": "answer_question",
        "description": "Return a structured answer with content, confidence, sources, prompt_tokens, completion_tokens",
        "parameters": {
            "type": "object",
            "properties": {
                "content":    {"type": "string"},
                "confidence": {"type": "number"},
                "sources":    {"type": "array", "items": {"type": "string"}},
                "prompt_tokens": {"type": "number"},
                "completion_tokens": {"type": "number"}
            },
            "required": ["content", "confidence", "sources", "prompt_tokens", "completion_tokens"],
        },
    },
}

#==============================================================================

CLARIFY_TOOL = {
    "type": "function",
    "function": {
        "name": "ask_for_clarification",
        "description": "Use when the question is too vague to answer well. Also return a structured answer with clarification, prompt_tokens, completion_tokens",
        "parameters": {
            "type": "object",
            "properties": {"question_back": {"type": "string"}, 
                            "prompt_tokens": {"type": "number"},
                            "completion_tokens": {"type": "number"}
                            },
            "required": ["question_back", "prompt_tokens", "completion_tokens"],
        },
    },
}

#==============================================================================


# ─────────────────────────────────────────────────────────────────────────────
# LLM client setup — branches on Settings.use_fake at module-load time
# ─────────────────────────────────────────────────────────────────────────────
_settings_for_import = Settings()

if _settings_for_import.use_fake:
    from .fake_llm import Question, Answer, fake_ask_llm, FakeLLMError
else:
    from dotenv import load_dotenv
    from openai import AsyncOpenAI
    from pydantic import BaseModel

    load_dotenv()
    _client = AsyncOpenAI()

    class Question(BaseModel):
        text: str

    class Answer(BaseModel):
        question: str
        text:     str
        cost_usd: float
        retries:  int = 0
        confidence: float = 1.0
        sources: list[str] = []
        prompt_tokens: int
        completion_tokens: int


# ─────────────────────────────────────────────────────────────────────────────
# CSV loader
# ─────────────────────────────────────────────────────────────────────────────
def load_questions(path: str | Path = "data/questions.csv") -> list[Question]:
    """Read questions from a CSV with a `text` column."""
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [Question(text=row["text"]) for row in rows if row.get("text")]


# ─────────────────────────────────────────────────────────────────────────────
# Core LLM calls
# ─────────────────────────────────────────────────────────────────────────────
async def ask_llm(q: Question, fail_rate: float = 0.0) -> Answer:
    """One LLM call. Branches on Settings.use_fake."""
    #print(f"ask_llm called with question: {q}")
    if _settings_for_import.use_fake:
        ans = await fake_ask_llm(q, fail_rate=fail_rate)
    else:
        #resp = await _client.chat.completions.create(
        #    model=_settings_for_import.model,
        #    messages=[{"role": "user", "content": q.text}],
        #)
        #ans = Answer(
        #    question=q.text,
        #    text=resp.choices[0].message.content,
        #    cost_usd=0.0001,                  # real cost-from-usage lands in W25
        #)
        resp = await _client.chat.completions.create(
            model=_settings_for_import.model,
            messages=[{"role": "user", "content": q.text}],   # no "return JSON" needed
            #tools=[ANSWER_TOOL, CLARIFY_TOOL],
            tools=[ANSWER_TOOL],
            tool_choice={"type": "function", "function": {"name": "answer_question"}},
            temperature=_settings_for_import.user_temperature,     # randomness, 0.0 (deterministic-ish) .. 2.0 (wild)
            #n=_settings_for_import.no_of_choices,                 # how many separate completions to return in `choices`
            seed=_settings_for_import.user_seed,             # best-effort reproducibility (pair with temperature=0)
            ##stop=["\n\n"],       # stop generating if any of these strings appears
            ##max_tokens=50,       # HARD cap on OUTPUT tokens (see max_completion_tokens note)
            ##top_p=1.0,           # nucleus sampling: keep tokens up to this cumulative prob
        )
        print(f"Raw structure: {resp.choices[0]}")
        #print(f"Raw structure: {resp.choices[0].message.content}")
        #print(f"Raw structure - tool calls: {resp.choices[0].message.tool_calls[0]}")
        #print(f"Raw structure - Function: {resp.choices[0].message.tool_calls[0].function}")
        #args = json.loads(resp.choices[0].message.tool_calls[0].function.arguments)
        args = json.loads(resp.choices[0].message.tool_calls[0].function.arguments)

        print("structured args:", args)
        print("confidence (from the MODEL):", args["confidence"])
        ans = Answer(
        question=q.text,
        text=args["content"],
        cost_usd=calc_cost_in_usd(_settings_for_import.model, resp.usage.prompt_tokens, resp.usage.completion_tokens),                  # Based on tiktoken should change
        confidence = args["confidence"],
        sources = args.get("sources", []),
        prompt_tokens = resp.usage.prompt_tokens,
        completion_tokens = resp.usage.completion_tokens,
        )

        log.info(f"asked: {q.text[:40]}")
        log.info(f"Answer: {ans}")
        
    return ans


async def ask_llm_with_retry(
    q: Question, tries: int = 3, fail_rate: float = 0.0
) -> Answer:
    """Retry up to `tries` times. Wait 1 s, 2 s, 4 s between attempts.

    Re-raises the last exception if all attempts fail (no silent failures).
    """
    for attempt in range(tries):
        try:
            ans = await ask_llm(q, fail_rate=fail_rate)
            ans.retries = attempt
            return ans
        except Exception as exc:
            if attempt == tries - 1:
                raise
            log.warning(f"retry {attempt + 1} for: {q.text[:40]} ({exc})")
            await asyncio.sleep(2 ** attempt)
    raise RuntimeError("unreachable")          # pragma: no cover


# ─────────────────────────────────────────────────────────────────────────────
# Batch runners
# ─────────────────────────────────────────────────────────────────────────────
async def run_batch(
    questions: list[Question], fail_rate: float = 0.0
) -> list[Answer]:
    """Fire every question in parallel via one big asyncio.gather (no batching)."""
    tasks = [ask_llm_with_retry(q, fail_rate=fail_rate) for q in questions]
    return await asyncio.gather(*tasks)


async def run_in_batches(
    questions: list[Question],
    batch_size: int = 5,
    fail_rate: float = 0.0,
) -> list[Answer]:
    """Fire questions in chunks of `batch_size`, with a 100 ms pause between batches."""
    out: list[Answer] = []
    for i in range(0, len(questions), batch_size):
        chunk = questions[i : i + batch_size]
        log.info(f"batch {i // batch_size + 1}: {len(chunk)} questions")
        batch_answers = await asyncio.gather(
            *(ask_llm_with_retry(q, fail_rate=fail_rate) for q in chunk)
        )
        out.extend(batch_answers)
        await asyncio.sleep(0.1)              # gentle pace between batches
        break
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Run summariser
# ─────────────────────────────────────────────────────────────────────────────
def summarise_run(
    answers: list[Answer],
    *,
    started_at: float,
    elapsed: float,
    fail_rate: float,
    use_fake: bool,
) -> RunSummary:
    """Roll a list of Answers + wall-clock data into a RunSummary."""
    return RunSummary(
        started_at      = started_at,
        elapsed_seconds = elapsed,
        n_questions     = len(answers),
        n_succeeded     = len(answers),
        n_retries_total = sum(a.retries  for a in answers),
        total_cost_usd  = sum(a.cost_usd for a in answers),
        fail_rate       = fail_rate,
        use_fake        = use_fake,
    )

# ─────────────────────────────────────────────────────────────────────────────
# Real streaming (W4) — fake path simulates; real path streams delta.content
# ─────────────────────────────────────────────────────────────────────────────
async def stream_answer(question_text: str):
    """Async generator yielding the answer in pieces."""
    if _settings_for_import.use_fake:                        # FLOW: simulate from the fake answer
        ans = await ask_llm(Question(text=question_text))
        for word in ans.text.split(" "):
            yield word + " "
            await asyncio.sleep(0.05)
        return
    stream = await _client.chat.completions.create(
            model=_settings_for_import.model,
            messages=[{"role": "user", "content": question_text}],   # no "return JSON" needed
            #tools=[ANSWER_TOOL, CLARIFY_TOOL],
            tools=[ANSWER_TOOL],
            tool_choice={"type": "function", "function": {"name": "answer_question"}},
            temperature=_settings_for_import.user_temperature,     # randomness, 0.0 (deterministic-ish) .. 2.0 (wild)
            #n=_settings_for_import.no_of_choices,                 # how many separate completions to return in `choices`
            seed=_settings_for_import.user_seed,             # best-effort reproducibility (pair with temperature=0)
            stream=True,  # Required for streaming chunks
            stream_options={"include_usage": True},  # Enables usage tracking in stream
        )

    accumulated_args = ""
    prompt_tokens = 0
    completion_tokens = 0

    async for chunk in stream:
        if chunk.usage:        # 🟢 Captures usage on the final chunk
            prompt_tokens       = chunk.usage.prompt_tokens
            completion_tokens   = chunk.usage.completion_tokens

        if not chunk.choices:
            continue
        if chunk.choices[0].delta.tool_calls:
            arg_chunk = chunk.choices[0].delta.tool_calls[0].function.arguments
            accumulated_args += arg_chunk
            yield arg_chunk

    log.info("Finished yields..")
    try:
        args = json.loads(accumulated_args)
    except json.JSONDecodeError:
        log.error(f"Failed to parse JSON tool arguments: {accumulated_args}")
        args = {}

    # Construct the Answer object
    ans = Answer(
        question=question_text,
        text=args.get("content", ""),
        cost_usd=calc_cost_in_usd(_settings_for_import.model, prompt_tokens, completion_tokens),
        confidence=args.get("confidence", 0.0),
        sources=args.get("sources", []),
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )

    log.info(f"asked: {question_text[:40]}")
    log.info(f"Answer: {ans}")


# ─────────────────────────────────────────────────────────────────────────────
# Entrypoint
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    settings = Settings()
    log.info(f"config: {settings.model_dump(mode='json')}")

    questions = load_questions(settings.questions_csv)
    log.info(f"loaded {len(questions)} questions")

    started = time.time()
    answers = asyncio.run(
        run_in_batches(
            questions,
            batch_size=settings.batch_size,
            fail_rate=settings.fail_rate,
        )
    )
    elapsed = time.time() - started

    summary = summarise_run(
        answers,
        started_at = started,
        elapsed    = elapsed,
        fail_rate  = settings.fail_rate,
        use_fake   = settings.use_fake,
    )
    log.info(f"summary: {summary.model_dump_json()}")

    # Write the structured artefact
    settings.results_json.write_text(
        json.dumps({
            "summary": summary.model_dump(mode="json"),
            "answers": [a.model_dump() for a in answers],
        }, indent=2),
        encoding="utf-8",
    )
    print(f"wrote {len(answers)} answers to {settings.results_json} in {elapsed:.2f}s")

    # SQLite persistence
    # Deferred import: store.py imports Answer from this module; top-level import
    # would cause a circular import.
    from .store import connect, write_run, write_answers
    with connect(settings.results_db) as con:
        run_id = write_run(con, summary)
        n      = write_answers(con, run_id, answers, model=settings.model)
    log.info(f"persisted run {run_id} with {n} answers to {settings.results_db}")
