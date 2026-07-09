# Databricks AI 基盤ハンズオン（Free Edition 対応）— 払出 → 開発 → RAG → ガバナンス → コスト最適化

**Databricks AI Platform Workshop — self-service provisioning, RAG, governance, and LLM cost control on Free Edition**

---

## 全体像

本ワークショップは 8 モジュール構成で、Databricks 上の AI 基盤を「環境払出 → 開発 → RAG → ガバナンス → コスト最適化」の流れで手を動かして体験します。

### モジュール構成

| Module | テーマ | 実行環境 |
| --- | --- | --- |
| 0 | イントロ・環境確認 | FE ノート |
| 1 | PoC 環境払出とデータ準備 | FE ノート |
| 2 | Genie Code で AI ドリブン開発 | FE ノート |
| 3 | RAG・Vector Search・Apps | FE ノート |
| 4 | Unity Catalog ガバナンス | FE ノート |
| 5A | AI Gateway ガバナンス・コスト可視化 | FE ノート |
| 5B | LLM コスト最適化（Omnigent 0.4） | ローカル |
| 6 | 本番移行・サポート | FE ノート |
| 7 | まとめ | ドキュメント |

### 2 つの実行環境

- **Databricks Free Edition ノートブック**（Module 0–6, 5A）: サーバレスコンピュートで即実行
- **ローカル PC**（Module 5B）: Omnigent 0.4 で LLM ルーティング・コスト比較

---

## クイックスタート

### リポジトリ取得

```bash
git clone https://github.com/machonabe/databricks-ai-platform-workshop.git
```

### Databricks 側（Module 0–6, 5A）

1. `notebooks/` を各自の FE ワークスペースにインポート（Git フォルダ推奨）
2. 各ノートブック先頭の `CATALOG` / `SCHEMA` 変数を自分の環境に合わせて設定
3. 上から順にセルを実行

### ローカル側（Module 5B — Omnigent）

```bash
cd databricks-ai-platform-workshop
./setup.sh          # Python 3.11+、仮想環境、Omnigent 0.4 インストール
cp .env.example .env  # API キーを編集
cd lab
python step1_baseline.py
python step2_switch.py
python step3_routing.py
python step3b_costfirst.py
```

---

## 前提・注意事項

- **Free Edition は各自アカウント推奨**: 共有すると日次クォータでその日のコンピュートが停止します
- **API キーはコミットしない**: `.env` は `.gitignore` で除外済み
- **Omnigent 0.4**: 公開リポジトリは 0.1.0 。0.4 の取得元は `setup.sh` の `OMNIGENT_REPO` / `OMNIGENT_REF` で指定してください
- **FE 制約**: サーバレス専用、GPU/カスタムコンピュート無し、外部ストレージ不可、DBFS 不可

---

## Omnigent について

[Omnigent](https://github.com/FrancescoStabile/omnigent) は MIT ライセンスのオープンソース LLM ルーターです。本ワークショップでは v0.4 を使用し、LLM コスト最適化の実践的な体験を提供します。Omnigent は初期段階の OSS プロジェクトであり、今後の変更にご注意ください。

---

## リポジトリ構成

```
./
├── README.md
├── HANDSON.md
├── setup.sh
├── requirements.txt
├── .env.example
├── .gitignore
├── notebooks/
│   ├── 00_intro_env_check.py
│   ├── 01_poc_provisioning_and_data.py
│   ├── 02_genie_code_ai_dev.py
│   ├── 03_rag_vector_search_app.py
│   ├── 04_unity_catalog_governance.py
│   ├── 05_ai_gateway_governance.py
│   └── 06_support_and_prod_migration.py
├── lab/
│   ├── omni_lab.py
│   ├── log_cost.py
│   ├── step1_baseline.py
│   ├── step2_switch.py
│   ├── step3_routing.py
│   ├── step3b_costfirst.py
│   └── step5a_databricks_route.py
└── databricks/
    └── finops_dashboard_setup.md
```

---

## ライセンス

本リポジトリのコンテンツは社内配布用です。Omnigent は MIT ライセンスに従います。
