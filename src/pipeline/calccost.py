"""src.pipeline.calccost.py - provides cost from token usage based on tiktoken.

RATES are $ per 1,000,000 tokens as (input_rate, output_rate).
VERIFY AGAINST TODAY'S PRICING before trusting these numbers.
"""

from .settings import Settings, RunSummary

_settings_for_import = Settings()

def calc_cost_in_usd(model: str, prompt_tokens: int, completion_tokens: int):
    price = _settings_for_import.PRICING
    model_pricing = price.get(model)
    input_cost = (prompt_tokens / 1_000_000) * model_pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * model_pricing["output"]

    real_cost_in_usd = input_cost + output_cost
    return real_cost_in_usd