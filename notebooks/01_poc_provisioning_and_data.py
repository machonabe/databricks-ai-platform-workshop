# Databricks notebook source
# MAGIC %md
# MAGIC # Module 1: PoC 環境払出とデータ準備（35分）
# MAGIC 
# MAGIC ## 目的
# MAGIC - 数コマンドでの環境払出（Catalog / Schema / Volume）
# MAGIC - サンプルデータの生成と Delta テーブル化
# MAGIC - 「簡易申請書 → 即時払出」のアナロジーを体験
# MAGIC 
# MAGIC ## FE 制約
# MAGIC - 外部ストレージ接続不可 → マネージド Volume/テーブルで代替
# MAGIC - DBFS 不可 → UC Volume を使用

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: ハンズオン用カタログ・スキーマの決定
# MAGIC 
# MAGIC Free Edition ではワークスペースに既定のカタログが割り当てられています。
# MAGIC そのカタログ内にハンズオン用のスキーマを作成します。
# MAGIC 
# MAGIC > **注意**: FE では新規カタログの作成が制限される場合があります。
# MAGIC その場合は `current_catalog()` で返る既定カタログをそのまま使ってください。

# COMMAND ----------

# まず現在の既定カタログを確認
current_cat = spark.sql("SELECT current_catalog()").collect()[0][0]
print(f"現在の既定カタログ: {current_cat}")

# COMMAND ----------

# ハンズオン用の設定
# 既定カタログをそのまま使い、スキーマを新規作成します
CATALOG = current_cat  # FE の既定カタログをそのまま使用
SCHEMA = "ai_workshop"  # ハンズオン用スキーマ
VOLUME_NAME = "uploads"

print(f"CATALOG: {CATALOG}")
print(f"SCHEMA:  {SCHEMA}")
print(f"→ この値を他のノートブックの CATALOG/SCHEMA にも設定してください")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Catalog / Schema / Volume の作成（= 環境払出）
# MAGIC 
# MAGIC 従来型: 申請書 → 承認 → インフラ構築 → 数週間
# MAGIC 
# MAGIC **Databricks**: 以下の SQL で即時払出↓

# COMMAND ----------

# FE では CREATE CATALOG が制限される場合があるため、既定カタログ内に Schema と Volume を作成
try:
    spark.sql(f"CREATE CATALOG IF NOT EXISTS {CATALOG}")
    print(f"✅ Catalog 確認/作成: {CATALOG}")
except Exception as e:
    # FE では既定カタログが既に存在するのでエラーでも続行可能
    print(f"ℹ️ Catalog は既存または作成権限なし（既定カタログを使用）: {e}")

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {CATALOG}.{SCHEMA}.{VOLUME_NAME}")

print(f"✅ 環境払出完了: {CATALOG}.{SCHEMA}")
print(f"   Volume: /Volumes/{CATALOG}/{SCHEMA}/{VOLUME_NAME}")
print()
print(f"📌 他のノートブックでは以下を先頭に設定してください:")
print(f'   CATALOG = "{CATALOG}"')
print(f'   SCHEMA = "{SCHEMA}"')

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
