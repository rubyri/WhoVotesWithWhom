"""
UN General Assembly Voting Data — Pairwise Agreement Matrix
============================================================
Computes pairwise voting agreement scores between all country pairs,
both overall and per subject category, for each year.

Design choices:
  - Strict agreement: only resolutions where BOTH countries voted (Y/N/A)
  - A+A (both abstained) counts as agreement
  - Minimum 5 shared votes per pair-year; below this score is NaN
  - Computed by year (aligns with ideal points data)
  - Output: long format CSV + NxN matrix JSON for latest year

Outputs:
  - agreement_overall.csv      : overall pairwise scores per year
  - agreement_by_category.csv  : per-category scores per year
  - agreement_matrix_YYYY.json : NxN matrix for latest year 
"""

import pandas as pd
import numpy as np
import json
from itertools import combinations

UN_CLEAN_PATH = "data/processed/un_clean.csv"
MIN_SHARED_VOTES = 5

# ── 1. Load ───────────────────────────────────────────────────────────────────

un = pd.read_csv(UN_CLEAN_PATH, low_memory=False)
un["date"] = pd.to_datetime(un["date"], errors="coerce")
print(f"  Rows loaded : {len(un):,}")

# Keep only actual votes (drop absent X rows)
un_voted = un[un["vote_num"].notna()].copy()
print(f"  Rows with valid vote (Y/N/A) : {len(un_voted):,}")
print(f"  Rows dropped (absent/X)      : {len(un) - len(un_voted):,}")


# ── 2. Core agreement function ────────────────────────────────────────────────

def compute_agreement(df, group_cols):
    """
    Given a dataframe of votes, compute pairwise agreement for each
    group defined by group_cols (e.g. ['year'] or ['year', 'subject_category']).

    Returns a dataframe with columns:
        group_cols + [ms_code1, ms_code2, n_shared, agreement]
    """
    records = []

    groups = df.groupby(group_cols)
    total_groups = len(groups)

    for i, (group_key, group_df) in enumerate(groups):
        if i % 10 == 0:
            print(f"    Processing group {i+1}/{total_groups} : {group_key}", end="\r")

        # Pivot: rows = resolution, columns = country, values = vote_num
        pivot = group_df.pivot_table(
            index="resolution",
            columns="ms_code",
            values="vote_num",
            aggfunc="first"
        )

        countries = pivot.columns.tolist()
        if len(countries) < 2:
            continue

        # Vectorised pairwise computation
        vote_matrix = pivot.values  # shape: (resolutions, countries)
        n_countries = len(countries)

        for idx1, idx2 in combinations(range(n_countries), 2):
            v1 = vote_matrix[:, idx1]
            v2 = vote_matrix[:, idx2]

            # Only rows where both voted
            both_voted = ~(np.isnan(v1) | np.isnan(v2))
            n_shared = both_voted.sum()

            if n_shared < MIN_SHARED_VOTES:
                continue

            n_agree = (v1[both_voted] == v2[both_voted]).sum()
            agreement = n_agree / n_shared

            record = {
                "ms_code1"  : countries[idx1],
                "ms_code2"  : countries[idx2],
                "n_shared"  : int(n_shared),
                "agreement" : round(float(agreement), 4),
            }

            # Add group keys
            if isinstance(group_key, tuple):
                for col, val in zip(group_cols, group_key):
                    record[col] = val
            else:
                record[group_cols[0]] = group_key

            records.append(record)

    print()  # newline after progress
    return pd.DataFrame(records)


# ── 3. Overall agreement per year ─────────────────────────────────────────────

overall = compute_agreement(un_voted, ["year"])

print(f"  Pairs computed     : {len(overall):,}")
print(f"  Year range         : {overall['year'].min()} – {overall['year'].max()}")
print(f"\n  Agreement score distribution:")
print(overall["agreement"].describe(percentiles=[.1, .25, .5, .75, .9]).round(3).to_string())

latest = overall[overall["year"] == overall["year"].max()]
print(latest.nlargest(10, "agreement")[["ms_code1", "ms_code2", "n_shared", "agreement"]].to_string(index=False))

print(latest.nsmallest(10, "agreement")[["ms_code1", "ms_code2", "n_shared", "agreement"]].to_string(index=False))


# ── 4. Per-category agreement per year ───────────────────────────────────────

# Exclude Uncategorized and Other for category breakdown
un_cat = un_voted[~un_voted["subject_category"].isin(["Uncategorized", "Other"])]
print(f"  Rows used for category breakdown : {len(un_cat):,}")
print(f"\n  Computing agreement by year + category...")

by_category = compute_agreement(un_cat, ["year", "subject_category"])

print(by_category.groupby("subject_category").size().sort_values(ascending=False).to_string())

print(
    by_category.groupby("subject_category")["agreement"]
    .median()
    .sort_values(ascending=False)
    .round(3)
    .to_string()
)


# ── 5. Export CSVs ────────────────────────────────────────────────────────────

overall_cols = ["year", "ms_code1", "ms_code2", "n_shared", "agreement"]
overall[overall_cols].to_csv("data/processed/agreement_overall.csv", index=False)
print("  Exported: agreement_overall.csv")

cat_cols = ["year", "subject_category", "ms_code1", "ms_code2", "n_shared", "agreement"]
by_category[cat_cols].to_csv("data/processed/agreement_by_category.csv", index=False)
print("  Exported: agreement_by_category.csv")


# ── 6. Export NxN matrix JSON for D3 ─────────────────────────────────────────

latest_year = overall["year"].max()
latest_df   = overall[overall["year"] == latest_year].copy()

# Get all countries present in the latest year
all_codes = sorted(set(latest_df["ms_code1"].tolist() + latest_df["ms_code2"].tolist()))
code_to_idx = {code: i for i, code in enumerate(all_codes)}
n = len(all_codes)

# Build NxN matrix (default 0.5 = unknown, diagonal = 1.0)
matrix = np.full((n, n), np.nan)
np.fill_diagonal(matrix, 1.0)

for _, row in latest_df.iterrows():
    i = code_to_idx[row["ms_code1"]]
    j = code_to_idx[row["ms_code2"]]
    matrix[i, j] = row["agreement"]
    matrix[j, i] = row["agreement"]

# Serialise — replace NaN with null for JSON
matrix_list = [
    [None if np.isnan(v) else round(v, 4) for v in row]
    for row in matrix
]

output = {
    "year"      : int(latest_year),
    "countries" : all_codes,
    "matrix"    : matrix_list,
}

json_path = f"data/processed/agreement_matrix_{latest_year}.json"
with open(json_path, "w") as f:
    json.dump(output, f)

print(f"  Exported: {json_path}")
print(f"  Matrix size: {n} × {n} countries")
print(f"  NaN entries (pairs below threshold): {np.isnan(matrix).sum() - 0:,}")

# Export resolution counts per year
res_counts = (
    un_voted.groupby("year")["resolution"]
    .nunique()
    .reset_index()
    .rename(columns={"resolution": "n_resolutions"})
)
res_counts.to_csv("data/processed/resolution_counts.csv", index=False)
print("  Exported: resolution_counts.csv")