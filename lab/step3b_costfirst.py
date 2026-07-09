# lab/step3b_costfirst.py — TASK_ROUTING を書き換えてコスト最優先にチューニング
import asyncio
from omnigent.router import LLMRouter, Provider, TaskType, TASK_ROUTING
from omni_lab import run_once
from log_cost import append_cost

TASK_ROUTING[TaskType.PLANNING]   = [Provider.DEEPSEEK, Provider.CLAUDE]
TASK_ROUTING[TaskType.ANALYSIS]   = [Provider.DEEPSEEK, Provider.OPENAI]
TASK_ROUTING[TaskType.REPORT]     = [Provider.OPENAI,   Provider.DEEPSEEK]
TASK_ROUTING[TaskType.TOOL_USE]   = [Provider.DEEPSEEK, Provider.OPENAI]
TASK_ROUTING[TaskType.REFLECTION] = [Provider.DEEPSEEK, Provider.LOCAL]

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
            append_cost({**r, "task": "costfirst:" + task.value})
            total += r["cost"]
    finally:
        await router.close()
    print(f"\n=== コスト最優先ルーティングの合計: ${total:.6f} ===")


asyncio.run(main())
