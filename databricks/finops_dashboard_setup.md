# FinOps ダッシュボードセットアップ

Module 5B（ローカル）で生成された `omnigent_costs.csv` を Databricks に取り込み、AI/BI ダッシュボードで可視化する手順です。

---

## 1. CSV を UC Volume にアップロード

ローカルで `lab/` ディレクトリに生成された `omnigent_costs.csv` を Databricks の Volume にアップロードします。

### 方法 A: UI からアップロード

1. Catalog Explorer → `<catalog>.<schema>.uploads` Volume を開く
2. **Upload to this volume** をクリック
3. `omnigent_costs.csv` を選択してアップロード

### 方法 B: Databricks CLI

```bash
databricks fs cp omnigent_costs.csv \
  dbfs:/Volumes/<catalog>/<schema>/uploads/omnigent_costs.csv
```

---

## 2. Delta テーブル化

ノートブックまたは SQL エディタで実行:

```sql
CREATE TABLE IF NOT EXISTS <catalog>.<schema>.omnigent_costs AS
SELECT * FROM read_files('/Volumes/<catalog>/<schema>/uploads/omnigent_costs.csv',
                         format => 'csv', header => true);
```

データ確認:

```sql
SELECT * FROM <catalog>.<schema>.omnigent_costs ORDER BY ts DESC LIMIT 20;
```

---

## 3. AI/BI ダッシュボード作成

### ダッシュボードのタイル構成

#### タイル 1: 合計コスト（カウンター）

```sql
SELECT 
  ROUND(SUM(CAST(cost_usd AS DOUBLE)), 4) AS total_cost_usd,
  COUNT(*) AS total_requests
FROM <catalog>.<schema>.omnigent_costs;
```

#### タイル 2: プロバイダ別コスト（バーチャート）

```sql
SELECT 
  provider,
  ROUND(SUM(CAST(cost_usd AS DOUBLE)), 4) AS total_cost,
  SUM(CAST(in_tok AS INT)) AS total_input_tokens,
  SUM(CAST(out_tok AS INT)) AS total_output_tokens
FROM <catalog>.<schema>.omnigent_costs
GROUP BY provider
ORDER BY total_cost DESC;
```

#### タイル 3: タスク別コスト（バーチャート）

```sql
SELECT 
  task,
  provider,
  ROUND(SUM(CAST(cost_usd AS DOUBLE)), 6) AS cost
FROM <catalog>.<schema>.omnigent_costs
GROUP BY task, provider
ORDER BY cost DESC;
```

#### タイル 4: 日次推移（折れ線チャート）

```sql
SELECT 
  DATE(ts) AS date,
  ROUND(SUM(CAST(cost_usd AS DOUBLE)), 6) AS daily_cost,
  COUNT(*) AS requests
FROM <catalog>.<schema>.omnigent_costs
GROUP BY DATE(ts)
ORDER BY date;
```

#### タイル 5: 既定 vs コスト最優先比較（バーチャート）

```sql
SELECT 
  CASE 
    WHEN task LIKE 'costfirst:%' THEN 'cost-first'
    ELSE 'default'
  END AS routing_strategy,
  ROUND(SUM(CAST(cost_usd AS DOUBLE)), 6) AS total_cost,
  COUNT(*) AS requests
FROM <catalog>.<schema>.omnigent_costs
GROUP BY 1;
```

---

## 4. AI Gateway 使用状況と並べる

Module 5A で取得した AI Gateway の推論テーブルと並べて表示することで、
「Databricks 内の利用コスト」と「外部 LLM の利用コスト」を統合的に可視化できます。

```sql
-- 統合ビューの例
SELECT 'Omnigent (External)' AS source, provider, CAST(cost_usd AS DOUBLE) AS cost, ts
FROM <catalog>.<schema>.omnigent_costs
UNION ALL
SELECT 'AI Gateway (Databricks)' AS source, 'databricks' AS provider, 
       total_tokens * 0.0001 AS cost,  -- 概算
       from_unixtime(timestamp_ms/1000) AS ts
FROM <catalog>.<schema>.`databricks-meta-llama-3-3-70b-instruct_payload`
ORDER BY ts DESC;
```

---

## ダッシュボード作成手順

1. 左サイドバー → **New** → **Dashboard**
2. 上記の SQL をそれぞれデータセットとして追加
3. 適切なチャートタイプを選択してタイルを配置
4. ダッシュボードを保存・公開
