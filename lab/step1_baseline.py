# lab/step1_baseline.py — 単一 LLM で動作確認
import asyncio
from omnigent.router import LLMRouter, Provider
from omni_lab import run_once


async def main():
    router = LLMRouter(primary=Provider.DEEPSEEK, fallback=None)
    try:
        await run_once(router, "EV のバッテリー BMS の役割を 3 文で説明して。")
    finally:
        await router.close()


asyncio.run(main())
