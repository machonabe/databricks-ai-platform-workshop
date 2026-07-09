# lab/step5a_databricks_route.py（任意）— Databricks FMAPI へルーティング（ローカルから実行）
import os, asyncio
from omnigent.router import PROVIDERS, Provider, LLMRouter
from omni_lab import run_once

PROVIDERS[Provider.OPENAI] = {
    "base_url": f"{os.environ['DATABRICKS_HOST']}/serving-endpoints",
    "model": "databricks-meta-llama-3-3-70b-instruct",  # 自環境で提供中のエンドポイント名に置換
    "api_key_env": "DATABRICKS_TOKEN",
    "cost_per_1k_in": 0.0,
    "cost_per_1k_out": 0.0,
}


async def main():
    router = LLMRouter(primary=Provider.OPENAI, fallback=None)
    try:
        await run_once(router, "レイクハウスの利点を 3 点、簡潔に。", provider_override=Provider.OPENAI)
    finally:
        await router.close()


asyncio.run(main())
