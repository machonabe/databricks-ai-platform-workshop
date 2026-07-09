# Databricks notebook source
# MAGIC %md
# MAGIC # 共通設定 (config)
# MAGIC 
# MAGIC 各ノートブックの先頭で `%run ./config` を実行すると、
# MAGIC `CATALOG` / `SCHEMA` / `VOLUME_NAME` が自動設定されます。
# MAGIC 
# MAGIC 手動編集は不要です（既定カタログを自動検出します）。

# COMMAND ----------

# ワークスペースの既定カタログを自動検出
CATALOG = spark.sql("SELECT current_catalog()").collect()[0][0]

# ハンズオン用スキーマ名（全 Module 共通）
SCHEMA = "ai_workshop"

# 共通 Volume 名
VOLUME_NAME = "uploads"

print(f"=== ハンズオン共通設定 ===")
print(f"  CATALOG : {CATALOG}")
print(f"  SCHEMA  : {SCHEMA}")
print(f"  VOLUME  : /Volumes/{CATALOG}/{SCHEMA}/{VOLUME_NAME}")
