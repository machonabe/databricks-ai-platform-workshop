# VS Code 拡張 + Databricks Connect セットアップ手順

ローカル開発環境から Databricks のサーバレスコンピュートに接続し、AI 支援付き開発を行う手順です。

---

## 1. VS Code 拡張のインストール

1. VS Code を開く
2. Extensions マーケットプレース (`Cmd+Shift+X` / `Ctrl+Shift+X`) を開く
3. **「Databricks」** で検索
4. **Databricks** 拡張をインストール

---

## 2. ワークスペースへの接続

1. コマンドパレット (`Cmd+Shift+P` / `Ctrl+Shift+P`) を開く
2. **Databricks: Configure Workspace** を選択
3. ワークスペース URL を入力:
   ```
   https://<your-workspace>.cloud.databricks.com
   ```
4. 認証方法を選択:
   - **OAuth (U2M)**: ブラウザでログイン（推奨）
   - **Personal Access Token**: PAT を入力

---

## 3. Databricks Connect のインストール

```bash
# DBR バージョンに合わせてインストール（例: DBR 16.x）
pip install databricks-connect==16.0.*

# サーバレス接続の場合
pip install databricks-connect
```

> **注意**: `databricks-connect` のバージョンは接続先クラスタの DBR バージョンと一致させてください。サーバレスの場合は最新版で OK です。

---

## 4. 認証設定

### 方法 A: `~/.databrickscfg` ファイル（推奨）

```ini
[DEFAULT]
host = https://<your-workspace>.cloud.databricks.com
token = dapi_xxxxxxxxxxxx

# 特定クラスタに接続する場合（任意）
cluster_id = 0101-123456-abcdefgh

# サーバレスに接続する場合
serverless_compute_id = auto
```

### 方法 B: 環境変数

```bash
export DATABRICKS_HOST=https://<your-workspace>.cloud.databricks.com
export DATABRICKS_TOKEN=dapi_xxxxxxxxxxxx
```

---

## 5. Python コードから利用

```python
from databricks.connect import DatabricksSession

# プロファイルを指定して接続
spark = DatabricksSession.builder.profile("DEFAULT").getOrCreate()

# サーバレスコンピュートで即実行
df = spark.sql("SELECT current_catalog(), current_user()")
df.show()

# テーブルの読み書きもローカルから可能
df = spark.table("catalog.schema.vehicle_logs")
df.filter(df.battery_pct < 30).show()
```

### サーバレスに明示的に接続

```python
from databricks.connect import DatabricksSession

spark = (
    DatabricksSession.builder
    .host("https://<your-workspace>.cloud.databricks.com")
    .token("dapi_xxxxxxxxxxxx")
    .serverless(True)
    .getOrCreate()
)
```

---

## 6. VS Code での開発フロー

```
ローカル PC                         Databricks
┌─────────────────┐                ┌──────────────────────┐
│  VS Code        │                │  サーバレスコンピュート    │
│  + Databricks   │ ──── API ───→  │  (Spark 実行)         │
│    拡張         │                │                      │
│  + Python       │ ←── 結果 ────  │  Unity Catalog        │
│    コード       │                │  (データ参照)          │
└─────────────────┘                └──────────────────────┘
```

### できること

| 機能 | 説明 |
| --- | --- |
| コード実行 | ローカルの `.py` / `.ipynb` からリモート Spark を実行 |
| デバッグ | ブレークポイント付きでステップ実行 |
| テスト | `pytest` でユニットテスト（Spark DataFrame のテスト含む） |
| ノートブック同期 | ワークスペースのノートブックをローカルに同期・編集 |
| Genie Code | VS Code 内で AI 支援付きコード生成 |
| オートコンプリート | UC テーブル名・カラム名の補完 |

---

## 7. トラブルシューティング

### `Connection refused` エラー

```bash
# クラスタが起動しているか確認
databricks clusters get --cluster-id <cluster_id>
```

### バージョン不一致エラー

```
databricks-connect のバージョンと DBR バージョンを揃えてください:
- DBR 16.x → pip install databricks-connect==16.0.*
- DBR 17.x → pip install databricks-connect==17.0.*
- サーバレス → pip install databricks-connect (最新版)
```

### 認証エラー

```bash
# トークンの有効性を確認
databricks auth token
# または OAuth で再認証
databricks auth login --host https://<your-workspace>.cloud.databricks.com
```

---

## 参考リンク

- [Databricks Connect ドキュメント](https://docs.databricks.com/dev-tools/databricks-connect/index.html)
- [VS Code 拡張ドキュメント](https://docs.databricks.com/dev-tools/vscode-ext/index.html)
- [Databricks CLI セットアップ](https://docs.databricks.com/dev-tools/cli/index.html)
