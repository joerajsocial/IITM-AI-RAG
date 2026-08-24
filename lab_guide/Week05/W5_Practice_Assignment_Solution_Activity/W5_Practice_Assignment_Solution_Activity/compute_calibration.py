"""compute_calibration.py — W5 activity helper.

Reads the learner's `docs/judge-calibration.md` (specifically the
"My scores" markdown table) and the judge's verdicts in the
`eval_runs` table, then prints agreement metrics:

- Exact agreement (out of 30 dimension-scores)
- Within-1 agreement (Δ ≤ 1)
- Per-dimension breakdown
- Specific disagreements > 1 (the ones worth investigating)

Usage:
    python compute_calibration.py \\
        --calibration-file docs/judge-calibration.md \\
        --db data/answers.db \\
        --label eval-run-001
"""
from __future__ import annotations

import argparse
import re
import sqlite3
from pathlib import Path


# Match a markdown table row like:
# | g001 | 3 | 4 | 3 | One-line note |
TABLE_ROW = re.compile(
    r"^\|\s*(g\d+)\s*\|\s*(\d)\s*\|\s*(\d)\s*\|\s*(\d)\s*\|",
)


def parse_calibration_file(path: str) -> dict[str, dict[str, int]]:
    """Extract the learner's blind scores from the markdown table.

    Returns: { golden_id -> {accuracy, groundedness, format} }
    """
    scores = {}
    for line in Path(path).read_text().splitlines():
        match = TABLE_ROW.match(line)
        if match:
            gid, a, g, f = match.groups()
            scores[gid] = {
                "accuracy": int(a),
                "groundedness": int(g),
                "format": int(f),
            }
    return scores


def fetch_judge_scores(db_path: str, label: str,
                       golden_ids: list[str]) -> dict[str, dict[str, int]]:
    """Pull the judge's scores for the same entries from eval_runs."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    placeholders = ",".join("?" * len(golden_ids))
    cur.execute(f"""
        SELECT golden_id, accuracy, groundedness, format
        FROM eval_runs
        WHERE eval_run_label = ?
          AND golden_id IN ({placeholders})
    """, (label, *golden_ids))
    out = {}
    for gid, a, g, f in cur.fetchall():
        out[gid] = {"accuracy": a, "groundedness": g, "format": f}
    conn.close()
    return out


def compute_agreement(mine: dict, judge: dict) -> dict:
    """Compute exact / within-1 / per-dimension agreement + disagreements > 1."""
    dimensions = ["accuracy", "groundedness", "format"]
    exact = 0
    within_1 = 0
    total = 0
    per_dim_exact = {d: 0 for d in dimensions}
    per_dim_total = {d: 0 for d in dimensions}
    disagreements_gt1 = []

    for gid, my_scores in mine.items():
        if gid not in judge:
            continue  # judge didn't score this one
        for dim in dimensions:
            my_score = my_scores[dim]
            judge_score = judge[gid][dim]
            total += 1
            per_dim_total[dim] += 1
            delta = abs(my_score - judge_score)
            if delta == 0:
                exact += 1
                per_dim_exact[dim] += 1
                within_1 += 1
            elif delta == 1:
                within_1 += 1
            else:
                disagreements_gt1.append({
                    "gid": gid,
                    "dimension": dim,
                    "mine": my_score,
                    "judge": judge_score,
                    "delta": delta,
                })

    return {
        "exact": exact,
        "within_1": within_1,
        "total": total,
        "per_dim_exact": per_dim_exact,
        "per_dim_total": per_dim_total,
        "disagreements_gt1": disagreements_gt1,
    }


def print_summary(result: dict):
    total = result["total"]
    n_entries = total // 3
    print("\nCalibration summary")
    print("-" * 19)
    print(f"  n entries           : {n_entries}")
    print(f"  n dimension-scores  : {total}")
    if total > 0:
        exact_pct = 100 * result["exact"] / total
        within1_pct = 100 * result["within_1"] / total
        print(f"  exact agreement     : {result['exact']} / {total}  ({exact_pct:.0f}%)")
        print(f"  within-1 agreement  : {result['within_1']} / {total}  ({within1_pct:.0f}%)")
    print(f"  per-dimension exact :")
    for dim, count in result["per_dim_exact"].items():
        denom = result["per_dim_total"][dim]
        print(f"    {dim:<16}  : {count} / {denom}")
    print(f"  disagreements > 1   : {len(result['disagreements_gt1'])}")
    for d in result["disagreements_gt1"]:
        higher = "I rated higher" if d["mine"] > d["judge"] else "judge rated higher"
        print(f"    {d['gid']}: I scored {d['dimension'][0]}={d['mine']} / "
              f"judge={d['judge']} (Δ={d['delta']}). {higher}.")


def main():
    parser = argparse.ArgumentParser(
        description="Compute LLM judge calibration agreement.",
    )
    parser.add_argument("--calibration-file", required=True,
                        help="Path to docs/judge-calibration.md")
    parser.add_argument("--db", required=True,
                        help="Path to data/answers.db")
    parser.add_argument("--label", required=True,
                        help="eval_run_label (e.g. eval-run-001)")
    args = parser.parse_args()

    mine = parse_calibration_file(args.calibration_file)
    if not mine:
        print(f"ERROR: no scored rows found in {args.calibration_file}")
        print("Expected markdown table rows like: | g001 | 3 | 4 | 3 | ... |")
        return

    judge = fetch_judge_scores(args.db, args.label, list(mine.keys()))
    if not judge:
        print(f"ERROR: no judge scores in {args.db} for label={args.label}")
        return

    result = compute_agreement(mine, judge)
    print_summary(result)


if __name__ == "__main__":
    main()
