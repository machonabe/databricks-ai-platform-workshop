# Databricks notebook source
# MAGIC %md
# MAGIC # Module 3: RAG ・ Vector Search ・ Apps（50分 ★）
# MAGIC 
# MAGIC ## 目的
# MAGIC - RAG（Retrieval-Augmented Generation）を手組みで体験
# MAGIC - Vector Search を Delta Sync インデックス + マネージド埋め込みで作成
# MAGIC - FMAPI で回答生成
# MAGIC - Databricks Apps で簡易チャット UI を公開
# MAGIC 
# MAGIC ## FE 制約
# MAGIC - Vector Search: 1 エンドポイント / 1 ユニット、Direct Vector Access 不可
# MAGIC - → **Delta Sync インデックス + マネージド埋め込み**を使用
# MAGIC - FMAPI: 一部モデル非対応（利用可能なモデルを使用）
# MAGIC - Apps: 最大 3、24h で自動停止
# MAGIC - **Agent Bricks (Knowledge Assistant) は FE 非対応** → 手組みで実装
# MAGIC - 本番では Agent Bricks / 常設 Model Serving に置換

# COMMAND ----------

# ⯅ 自分の環境に合わせて変更
CATALOG = "<catalog>"
SCHEMA = "<schema>"
VS_ENDPOINT_NAME = "workshop_vs_endpoint"  # Vector Search エンドポイント名

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: 文書データの準備
# MAGIC 
# MAGIC RAG 用のナレッジベースとなる文書データを作成します。

# COMMAND ----------

# サンプル文書データ（EV・AI基盤関連の FAQ）
documents = [
    {"doc_id": "doc-001", "title": "EV バッテリー管理", "content": "EV のバッテリーマネジメントシステム（BMS）は、バッテリーの充電状態・温度・電圧をリアルタイムで監視します。過充電や過放電を防ぎ、バッテリー寿命を最大化します。温度管理は特に重要で、45℃以上では劣化が加速します。"},
    {"doc_id": "doc-002", "title": "レイクハウスアーキテクチャ", "content": "レイクハウスはデータウェアハウスとデータレイクを統合したアーキテクチャです。Delta Lake をストレージ層に使い、ACID トランザクション、スキーマエンフォースメント、タイムトラベルを提供します。BI・ML・AI を単一プラットフォームで実現します。"},
    {"doc_id": "doc-003", "title": "Unity Catalog の役割", "content": "Unity Catalog は Databricks の統合ガバナンスレイヤーです。データ、AI モデル、ファイルを一元管理し、行レベルセキュリティ、列マスキング、リネージ追跡を提供します。「データを動かさず in-place でガバナンス」が基本思想です。"},
    {"doc_id": "doc-004", "title": "AI Gateway", "content": "AI Gateway は Model Serving エンドポイントにガバナンス機能を追加します。レート制限、ガードレール（PII検出・安全性フィルタ）、使用状況トラッキング、推論テーブル（ペイロードログ）を提供します。"},
    {"doc_id": "doc-005", "title": "コスト最適化", "content": "LLM コスト最適化のアプローチ: (1) タスク種別で最適なモデルを選択（ルーティング）、(2) プロンプト最適化でトークン削減、(3) キャッシングで重複リクエストを削減、(4) AI Gateway で使用量可視化。"},
    {"doc_id": "doc-006", "title": "サーバレスコンピュート", "content": "サーバレスコンピュートはクラスタ起動待ちなしで即時実行されます。自動スケールにより使用量に応じた課金。Free Edition ではサーバレス専用で、Python と SQL のみサポートされます。"},
]

df_docs = spark.createDataFrame(documents)
df_docs.write.mode("overwrite").option("mergeSchema", "true").saveAsTable(f"{CATALOG}.{SCHEMA}.knowledge_base")

print(f"✅ 文書テーブル作成: {CATALOG}.{SCHEMA}.knowledge_base ({len(documents)} 件)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Vector Search エンドポイント作成
# MAGIC 
# MAGIC FE では 1 エンドポイント / 1 ユニットが上限です。

# COMMAND ----------

from databricks.vector_search.client import VectorSearchClient

vsc = VectorSearchClient()

# エンドポイント作成（既存ならスキップ）
try:
    vsc.create_endpoint(name=VS_ENDPOINT_NAME, endpoint_type="STANDARD")
    print(f"✅ Vector Search エンドポイント作成: {VS_ENDPOINT_NAME}")
except Exception as e:
    if "already exists" in str(e).lower() or "RESOURCE_ALREADY_EXISTS" in str(e):
        print(f"ℹ️ エンドポイントは既存: {VS_ENDPOINT_NAME}")
    else:
        raise e

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Delta Sync インデックス作成（マネージド埋め込み）
# MAGIC 
# MAGIC - **Delta Sync**: ソーステーブルと自動同期
# MAGIC - **マネージド埋め込み**: Databricks が埋め込みモデルを管理

# COMMAND ----------

INDEX_NAME = f"{CATALOG}.{SCHEMA}.knowledge_base_index"

try:
    index = vsc.create_delta_sync_index(
        endpoint_name=VS_ENDPOINT_NAME,
        index_name=INDEX_NAME,
        source_table_name=f"{CATALOG}.{SCHEMA}.knowledge_base",
        pipeline_type="TRIGGERED",
        primary_key="doc_id",
        embedding_source_column="content",
        embedding_model_endpoint_name="databricks-gte-large-en"  # FE で利用可能な埋め込みモデル
    )
    print(f"✅ インデックス作成開始: {INDEX_NAME}")
except Exception as e:
    if "already exists" in str(e).lower() or "RESOURCE_ALREADY_EXISTS" in str(e):
        print(f"ℹ️ インデックスは既存: {INDEX_NAME}")
    else:
        raise e

# COMMAND ----------

# インデックスの同期状態を確認
import time

print("インデックス同期中... (初回は数分かかります)")
for i in range(30):
    try:
        idx = vsc.get_index(VS_ENDPOINT_NAME, INDEX_NAME)
        status = idx.describe().get("status", {}).get("ready", False)
        if status:
            print(f"✅ インデックス準備完了!")
            break
    except Exception:
        pass
    time.sleep(10)
    print(f"  待機中... ({(i+1)*10}秒)")
else:
    print("⚠️ タイムアウト。Catalog Explorer でインデックス状態を確認してください。")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: 検索クエリ

# COMMAND ----------

# ベクトル検索
idx = vsc.get_index(VS_ENDPOINT_NAME, INDEX_NAME)

results = idx.similarity_search(
    query_text="バッテリーの温度管理について教えて",
    columns=["doc_id", "title", "content"],
    num_results=3
)

print("=== 検索結果 ===")
for row in results.get("result", {}).get("data_array", []):
    print(f"\n[{row[0]}] {row[1]}")
    print(f"  {row[2][:100]}...")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: FMAPI で回答生成（最小 RAG）

# COMMAND ----------

import requests
import json

def rag_answer(question: str) -> str:
    """Vector Search + FMAPI で簡易 RAG"""
    # 1. 検索
    idx = vsc.get_index(VS_ENDPOINT_NAME, INDEX_NAME)
    search_results = idx.similarity_search(
        query_text=question,
        columns=["title", "content"],
        num_results=2
    )
    
    # 2. コンテキスト構築
    context_parts = []
    for row in search_results.get("result", {}).get("data_array", []):
        context_parts.append(f"[文書: {row[0]}]\n{row[1]}")
    context = "\n\n".join(context_parts)
    
    # 3. FMAPI で回答生成
    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient()
    
    response = w.serving_endpoints.query(
        name="databricks-meta-llama-3-3-70b-instruct",  # FE で利用可能なモデル
        messages=[
            {"role": "system", "content": "以下のコンテキストに基づいて日本語で回答してください。コンテキストにない情報は「情報がありません」と答えてください。\n\nコンテキスト:\n" + context},
            {"role": "user", "content": question}
        ],
        max_tokens=500
    )
    
    return response.choices[0].message.content

# COMMAND ----------

# RAG 実行
answer = rag_answer("バッテリー管理で重要なことは？")
print("\n=== RAG 回答 ===")
print(answer)

# COMMAND ----------

# 別の質問も試す
answer2 = rag_answer("レイクハウスとは何ですか？")
print("\n=== RAG 回答 ===")
print(answer2)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Databricks Apps でチャット UI
# MAGIC 
# MAGIC ### 手順（手動）
# MAGIC 
# MAGIC 1. ワークスペースの **Compute > Apps** を開く
# MAGIC 2. **Create App** をクリック
# MAGIC 3. 以下の `app.py` をアップロード:
# MAGIC 
# MAGIC ```python
# MAGIC # app.py - 簡易 RAG チャット UI (Gradio)
# MAGIC import gradio as gr
# MAGIC from databricks.sdk import WorkspaceClient
# MAGIC from databricks.vector_search.client import VectorSearchClient
# MAGIC 
# MAGIC VS_ENDPOINT = "workshop_vs_endpoint"
# MAGIC INDEX_NAME = "<catalog>.<schema>.knowledge_base_index"  # 要置換
# MAGIC 
# MAGIC vsc = VectorSearchClient()
# MAGIC w = WorkspaceClient()
# MAGIC 
# MAGIC def chat(message, history):
# MAGIC     idx = vsc.get_index(VS_ENDPOINT, INDEX_NAME)
# MAGIC     results = idx.similarity_search(query_text=message, columns=["title","content"], num_results=2)
# MAGIC     context = "\n".join([r[1] for r in results.get("result",{}).get("data_array",[])])
# MAGIC     resp = w.serving_endpoints.query(
# MAGIC         name="databricks-meta-llama-3-3-70b-instruct",
# MAGIC         messages=[{"role":"system","content":f"コンテキスト:\n{context}"},{"role":"user","content":message}],
# MAGIC         max_tokens=500
# MAGIC     )
# MAGIC     return resp.choices[0].message.content
# MAGIC 
# MAGIC gr.ChatInterface(chat, title="RAG Chat").launch()
# MAGIC ```
# MAGIC 
# MAGIC 4. `app.yaml` に以下を設定:
# MAGIC ```yaml
# MAGIC command: ["python", "app.py"]
# MAGIC env:
# MAGIC   - name: DATABRICKS_HOST
# MAGIC     value: "{{DATABRICKS_HOST}}"
# MAGIC ```
# MAGIC 
# MAGIC ### FE 制約の注意
# MAGIC - Apps は最大 3 つまで
# MAGIC - 起動から 24 時間で自動停止
# MAGIC - 本番では常設 Model Serving エンドポイント + Agent Bricks に置換

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✅ 完了条件
# MAGIC 
# MAGIC - [x] 質問に文書由来の回答が返る
# MAGIC - [x] Vector Search インデックスが作成・同期された
# MAGIC - [x] Apps の URL でチャットできる（Apps デプロイ後）
# MAGIC 
# MAGIC ### 本番へのステップ
# MAGIC - Agent Bricks (Knowledge Assistant) でエンタープライズ RAG
# MAGIC - 常設 Model Serving で GPU 付きカスタムモデル
# MAGIC - Provisioned Throughput で安定スループット
