# Databricks notebook source
# MAGIC %md
# MAGIC # Module 0: イントロ・環境確認（15分）
# MAGIC 
# MAGIC ## ワークショップ全体像
# MAGIC 
# MAGIC 本ワークショップでは Databricks の AI 基盤を「環境払出 → 開発 → RAG → ガバナンス → コスト最適化」の流れで体験します。
# MAGIC 
# MAGIC | Module | テーマ | 所要時間 |
# MAGIC | --- | --- | --- |
# MAGIC | 0 | イントロ・環境確認 | 15分 |
# MAGIC | 1 | PoC 環境払出とデータ準備 | 35分 |
# MAGIC | 2 | Genie Code で AI ドリブン開発 | 30分 |
# MAGIC | 3 | RAG・Vector Search・Apps | 50分 |
# MAGIC | 4 | Unity Catalog ガバナンス | 45分 |
# MAGIC | 5A | AI Gateway ガバナンス | 40分 |
# MAGIC | 5B | LLM コスト（Omnigent・ローカル） | 30分 |
# MAGIC | 6 | 本番移行・サポート | 20分 |
# MAGIC 
# MAGIC ## 進め方
# MAGIC 
# MAGIC 1. 各ノートブック先頭の `CATALOG` / `SCHEMA` を自分の環境に合わせて設定
# MAGIC 2. 上から順にセルを実行
# MAGIC 3. サーバレスコンピュートで即時実行（クラスタ起動待ちなし）
# MAGIC 
# MAGIC ## Free Edition の位置付け
# MAGIC 
# MAGIC - サーバレス専用（カスタムコンピュート/GPU なし）
# MAGIC - Python + SQL のみ（R/Scala 不可）
# MAGIC - Unity Catalog フルマネージド
# MAGIC - 外部ストレージ接続不可→マネージド Volume/テーブルで代替

# COMMAND ----------

# MAGIC %md
# MAGIC ## 環境確認
# MAGIC 
# MAGIC サーバレスコンピュートに接続し、即座に結果が返ることを確認します。

# COMMAND ----------

# MAGIC %sql
# MAGIC -- 環境情報の確認（即座に結果が返る = サーバレスの「待ち時間ゼロ」）
SELECT 
  current_catalog() AS catalog,
  current_user() AS user,
  current_version() AS runtime_version

# COMMAND ----------

# MAGIC %md
# MAGIC ## サーバレス即実行の体感
# MAGIC 
# MAGIC 以下の軽量計算を実行し、クラスタ起動待ちなしで結果が返ることを体感します。

# COMMAND ----------

import time

start = time.time()

# サーバレスで即座に実行される軽量計算
df = spark.range(1_000_000).selectExpr("id", "id * 2 AS doubled", "id % 7 AS remainder")
result = df.groupBy("remainder").count().collect()

elapsed = time.time() - start
print(f"✅ 100万行の集計が {elapsed:.2f} 秒で完了（サーバレス）")
for row in result:
    print(f"  remainder={row['remainder']}: count={row['count']}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## UC ・ サーバレス ・ ワークスペースの関係
# MAGIC 
# MAGIC ```
# MAGIC ┌─────────────────────────────────────────────────────────────────┐
# MAGIC │                    Databricks Workspace                       │
# MAGIC │                                                                 │
# MAGIC │  ┌─────────────────┐   ┌───────────────────────┐          │
# MAGIC │  │  サーバレス       │   │  Unity Catalog          │          │
# MAGIC │  │  コンピュート     │   │  (メタストア)          │          │
# MAGIC │  │                 │   │                       │          │
# MAGIC │  │  - 即時起動     │   │  - Catalog             │          │
# MAGIC │  │  - 自動スケール  │   │    └─ Schema           │          │
# MAGIC │  │  - Python/SQL  │   │       └─ Table/View  │          │
# MAGIC │  │                 │   │       └─ Volume      │          │
# MAGIC │  └─────────────────┘   │       └─ Function    │          │
# MAGIC │                        └───────────────────────┘          │
# MAGIC │                                                                 │
# MAGIC │  ノートブック / SQL エディタ / Genie Code / Jobs / Apps     │
# MAGIC └─────────────────────────────────────────────────────────────────┘
# MAGIC ```
# MAGIC 
# MAGIC **ポイント:**
# MAGIC - サーバレスはクラスタ起動待ちがない（従来のクラスタ型との違い）
# MAGIC - Unity Catalog が全データのメタストア（カタログ）として機能
# MAGIC - Free Edition でも UC + サーバレスのフル機能が使える

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✅ 完了条件
# MAGIC 
# MAGIC - [x] 上記の環境確認クエリが即座に結果を返した
# MAGIC - [x] サーバレスコンピュートで「待ち時間ゼロ」を体感できた
# MAGIC - [x] UC / サーバレス / ワークスペースの関係を理解した
