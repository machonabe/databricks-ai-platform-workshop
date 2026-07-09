#!/usr/bin/env bash
set -euo pipefail

# ▼ Omnigent 0.4 の取得元（社内で確定した値に置き換える）
#   公開 FrancescoStabile/omnigent は現在 0.1.0（タグ無し）で v0.4 は存在しない。
#   0.4 のフォーク/内部ビルドの URL と ref（タグ or コミット）を指定すること。
OMNIGENT_REPO="REPLACE_WITH_YOUR_OMNIGENT_0_4_REPO_URL"
OMNIGENT_REF="v0.4.0"

echo "==> Python 3.11+ 確認"
python3 --version

echo "==> 仮想環境"
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip

echo "==> Omnigent 0.4 を取得"
if [ ! -d "omnigent" ]; then
  git clone "$OMNIGENT_REPO" omnigent
fi
( cd omnigent && git fetch --all --tags && git checkout "$OMNIGENT_REF" )

echo "==> インストール"
pip install -e ./omnigent
pip install -r requirements.txt

echo "==> バージョン検証（0.4.x でなければ失敗）"
python - <<'PY'
import importlib.metadata as m
v = m.version("omnigent")
print("omnigent installed:", v)
assert v.startswith("0.4"), f"ERROR: expected 0.4.x but got {v}. OMNIGENT_REPO/OMNIGENT_REF を確認してください。"
PY

echo "==> API 確認"
python -c "from omnigent.router import LLMRouter, Provider, TaskType; print('ok', [p.value for p in Provider])"

echo ""
echo "セットアップ完了。次に:"
echo "  cp .env.example .env   # キーを編集"
echo "  cd lab && python step1_baseline.py"
