# lab/step3_routing.py — インテリジェントルーティング（タスク種別ベースの自動選択）
import asyncio
from omnigent.router import LLMRouter, Provider, TaskType
from omni_lab import run_once
from log_cost import append_cost

TASKS = {
    TaskType.PLANNING:   "データパイプラインをレイクハウスへ移行する 3 ステップの計画を書いて。",
    TaskType.TOOL_USE:   "関数 get_weather(city) がある。東京について呼び出す形を示して。",
    TaskType.REFLECTION: "前の回答は十分だった? 理由を 1 つ添えて yes/no で。",
    TaskType.REPORT:     "コスト最適化プロジェクトのエグゼクティブサマリを 2 文で。",
}


async def main():
    router = LLMRouter(primary=Provider.DEEPSEEK, fallback=Provider.CLAUDE)
    total = 0.0
    try:
        for task, prompt in TASKS.items():
            print(f"\n================  task = {task.value}  ================")
            r = await run_once(router, prompt, task_type=task)
            append_cost({**r, "task": task.value})
            total += r["cost"]
    finally:
        await router.close()
    print(f"\n=== この実行の合計コスト: ${total:.6f} ===")


asyncio.run(main())
