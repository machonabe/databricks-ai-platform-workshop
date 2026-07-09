# Databricks notebook source
# MAGIC %md
# MAGIC # Module 1: PoC 環境払出とデータ準備（35分）
# MAGIC 
# MAGIC ## 目的
# MAGIC - 数コマンドでの環境払出（Catalog / Schema / Volume）
# MAGIC - サンプルデータの生成と Delta テーブル化
# MAGIC - 「簡易申請書 → 即時払出」のアナロジーを体験
# MAGIC 
# MAGIC ## SPARK 施策
# MAGIC - ① 即払出: 申請から数分で環境が整う
# MAGIC - ② 標準環境: ノート + SQL エディタが標準ツール
# MAGIC 
# MAGIC ## FE 制約
# MAGIC - 外部ストレージ接続不可 → マネージド Volume/テーブルで代替
# MAGIC - DBFS 不可 → UC Volume を使用

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: 環境変数の設定
# MAGIC 
# MAGIC 以下の `CATALOG` と `SCHEMA` を自分の環境に合わせて設定してください。

# COMMAND ----------

# ⯅ 自分の環境に合わせて変更
CATALOG = "<catalog>"
SCHEMA = "<schema>"
VOLUME_NAME = "uploads"

print(f"CATALOG: {CATALOG}")
print(f"SCHEMA:  {SCHEMA}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Catalog / Schema / Volume の作成（= 環境払出）
# MAGIC 
# MAGIC 従来型: 申請書 → 承認 → インフラ構築 → 数週間
# MAGIC 
# MAGIC **Databricks**: 以下の SQL で即時払出↓

# COMMAND ----------

spark.sql(f"CREATE CATALOG IF NOT EXISTS {CATALOG}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {CATALOG}.{SCHEMA}.{VOLUME_NAME}")

print(f"✅ 環境払出完了: {CATALOG}.{SCHEMA}")
print(f"   Volume: /Volumes/{CATALOG}/{SCHEMA}/{VOLUME_NAME}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: サンプルデータの生成
# MAGIC 
# MAGIC 車両ログを模したデータを `spark.createDataFrame` で生成し、Delta テーブルとして保存します。

# COMMAND ----------

from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType, TimestampType
from datetime import datetime, timedelta
import random

# サンプル車両ログデータ
random.seed(42)
vehicles = ["VH-001", "VH-002", "VH-003", "VH-004", "VH-005"]
locations = ["東京", "大阪", "名古屋", "福岡", "札幌"]

rows = []
base_time = datetime(2025, 1, 1)
for i in range(500):
    rows.append((
        f"LOG-{i:04d}",
        random.choice(vehicles),
        random.choice(locations),
        random.uniform(20.0, 95.0),  # battery_pct
        random.randint(0, 150),       # speed_kmh
        random.uniform(10.0, 40.0),   # temperature_c
        base_time + timedelta(hours=random.randint(0, 720))
    ))

schema = StructType([
    StructField("log_id", StringType(), False),
    StructField("vehicle_id", StringType(), False),
    StructField("location", StringType(), False),
    StructField("battery_pct", DoubleType(), False),
    StructField("speed_kmh", IntegerType(), False),
    StructField("temperature_c", DoubleType(), False),
    StructField("timestamp", TimestampType(), False),
])

df = spark.createDataFrame(rows, schema=schema)
df.write.mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.vehicle_logs")

print(f"✅ Delta テーブル作成完了: {CATALOG}.{SCHEMA}.vehicle_logs ({df.count()} 行)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: データ確認

# COMMAND ----------

display(spark.sql(f"SELECT * FROM {CATALOG}.{SCHEMA}.vehicle_logs LIMIT 10"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: テーブルにコメントを付与（メタデータ駆動）
# MAGIC 
# MAGIC UC のメタデータは Genie Code やリネージで活用されます。

# COMMAND ----------

spark.sql(f"""
  COMMENT ON TABLE {CATALOG}.{SCHEMA}.vehicle_logs IS
  'EV 車両の走行ログ。バッテリー残量、速度、温度、位置情報を含む。'
""")
spark.sql(f"COMMENT ON COLUMN {CATALOG}.{SCHEMA}.vehicle_logs.battery_pct IS 'バッテリー残量 (%)'") 
spark.sql(f"COMMENT ON COLUMN {CATALOG}.{SCHEMA}.vehicle_logs.speed_kmh IS '走行速度 (km/h)'") 
spark.sql(f"COMMENT ON COLUMN {CATALOG}.{SCHEMA}.vehicle_logs.temperature_c IS '外気温 (℃)'") 

print("✅ テーブル/カラムコメント設定完了")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 補足: 払出の自動化・標準化
# MAGIC 
# MAGIC 実運用では以下を併用し、「申請→即時払出」を自動化できます:
# MAGIC 
# MAGIC - **Git フォルダ**: ノートブックのバージョン管理
# MAGIC - **Declarative Automation Bundles (DABs)**: テンプレートから同一環境を再現
# MAGIC - **Terraform / Databricks SDK**: IaC でワークスペース構成をコード化
# MAGIC 
# MAGIC これにより「テンプレから同一環境を再現」= 払出の自動化・標準化が実現します。

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✅ 完了条件
# MAGIC 
# MAGIC - [x] 自分の Catalog に Delta テーブルが 1 つできた
# MAGIC - [x] `SELECT * FROM <catalog>.<schema>.vehicle_logs` でデータが返る
# MAGIC - [x] Volume が作成された
