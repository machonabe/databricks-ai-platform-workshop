# Databricks notebook source
# MAGIC %md
# MAGIC # Module 5A: AI Gateway ガバナンス（40分 ★）
# MAGIC 
# MAGIC ## 目的
# MAGIC - AI Gateway でガバナンスを仕組み化
# MAGIC - レート制限 / ガードレール / 使用状況トラッキング / 推論テーブル
# MAGIC - AI/BI ダッシュボードで使用状況可視化
# MAGIC - サーバレス使用タグでコスト按分
# MAGIC 
# MAGIC ## FE 制約
# MAGIC - 推論テーブルはワークスペース内 UC で可 ✓
# MAGIC - **全社 `system.billing.usage` FinOps と Genie 予算は FE 不可** → スクショ/口頭で説明
# MAGIC 
# MAGIC ## Module 5B（Omnigent）について
# MAGIC - Module 5B は **ローカル PC** で Omnigent 0.4 を使った LLM コスト最適化を体験
# MAGIC - FE はサーバレスの外部通信制限により外部 LLM API に到達不可のため
# MAGIC - `lab/` ディレクトリのスクリプトをローカルで実行し、生成された CSV を UC Volume にアップロード

# COMMAND ----------

# ⯅ 自分の環境に合わせて変更
CATALOG = "<catalog>"
SCHEMA = "<schema>"
ENDPOINT_NAME = "databricks-meta-llama-3-3-70b-instruct"  # FE で利用可能な FMAPI エンドポイント

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: AI Gateway 設定の確認
# MAGIC 
# MAGIC Model Serving エンドポイントに AI Gateway を有効化します。
# MAGIC 
# MAGIC ### UI からの設定手順:
# MAGIC 1. **Serving** ページを開く
# MAGIC 2. 対象エンドポイントを選択
# MAGIC 3. **AI Gateway** タブで以下を有効化:
# MAGIC    - Rate Limits（レート制限）
# MAGIC    - Guardrails（PII 検出・安全性フィルタ）
# MAGIC    - Usage Tracking（使用状況トラッキング）
# MAGIC    - Inference Table（推論テーブル = ペイロードログ）

# COMMAND ----------

# SDK で AI Gateway 設定を確認
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# エンドポイント情報取得
try:
    endpoint = w.serving_endpoints.get(ENDPOINT_NAME)
    print(f"✅ エンドポイント: {endpoint.name}")
    print(f"   状態: {endpoint.state}")
    if hasattr(endpoint, 'ai_gateway') and endpoint.ai_gateway:
        gw = endpoint.ai_gateway
        print(f"   AI Gateway: 有効")
        if gw.rate_limits:
            print(f"   Rate Limits: {gw.rate_limits}")
        if gw.guardrails:
            print(f"   Guardrails: 有効")
        if gw.usage_tracking_config:
            print(f"   Usage Tracking: 有効")
        if gw.inference_table_config:
            print(f"   Inference Table: 有効")
    else:
        print("   AI Gateway: 未設定（UI から有効化してください）")
except Exception as e:
    print(f"⚠️ エンドポイント確認エラー: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: AI Gateway をプログラマティックに設定

# COMMAND ----------

from databricks.sdk.service.serving import AiGatewayConfig, AiGatewayRateLimit, AiGatewayUsageTrackingConfig, AiGatewayInferenceTableConfig, AiGatewayGuardrails, AiGatewayGuardrailParameters

try:
    w.serving_endpoints.put_ai_gateway(
        name=ENDPOINT_NAME,
        ai_gateway=AiGatewayConfig(
            rate_limits=[
                AiGatewayRateLimit(
                    calls=100,
                    renewal_period="minute",
                    key="user"
                )
            ],
            usage_tracking_config=AiGatewayUsageTrackingConfig(enabled=True),
            inference_table_config=AiGatewayInferenceTableConfig(
                catalog_name=CATALOG,
                schema_name=SCHEMA,
                enabled=True
            ),
            guardrails=AiGatewayGuardrails(
                input=AiGatewayGuardrailParameters(
                    pii={"behavior": "BLOCK"},
                    safety=True
                ),
                output=AiGatewayGuardrailParameters(
                    pii={"behavior": "BLOCK"},
                    safety=True
                )
            )
        )
    )
    print("✅ AI Gateway 設定完了")
except Exception as e:
    print(f"⚠️ AI Gateway 設定: {e}")
    print("   FMAPI エンドポイントは AI Gateway の一部設定が制限される場合があります。UI から設定してください。")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: テストリクエスト送信
# MAGIC 
# MAGIC 推論テーブルと使用状況トラッキングのデータを生成します。

# COMMAND ----------

# FMAPI にリクエスト送信
test_prompts = [
    "レイクハウスの利点を 3 つ教えてください。",
    "Delta Lake と Parquet の違いは？",
    "AI Gateway のガードレール機能を説明して。",
]

for prompt in test_prompts:
    response = w.serving_endpoints.query(
        name=ENDPOINT_NAME,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200
    )
    print(f"\nQ: {prompt}")
    print(f"A: {response.choices[0].message.content[:100]}...")
    print(f"   tokens: {response.usage.prompt_tokens} in / {response.usage.completion_tokens} out")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: 使用状況テーブルの確認
# MAGIC 
# MAGIC AI Gateway が有効だと、使用状況が UC テーブルに記録されます。
# MAGIC 
# MAGIC > 注: 推論テーブルは有効化後数分でデータが入り始めます。

# COMMAND ----------

# 推論テーブルの確認（有効化後数分後に実行）
try:
    display(spark.sql(f"""
      SELECT 
        date_format(timestamp_ms / 1000, 'yyyy-MM-dd HH:mm') AS time_bucket,
        status_code,
        COUNT(*) AS request_count,
        SUM(total_tokens) AS total_tokens
      FROM {CATALOG}.{SCHEMA}.`{ENDPOINT_NAME}_payload`
      GROUP BY 1, 2
      ORDER BY 1 DESC
      LIMIT 20
    """))
except Exception as e:
    print(f"ℹ️ 推論テーブル未作成またはデータ未到着: {e}")
    print("   AI Gateway を有効化して数分待ってから再実行してください")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: AI/BI ダッシュボード作成
# MAGIC 
# MAGIC 使用状況データを可視化するダッシュボードを作成します。
# MAGIC 
# MAGIC ### 手順:
# MAGIC 1. **SQL Editor** で以下のクエリを作成
# MAGIC 2. **新規ダッシュボード** を作成し、クエリ結果をタイルとして配置

# COMMAND ----------

# ダッシュボード用クエリ例
print(f"""
-- ダッシュボード用 SQL 例:

-- 1. 日別リクエスト数
SELECT 
  date_format(from_unixtime(timestamp_ms/1000), 'yyyy-MM-dd') AS date,
  COUNT(*) AS requests,
  SUM(total_tokens) AS tokens
FROM {CATALOG}.{SCHEMA}.`{ENDPOINT_NAME}_payload`
GROUP BY 1 ORDER BY 1;

-- 2. ユーザー別使用量
SELECT 
  client.user AS user_name,
  COUNT(*) AS request_count,
  SUM(total_tokens) AS total_tokens
FROM {CATALOG}.{SCHEMA}.`{ENDPOINT_NAME}_payload`
GROUP BY 1 ORDER BY 3 DESC;

-- 3. サーバレス使用タグでコスト按分
SELECT 
  custom_tags['team'] AS team,
  COUNT(*) AS requests,
  SUM(total_tokens) * 0.0001 AS est_cost_usd  -- 概算
-- FROM system.billing.usage  -- ← FE 不可（有償版のみ）
FROM {CATALOG}.{SCHEMA}.`{ENDPOINT_NAME}_payload`
GROUP BY 1;
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ## FE 不可の機能（口頭/スクショ説明）
# MAGIC 
# MAGIC ### 全社 FinOps (`system.billing.usage`)
# MAGIC - 有償版では `system.billing.usage` テーブルで全社のコストを可視化
# MAGIC - DBU 消費、ワークスペース別、SKU 別のブレークダウン
# MAGIC - Genie 予算: アラート設定でコスト超過を事前検知
# MAGIC 
# MAGIC ### サーバレス使用タグ
# MAGIC - ノートブックやジョブにタグを付与し、コストをチーム/プロジェクト別に按分
# MAGIC - `custom_tags` でエンドポイント利用もチーム別に追跡可能

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✅ 完了条件
# MAGIC 
# MAGIC - [x] AI Gateway の構成要素（レート制限/ガードレール/トラッキング/推論テーブル）を理解した
# MAGIC - [x] 使用状況ダッシュボードが表示される（または作成手順を理解）
# MAGIC - [x] FE 不可の FinOps 機能を認識した
