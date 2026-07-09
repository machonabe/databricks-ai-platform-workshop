# Databricks notebook source
# MAGIC %md
# MAGIC # Module 4: Unity Catalog ガバナンス（45分 ★）
# MAGIC 
# MAGIC ## 目的
# MAGIC - 粗→細のアクセス制御を実演
# MAGIC - 行フィルタ・列マスキング・タグ付け・ ABAC
# MAGIC - 「捨てない・重ねない・コピーしない」= データを動かさず in-place にガバナンスを重ねる
# MAGIC 
# MAGIC ## FE 制約
# MAGIC - RLS/マスキング/ABAC はサーバレスで動作 ✓
# MAGIC - SCIM/SSO/アカウントポリシーは FE 不可 → ワークスペース内グループ + GRANT で概念実演

# COMMAND ----------

# ⯅ 自分の環境に合わせて変更
CATALOG = "<catalog>"
SCHEMA = "<schema>"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: GRANT による粗→細のアクセス制御
# MAGIC 
# MAGIC UC の権限モデル:
# MAGIC - **Catalog レベル**: カタログ全体へのアクセス
# MAGIC - **Schema レベル**: スキーマ内全テーブルへのアクセス
# MAGIC - **Table レベル**: 個別テーブルへのアクセス

# COMMAND ----------

# グループ作成（FE ではワークスペース内グループで概念実演）
# 注: FE では SCIM/SSO が使えないため、アカウントグループ作成は口頭説明
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")

# GRANT の例（グループがあれば実行可能）
# 粗い権限: Schema 全体への読み取り
print("""
-- 粗い権限の例:
GRANT USE CATALOG ON CATALOG <catalog> TO `data_readers`;
GRANT USE SCHEMA ON SCHEMA <catalog>.<schema> TO `data_readers`;
GRANT SELECT ON SCHEMA <catalog>.<schema> TO `data_readers`;

-- 細かい権限の例:
GRANT SELECT ON TABLE <catalog>.<schema>.vehicle_logs TO `analyst_team`;
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: 行フィルタ関数（Row-Level Security）
# MAGIC 
# MAGIC ユーザーの属性に応じてデータをフィルタリングします。

# COMMAND ----------

# 行フィルタ関数の作成
spark.sql(f"""
CREATE OR REPLACE FUNCTION {CATALOG}.{SCHEMA}.row_filter_by_location(location_val STRING)
RETURNS BOOLEAN
RETURN 
  -- 管理者は全データ参照可、それ以外は東京のみ
  IS_ACCOUNT_GROUP_MEMBER('admins') OR location_val = '東京'
""")

print("✅ 行フィルタ関数作成完了")

# COMMAND ----------

# 行フィルタをテーブルに適用
spark.sql(f"""
ALTER TABLE {CATALOG}.{SCHEMA}.vehicle_logs
SET ROW FILTER {CATALOG}.{SCHEMA}.row_filter_by_location ON (location)
""")

print("✅ 行フィルタ適用完了")
print("   admins グループ以外は「東京」のデータのみ表示されます")

# COMMAND ----------

# 行フィルタの効果確認
display(spark.sql(f"""
  SELECT location, COUNT(*) AS cnt
  FROM {CATALOG}.{SCHEMA}.vehicle_logs
  GROUP BY location
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: 列マスキング
# MAGIC 
# MAGIC 機密カラムの値を隠します。

# COMMAND ----------

# 列マスキング関数の作成
spark.sql(f"""
CREATE OR REPLACE FUNCTION {CATALOG}.{SCHEMA}.mask_vehicle_id(vehicle_id_val STRING)
RETURNS STRING
RETURN 
  CASE 
    WHEN IS_ACCOUNT_GROUP_MEMBER('admins') THEN vehicle_id_val
    ELSE CONCAT('VH-***')
  END
""")

print("✅ 列マスキング関数作成完了")

# COMMAND ----------

# 列マスキングをテーブルに適用
spark.sql(f"""
ALTER TABLE {CATALOG}.{SCHEMA}.vehicle_logs
ALTER COLUMN vehicle_id SET MASK {CATALOG}.{SCHEMA}.mask_vehicle_id
""")

print("✅ 列マスキング適用完了")
print("   admins グループ以外は vehicle_id が 'VH-***' と表示されます")

# COMMAND ----------

# マスキングの効果確認
display(spark.sql(f"SELECT log_id, vehicle_id, location, battery_pct FROM {CATALOG}.{SCHEMA}.vehicle_logs LIMIT 5"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: タグ付けと ABAC ポリシー
# MAGIC 
# MAGIC タグでデータを分類し、属性ベースのアクセス制御（ABAC）を実現します。

# COMMAND ----------

# テーブル・カラムにタグを付与
spark.sql(f"""
ALTER TABLE {CATALOG}.{SCHEMA}.vehicle_logs
SET TAGS ('sensitivity' = 'internal', 'domain' = 'connected_vehicle')
""")

spark.sql(f"""
ALTER TABLE {CATALOG}.{SCHEMA}.vehicle_logs
ALTER COLUMN vehicle_id SET TAGS ('pii' = 'true')
""")

spark.sql(f"""
ALTER TABLE {CATALOG}.{SCHEMA}.vehicle_logs
ALTER COLUMN location SET TAGS ('pii' = 'true')
""")

print("✅ タグ付与完了")
print("   - テーブル: sensitivity=internal, domain=connected_vehicle")
print("   - vehicle_id, location: pii=true")

# COMMAND ----------

# タグの確認
display(spark.sql(f"""
  SELECT * FROM {CATALOG}.information_schema.table_tags
  WHERE schema_name = '{SCHEMA}'
"""))

# COMMAND ----------

display(spark.sql(f"""
  SELECT * FROM {CATALOG}.information_schema.column_tags
  WHERE schema_name = '{SCHEMA}' AND table_name = 'vehicle_logs'
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ### ABAC ポリシーの説明
# MAGIC 
# MAGIC ABAC (Attribute-Based Access Control) では、タグに基づいてアクセスポリシーを自動適用できます:
# MAGIC 
# MAGIC ```sql
# MAGIC -- ABAC ポリシーの例（Catalog Explorer から設定）:
# MAGIC -- 「pii=true タグが付いた列は、pii_readers グループのみ参照可」
# MAGIC ```
# MAGIC 
# MAGIC → Catalog Explorer > テーブル > Governance タブから設定可能

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: リネージ確認
# MAGIC 
# MAGIC Catalog Explorer でテーブルのリネージ（データの来歴）を確認できます。
# MAGIC 
# MAGIC **確認方法:**
# MAGIC 1. Catalog Explorer を開く
# MAGIC 2. `<catalog>.<schema>.vehicle_logs` を選択
# MAGIC 3. **Lineage** タブでデータの流れを確認

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: 「利用者側/基盤側」の責任分界
# MAGIC 
# MAGIC | 層 | 責任 | UC での実現 |
# MAGIC | --- | --- | --- |
# MAGIC | テーブルオーナー | データ品質・コメント・タグ付け | COMMENT / SET TAGS |
# MAGIC | 基盤管理者 | アクセスポリシー・監査 | RLS / マスク / ABAC / リネージ |
# MAGIC | 利用者 | GRANT された範囲で利用 | SELECT / USE |
# MAGIC 
# MAGIC ### 「捨てない・重ねない・コピーしない」
# MAGIC 
# MAGIC - データを動かさず **in-place** にガバナンスを重ねる
# MAGIC - 同じテーブルに対し、ユーザーの属性に応じて見え方が変わる
# MAGIC - コピーを作らないのでデータ拡散リスクがない

# COMMAND ----------

# MAGIC %md
# MAGIC ## クリーンアップ（任意）
# MAGIC 
# MAGIC ハンズオン後に行フィルタ・マスキングを削除する場合:

# COMMAND ----------

# -- クリーンアップ用（必要な場合のみ実行）
# spark.sql(f"ALTER TABLE {CATALOG}.{SCHEMA}.vehicle_logs DROP ROW FILTER")
# spark.sql(f"ALTER TABLE {CATALOG}.{SCHEMA}.vehicle_logs ALTER COLUMN vehicle_id DROP MASK")
# print("✅ クリーンアップ完了")

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✅ 完了条件
# MAGIC 
# MAGIC - [x] 同一テーブルで権限によって見え方（マスクあり/なし、行フィルタ等）が変わることを示せた
# MAGIC - [x] タグ付けと ABAC の概念を理解した
# MAGIC - [x] 「in-place ガバナンス」の考え方を理解した
