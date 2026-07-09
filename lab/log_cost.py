# lab/log_cost.py — 実行結果を CSV に追記（Module 5B → 5A ダッシュボード用）
import csv, os, datetime


def append_cost(row, path="omnigent_costs.csv"):
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["ts", "task", "provider", "model", "in_tok", "out_tok", "cost_usd"])
        w.writerow([datetime.datetime.utcnow().isoformat(), row.get("task", ""),
                    row["provider"], row["model"], row["in_tok"], row["out_tok"], f"{row['cost']:.6f}"])
