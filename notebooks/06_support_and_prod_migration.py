# Databricks notebook source
# MAGIC %md
# MAGIC # Module 6: 常時相談窓口と本番移行（20分）
# MAGIC 
# MAGIC ## 目的
# MAGIC - dev/staging/prod のカタログ分離
# MAGIC - 簡単な Job / Lakeflow パイプライン
# MAGIC - Declarative Automation Bundles (DABs) での移行の型
# MAGIC - SDLC/AI チェックシート
# MAGIC 
# MAGIC ## FE 制約
# MAGIC - ジョブ同時 5
# MAGIC - Lakeflow パイプライン各タイプ 1

# COMMAND ----------

# MAGIC %run ./config

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: dev / staging / prod カタログ分離
# MAGIC 
# MAGIC 本番運用では環境ごとにカタログを分離します。

# COMMAND ----------

# 環境分離の実演
for env in ["dev", "staging", "prod"]:
    catalog_name = f"{CATALOG}_{env}"
    try:
        spark.sql(f"CREATE CATALOG IF NOT EXISTS {catalog_name}")
        spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog_name}.{SCHEMA}")
        print(f"✅ {catalog_name}.{SCHEMA} 作成完了")
    except Exception as e:
        print(f"⚠️ {catalog_name}: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 環境分離の意義
# MAGIC 
# MAGIC ```
# MAGIC dev        →  開発者が自由に実験
# MAGIC staging    →  テスト・品質検証
# MAGIC prod       →  本番データ・参照専用
# MAGIC ```
# MAGIC 
# MAGIC - 各環境で GRANT を分けることで、開発者が本番データを誤って変更するリスクを排除
# MAGIC - DABs で環境変数を切り替えることで同一コードを各環境にデプロイ

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: 簡単な Job 作成
# MAGIC 
# MAGIC ノートブックをジョブとしてスケジュール実行します。

# COMMAND ----------

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.jobs import Task, NotebookTask, CronSchedule
import os

w = WorkspaceClient()

# 現在のノートブックパスを取得
current_notebook = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
notebook_dir = "/".join(current_notebook.split("/")[:-1])

# ジョブ作成
try:
    job = w.jobs.create(
        name="workshop_daily_etl",
        tasks=[
            Task(
                task_key="env_check",
                notebook_task=NotebookTask(
                    notebook_path=f"{notebook_dir}/00_intro_env_check"
                )
            )
        ],
        schedule=CronSchedule(
            quartz_cron_expression="0 0 8 * * ?",  # 毎日 8:00
            timezone_id="Asia/Tokyo"
        )
    )
    print(f"✅ Job 作成完了: {job.job_id}")
    print(f"   名前: workshop_daily_etl")
    print(f"   スケジュール: 毎日 8:00 JST")
except Exception as e:
    print(f"⚠️ Job 作成: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Lakeflow パイプライン（概念）
# MAGIC 
# MAGIC Lakeflow Spark Declarative Pipelines (SDP) でデータパイプラインを定義:
# MAGIC 
# MAGIC ```python
# MAGIC # 例: Bronze → Silver → Gold のパイプライン
# MAGIC import dlt
# MAGIC 
# MAGIC @dlt.table(comment="生ログ")
# MAGIC def bronze_vehicle_logs():
# MAGIC     return spark.readStream.table("vehicle_logs")
# MAGIC 
# MAGIC @dlt.table(comment="クレンジング済み")
# MAGIC @dlt.expect_or_drop("valid_battery", "battery_pct BETWEEN 0 AND 100")
# MAGIC def silver_vehicle_logs():
# MAGIC     return dlt.read_stream("bronze_vehicle_logs")
# MAGIC 
# MAGIC @dlt.table(comment="地域別集計")
# MAGIC def gold_location_summary():
# MAGIC     return dlt.read("silver_vehicle_logs").groupBy("location").agg(...)
# MAGIC ```
# MAGIC 
# MAGIC > FE 制約: Lakeflow パイプラインは各タイプ 1 本まで

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Declarative Automation Bundles (DABs) での移行
# MAGIC 
# MAGIC ### DABs とは
# MAGIC - ノートブック・ジョブ・パイプラインを **YAML + ソースコード**で定義
# MAGIC - `databricks bundle deploy --target prod` で環境別デプロイ
# MAGIC - CI/CD パイプライン（GitHub Actions 等）と組み合わせ可能
# MAGIC 
# MAGIC ### ディレクトリ構成例
# MAGIC 
# MAGIC ```
# MAGIC my-project/
# MAGIC ├── databricks.yml        # バンドル定義
# MAGIC ├── resources/
# MAGIC │   ├── jobs.yml          # ジョブ定義
# MAGIC │   └── pipelines.yml    # パイプライン定義
# MAGIC ├── src/
# MAGIC │   └── etl_notebook.py
# MAGIC └── tests/
# MAGIC ```
# MAGIC 
# MAGIC ```yaml
# MAGIC # databricks.yml
# MAGIC bundle:
# MAGIC   name: vehicle-analytics
# MAGIC targets:
# MAGIC   dev:
# MAGIC     default: true
# MAGIC     workspace:
# MAGIC       host: https://your-workspace.cloud.databricks.com
# MAGIC   prod:
# MAGIC     workspace:
# MAGIC       host: https://your-workspace.cloud.databricks.com
# MAGIC     variables:
# MAGIC       catalog: prod_catalog
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: SDLC / AI チェックシート
# MAGIC 
# MAGIC ### 本番移行チェックリスト
# MAGIC 
# MAGIC | カテゴリ | 確認項目 | ツール |
# MAGIC | --- | --- | --- |
# MAGIC | データ品質 | スキーマ検証・データプロファイリング | Lakeflow Expectations |
# MAGIC | セキュリティ | RLS/マスク/ABAC 設定 | UC Governance |
# MAGIC | コスト | 予算アラート・タグ按分 | AI Gateway / FinOps |
# MAGIC | 可用性 | リトライ・アラート | Jobs 設定 |
# MAGIC | AI 固有 | ハルシネーションチェック・バイアス検証 | Guardrails / 評価 |
# MAGIC | 運用 | モニタリング・ログ | 推論テーブル |
# MAGIC 
# MAGIC ### 製品/運用の線引き
# MAGIC 
# MAGIC | 層 | 内容 | 誰が担うか |
# MAGIC | --- | --- | --- |
# MAGIC | 製品機能 | UC, AI Gateway, Jobs, Apps | Databricks が提供 |
# MAGIC | 標準テンプレ | DABs, ノートブックテンプレ | Databricks + SI |
# MAGIC | 運用モデル | 代理申請・セキュア設計・基盤運用 | お客様 + SI |
# MAGIC 
# MAGIC → Databricks が標準テンプレとガバナンス機能で下支えし、運用モデル層はお客様が設計

# COMMAND ----------

# MAGIC %md
# MAGIC ## クリーンアップ（任意）

# COMMAND ----------

# 作成したジョブを削除（必要な場合）
# w.jobs.delete(job_id=job.job_id)
# print(f"✅ Job {job.job_id} 削除")

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✅ 完了条件
# MAGIC 
# MAGIC - [x] dev → prod のカタログ分離ができた
# MAGIC - [x] ジョブが 1 本動く
# MAGIC - [x] DABs での移行の型を理解した
# MAGIC - [x] SDLC/AI チェックシートの雛形を確認した
