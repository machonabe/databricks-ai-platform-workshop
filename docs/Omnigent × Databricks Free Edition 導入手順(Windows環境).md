# Databricks notebook source
# MAGIC %md
# MAGIC # Omnigent × Databricks Free Edition 導入手順(Windows環境)
# MAGIC
# MAGIC Omnigent on Databricks(マネージド, Beta)を、Windows PCをホストとして利用するための手順です。

# COMMAND ----------

# MAGIC %md
# MAGIC ## ⚠️ Windows環境での注意点
# MAGIC
# MAGIC Omnigent on Databricks(マネージド版)は**ネイティブWindowsサポートがなく**、WSL2(Windows Subsystem for Linux)内で実行し、WSL2ディストリビューション上でLinux向けの手順に従う必要があります。
# MAGIC
# MAGIC ホスト接続は通常のPowerShell/コマンドプロンプトではなく、**WSL2内のターミナル**から行います。

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: WSL2のセットアップ(初回のみ)
# MAGIC
# MAGIC PowerShellを**管理者権限**で開いて実行します。
# MAGIC
# MAGIC ```powershell
# MAGIC wsl --install
# MAGIC ```
# MAGIC
# MAGIC 再起動後、Ubuntu等のディストリビューションの初期セットアップ(ユーザー作成)を済ませておきます。

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Free Editionワークスペースにアクセス
# MAGIC
# MAGIC ブラウザでFree Editionワークスペースにログインします(サインアップ済みであることが前提です)。

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: マネージドOmnigentを開く
# MAGIC
# MAGIC ブラウザで以下のURLにアクセスします。
# MAGIC
# MAGIC ```
# MAGIC https://<workspace-url>/omnigent
# MAGIC ```
# MAGIC
# MAGIC 「Connect a host」の画面で、次のようなコマンドが表示されます。
# MAGIC
# MAGIC ```
# MAGIC omni host --server https://dbc-xxxx.cloud.databricks.com
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: WSL2内でOmnigent CLIをインストール
# MAGIC
# MAGIC WSL2のターミナル(Ubuntu等)を開いて実行します。
# MAGIC
# MAGIC ```bash
# MAGIC # uvが無ければ先にインストール
# MAGIC curl -LsSf https://astral.sh/uv/install.sh | sh
# MAGIC
# MAGIC # Omnigent CLI インストール
# MAGIC uv tool install "omnigent[databricks]"
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: ホストを接続
# MAGIC
# MAGIC 同じWSL2ターミナルで、Step 3で表示されたコマンドを実行します。
# MAGIC
# MAGIC ```bash
# MAGIC omni host --server https://dbc-xxxx.cloud.databricks.com
# MAGIC ```
# MAGIC
# MAGIC ブラウザが開いてDatabricksへのOAuthログインが求められるので、ワークスペースの認証情報でログインします。成功すると、Web UIのホスト選択肢にこのWSL2マシンが表示されます。

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: セッション開始
# MAGIC
# MAGIC Web UIで **New Chat** → ホスト選択でWSL2マシンを選択 → 使いたいharness(Claude Code / Codexなど)を選んでタスクを送信します。

# COMMAND ----------

# MAGIC %md
# MAGIC ## オプション機能
# MAGIC
# MAGIC ### コスト可視化・予算設定
# MAGIC ワークスペース左サイドバーの **AI Gateway** → **View Dashboard** の **Cost Observability** タブで使用量を確認できます。予算は、モデル単位のレート制限、またはセッション設定パネルの `cost_budget` ポリシーで設定します。
# MAGIC
# MAGIC ### Intelligent Routing
# MAGIC チャットで「簡単なタスクは安いモデルに回して」と頼むか、セッション設定パネルのポリシー一覧からトグルします。
# MAGIC
# MAGIC ### エージェント切り替え(Codex ⇔ Claude Code)
# MAGIC セッションの「⋯」メニュー(またはメッセージのホバー)から **Fork** し、新しいharnessを選択します。会話履歴を引き継いだまま切り替わります。

# COMMAND ----------

# MAGIC %md
# MAGIC ## 補足
# MAGIC Omnigent on DatabricksはBeta機能のため、仕様変更が比較的速いです。お客様にご案内する前に、一度この手順をご自身の環境で試すことをお勧めします。