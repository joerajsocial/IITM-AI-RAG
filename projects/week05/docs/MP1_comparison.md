# Project - Evaluation & Analysis Report

## 1. Winning Strategy Analysis

Based on the evaluation, the **`structured`** strategy is the winner:

* While `Cost & parse rate` remains samme for all the prompt types, on `accuracy, judge score and latency` **structured prompt* won with highest score of **4.0, 3.8 & 1.389s respectively**.
* Second place is for **few shot** learning, with **3.8, 3.625 & 1.5s** as `accuracy, judge score and latency respectively`.

---

## 2. What surprised me?

* **Structured Output Dominance:** It was surprising that `structured` outpaced `cot` (Chain-of-Thought) across **all** quality and performance metrics (Accuracy, Judge Score, and Latency) while incurring zero added financial cost.

* I was expecting **Chain-of-Thought (CoT) Performance & Latency:** `cot` to win, but it yielded the highest latency (1.583s) and lower accuracy (3.5) than `few_shot` (3.7) and `structured` (4.0). Usually, explicit chain of thought improves reasoning, accuracy, but here the extra tokens generated increased latency without surpassing structured formatting.

---

## 3. Capstone domain strategy

For my capstone domain, I would try **`structured`** strategy first. It delivered the top performance across both accuracy, judge evaluation with fastest response time (1.336s) and same cost. Also, additionally, enforcing structured schemas (e.g., JSON/Pydantic models) eliminates parsing errors and smoother integration.

---

## 4. What would I try

If given more time, I would explore the following avenues:

1. **Optimize Prompting:** I would refine and fine-tune the prompt data to check if the cost and latency can be lowered.
2. **Different model comparison:** I would test this across alternative models Claude 3.5 Sonnet, OpenAI GPT-4o, or Llama 3 models, to check the performance & results.
3. **Dataset Expansion:** I would expand both the input and evaluation dataset with complex snippets to test which strategy wins, whether the current win is correct or not.

---


=================
## Code snippet of src.pipeline.pipeline => ask_llm()

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


async def ask_llm(q: Question, fail_rate: float = 0.0) -> Answer:
    """One LLM call. Branches on Settings.use_fake."""
    #print(f"ask_llm called with question: {q}")
    if _settings_for_import.use_fake:
        ans = await fake_ask_llm(q, fail_rate=fail_rate)
    else:
        resp = await _client.chat.completions.create(
            model=_settings_for_import.model,
            messages=[{"role": "user", "content": q.text}],   # no "return JSON" needed
            tools=[ANSWER_TOOL],
            tool_choice={"type": "function", "function": {"name": "answer_question"}},
            temperature=_settings_for_import.user_temperature,     # randomness, 0.0 (deterministic-ish) .. 2.0 (wild)
            #n=_settings_for_import.no_of_choices,                 # how many separate completions to return in `choices`
            seed=_settings_for_import.user_seed,             # best-effort reproducibility (pair with temperature=0)
        )
        print(f"Raw structure: {resp.choices[0]}")
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