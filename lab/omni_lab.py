# lab/omni_lab.py — Omnigent ハンズオン共通ヘルパ
from omnigent.router import PROVIDERS


def cost_of(model: str, in_tok: int, out_tok: int):
    for p, cfg in PROVIDERS.items():
        if cfg["model"] == model:
            c = (in_tok / 1000) * cfg["cost_per_1k_in"] + (out_tok / 1000) * cfg["cost_per_1k_out"]
            return c, p.value
    return 0.0, model or "unknown"


async def run_once(router, prompt, *, system=None, task_type=None, provider_override=None):
    text, model, in_tok, out_tok = "", None, 0, 0
    async for chunk in router.stream(
        [{"role": "user", "content": prompt}],
        system=system, task_type=task_type, provider_override=provider_override,
    ):
        if chunk.content:
            text += chunk.content
            print(chunk.content, end="", flush=True)
        if chunk.model:
            model = chunk.model
        if chunk.input_tokens:
            in_tok = chunk.input_tokens
        if chunk.output_tokens:
            out_tok = chunk.output_tokens
    cost, provider = cost_of(model, in_tok, out_tok)
    print(f"\n--- provider={provider}  model={model}  in={in_tok} out={out_tok}  cost=${cost:.6f}")
    return {"text": text, "model": model, "provider": provider,
            "in_tok": in_tok, "out_tok": out_tok, "cost": cost}
