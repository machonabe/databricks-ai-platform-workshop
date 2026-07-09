# Databricks AI 基盤ハンズオン（Free Edition 対応）

## SPARK 施策対応表

| Module | SPARK 施策 | 実行環境 |
| --- | --- | --- |
| 0 | ① 入口 | FE ノート |
| 1 | ① 即払出 / ② 標準環境 | FE ノート |
| 2 | ② 標準環境 / ⑦ AIドリブン | FE ノート |
| 3 | ⑥ RAG | FE ノート |
| 4 | ⑤ 安全な開発/本番 | FE ノート |
| 5A | ⑧ ガバナンス仕組み / ④ コスト | FE ノート |
| 5B | ④⑧ LLM コスト（Omnigent 0.4） | ローカル |
| 6 | ③ 寄り添い / 本番移行 | FE ノート |
| 7 | まとめ | ドキュメント |

---

## Module 0: イントロ・環境確認（15分）

- **目的**: AI 基盤の全体像、FE の位置関係、サーバレス即実行を体感
- **SPARK 施策**: ① 入口
- **実行環境**: Databricks Free Edition ノートブック
- **手順**: `notebooks/00_intro_env_check.py` を実行
- **FE 制約**: サーバレス専用。R/Scala 不可。
- **完了条件**: 先頭の環境確認クエリが即座に結果を返す

---

## Module 1: PoC 環境払出とデータ準備（35分）

- **目的**: 数コマンドでの環境払出とデータ準備
- **SPARK 施策**: ① 即払出 / ② 標準環境
- **実行環境**: FE ノート
- **手順**: `notebooks/01_poc_provisioning_and_data.py` を実行
- **FE 制約**: 外部ストレージ不可→マネージド volume/テーブル。DBFS 不可→ volume。
- **完了条件**: 自分の catalog に Delta テーブルが 1 つでき、SELECT できる

---

## Module 2: Genie Code で AI ドリブン開発（30分）

- **目的**: Genie Code で AI ドリブン開発、UC メタデータ駆動、skills/instructions/MCP でナレッジ注入
- **SPARK 施策**: ② 標準環境 / ⑦ AIドリブン
- **実行環境**: FE ノート
- **手順**: `notebooks/02_genie_code_ai_dev.py` を実行（手引き + 確認クエリ中心）
- **FE 制約**: 特になし（Genie Code は FE で利用可）
- **完了条件**: Genie Code で生成した SQL が Module 1 のテーブルに対して動く

---

## Module 3: RAG ・ Vector Search ・ Apps（50分 ★）

- **目的**: RAG を手組みで体験
- **SPARK 施策**: ⑥ RAG
- **実行環境**: FE ノート
- **手順**: `notebooks/03_rag_vector_search_app.py` を実行
- **FE 制約**:
  - Vector Search: 1 エンドポイント/1 ユニット、Direct Vector Access 不可 → Delta Sync インデックス + マネージド埋め込み
  - FMAPI: 一部モデル非対応
  - Apps: 最大 3、24h 停止
  - Agent Bricks KA は FE 非対応 → 手組み
- **完了条件**: 質問に文書由来の回答が返り、Apps の URL でチャットできる

---

## Module 4: Unity Catalog ガバナンス（45分 ★）

- **目的**: 粗→細のアクセス制御と in-place ガバナンス
- **SPARK 施策**: ⑤ 安全な開発/本番
- **実行環境**: FE ノート
- **手順**: `notebooks/04_unity_catalog_governance.py` を実行
- **FE 制約**: RLS/マスキング/ABAC はサーバレスで動作。SCIM/SSO/アカウントポリシーは FE 不可 → ワークスペース内グループ + GRANT で概念実演
- **完了条件**: 同一テーブルで権限によって見え方（マスクあり/なし等）が変わることを示せる

---

## Module 5A: AI Gateway ガバナンス（40分 ★）

- **目的**: AI Gateway でガバナンスを仕組み化
- **SPARK 施策**: ⑧ ガバナンス仕組み / ④ コスト
- **実行環境**: FE ノート
- **手順**: `notebooks/05_ai_gateway_governance.py` を実行
- **FE 制約**: 全社 `system.billing.usage` FinOps と Genie 予算は FE 不可 → スクショ/口頭
- **完了条件**: 使用状況ダッシュボードが表示される

---

## Module 5B: LLM コスト最適化（Omnigent 0.4・ローカル実行）

- **目的**: LLM 切り替え + インテリジェントルーティング + コスト比較
- **SPARK 施策**: ④⑧ LLM コスト
- **実行環境**: ローカル PC（FE はサーバレスの外部通信制限で外部 LLM API に到達不可）
- **前提**: `./setup.sh` 実行済み、`.env` 設定済み

### Step 1: 単一 LLM 動作確認

ファイル: `lab/step1_baseline.py`

```python
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
```

### Step 2: LLM 手動切り替え・コスト比較

ファイル: `lab/step2_switch.py`

```python
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
```

### Step 3: インテリジェントルーティング

ファイル: `lab/step3_routing.py`

```python
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
```

### Step 3b: コスト最優先チューニング

ファイル: `lab/step3b_costfirst.py`

```python
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
```

### Step 5a: Databricks FMAPI へルーティング（任意）

ファイル: `lab/step5a_databricks_route.py`

```python
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
```

### CSV アップロードとダッシュボード統合

実行後に生成される `omnigent_costs.csv` を UC volume にアップロードし、AI/BI ダッシュボードに統合する手順は `databricks/finops_dashboard_setup.md` を参照。

- **完了条件**: step3_routing.py 実行後に `omnigent_costs.csv` が生成され、コスト比較が確認できる

---

## Module 6: 常時相談窓口と本番移行（20分）

- **目的**: 常時相談窓口と本番移行の型
- **SPARK 施策**: ③ 寄り添い / 本番移行
- **実行環境**: FE ノート
- **手順**: `notebooks/06_support_and_prod_migration.py` を実行
- **FE 制約**: ジョブ同時 5、パイプライン各タイプ 1
- **完了条件**: dev→prod のカタログ分離とジョブ 1 本が動く

---

## Module 7: まとめ

### 8 施策 × Databricks 対応表（FE で触れた/見せた）

| SPARK 施策 | FE で実演 | FE で口頭/スクショ |
| --- | --- | --- |
| ① 入口 | ○ Module 0 | - |
| ② 標準環境 | ○ Module 1, 2 | - |
| ③ 寄り添い | ○ Module 6 | - |
| ④ コスト | ○ Module 5A, 5B | 全社 FinOps(口頭) |
| ⑤ 安全な開発/本番 | ○ Module 4 | SCIM/SSO(口頭) |
| ⑥ RAG | ○ Module 3 | Agent Bricks(口頭) |
| ⑦ AIドリブン | ○ Module 2 | - |
| ⑧ ガバナンス仕組み | ○ Module 5A | Genie予算(口頭) |

### 次ステップ（有償トライアル or 自社 WS）

- Agent Bricks（Knowledge Assistant / Supervisor Agent）でエンタープライズ RAG
- 外部データ接続（S3, ADLS, GCS）で実データレイクハウス構築
- 全社 `system.billing.usage` FinOps ダッシュボード + Genie 予算アラート
- SCIM/SSO 統合とアカウントレベルポリシー
- Provisioned Throughput で専用 GPU モデルサービング
- Declarative Automation Bundles (DABs) による CI/CD 自動化
