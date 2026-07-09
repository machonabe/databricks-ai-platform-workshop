# Databricks notebook source
# MAGIC %md
# MAGIC # Module 2: Genie Code で AI ドリブン開発（30分）
# MAGIC 
# MAGIC ## 目的
# MAGIC - Genie Code で AI ドリブン開発を体験
# MAGIC - UC メタデータ駆動（テーブルコメント、リネージ）
# MAGIC - skills / instructions / MCP でナレッジ注入
# MAGIC 
# MAGIC ## SPARK 施策
# MAGIC - ② 標準環境: ノート + SQL エディタ + Genie Code が標準ツール
# MAGIC - ⑦ AIドリブン: AI がコード生成・分析を支援

# COMMAND ----------

# ⯅ 自分の環境に合わせて変更
CATALOG = "<catalog>"
SCHEMA = "<schema>"

# COMMAND ----------

# MAGIC %md
# MAGIC ## 演習 1: Genie Code でクエリ生成
# MAGIC 
# MAGIC ### 操作手順
# MAGIC 
# MAGIC 1. ノートブックの右サイドバーで **Genie Code** を開く
# MAGIC 2. 以下のように自然言語で指示:
# MAGIC 
# MAGIC > 「`<catalog>.<schema>.vehicle_logs` から、地域別の平均バッテリー残量を集計して」
# MAGIC 
# MAGIC 3. 生成された SQL を確認し、実行
# MAGIC 
# MAGIC ### ポイント
# MAGIC - UC のテーブル/カラムコメントが Genie Code の精度を向上させる
# MAGIC - メタデータが充実するほど、AI の提案が正確に

# COMMAND ----------

# MAGIC %md
# MAGIC ## 演習 2: メタデータ確認
# MAGIC 
# MAGIC Genie Code が参照する UC メタデータを確認します。

# COMMAND ----------

# テーブルコメントの確認
display(spark.sql(f"""
  DESCRIBE TABLE EXTENDED {CATALOG}.{SCHEMA}.vehicle_logs
"""))

# COMMAND ----------

# カラムコメントの確認
display(spark.sql(f"""
  SELECT column_name, comment 
  FROM {CATALOG}.information_schema.columns 
  WHERE table_schema = '{SCHEMA}' AND table_name = 'vehicle_logs'
  ORDER BY ordinal_position
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 演習 3: Genie Code で分析クエリ生成
# MAGIC 
# MAGIC 以下のプロンプトを試してみてください:
# MAGIC 
# MAGIC 1. 「時間帯別の平均速度を計算してチャートにして」
# MAGIC 2. 「バッテリー残量が 30% 以下のレコードを抽出して」
# MAGIC 3. 「月別の走行ログ件数を集計して」
# MAGIC 
# MAGIC 生成されたコードが正しく動作するか確認しましょう。

# COMMAND ----------

# Genie Code が生成したコードの検証用（例: 地域別平均バッテリー）
display(spark.sql(f"""
  SELECT location, 
         ROUND(AVG(battery_pct), 1) AS avg_battery,
         COUNT(*) AS log_count
  FROM {CATALOG}.{SCHEMA}.vehicle_logs
  GROUP BY location
  ORDER BY avg_battery
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ## skills / instructions / MCP の位置付け
# MAGIC 
# MAGIC Genie Code にナレッジを注入する方法:
# MAGIC 
# MAGIC | 方法 | 内容 | 用途 |
# MAGIC | --- | --- | --- |
# MAGIC | **instructions** | `.assistant_instructions.md` | 個人の常用ルール（言語、スタイル） |
# MAGIC | **skills** | Genie Space の SQL ナレッジ | 組織のドメイン知識 |
# MAGIC | **MCP** | 外部ツール接続 | GitHub, Slack, Jira 等 |
# MAGIC 
# MAGIC ### VS Code 拡張 + Databricks Connect
# MAGIC 
# MAGIC ローカル開発環境でも Databricks Connect を使えば:
# MAGIC - VS Code からサーバレスコンピュートに接続
# MAGIC - Genie Code の AI 支援付き開発
# MAGIC - テスト・デバッグもローカルで完結

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✅ 完了条件
# MAGIC 
# MAGIC - [x] Genie Code で生成した SQL が Module 1 のテーブルに対して動く
# MAGIC - [x] UC メタデータ（テーブル/カラムコメント）を確認できた
# MAGIC - [x] skills/instructions/MCP の位置付けを理解した
