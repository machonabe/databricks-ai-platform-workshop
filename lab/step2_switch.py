# lab/step2_switch.py — LLM を手動で切り替え、同一プロンプトのコストを比較
import os, asyncio
from omnigent.router import LLMRouter, Provider, PROVIDERS
from omni_lab import run_once

PROMPT = "クラウド GPU を過剰にプロビジョニングするリスクを 4 つ、箇条書きで。"


def has_key(p):
    env = PROVIDERS[p]["api_key_env"]
    return bool(env) and bool(os.environ.get(env))


PROVIDERS_TO_TRY = [p for p in [Provider.DEEPSEEK, Provider.OPENAI, Provider.CLAUDE] if has_key(p)]


async def main():
    results = []
    for prov in PROVIDERS_TO_TRY:
        print(f"\n================  LLM = {prov.value}  ================")
        router = LLMRouter(primary=prov, fallback=None)
        try:
            results.append(await run_once(router, PROMPT, provider_override=prov))
        finally:
            await router.close()
    print("\n\n=== 同一プロンプトのコスト比較 ===")
    for r in results:
        print(f"{r['provider']:>10}: ${r['cost']:.6f}   ({r['in_tok']} in / {r['out_tok']} out)")


asyncio.run(main())
