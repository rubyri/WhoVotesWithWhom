"""
UN General Assembly Voting Data — Full Pipeline
================================================
Cleaning, joining, subject classification, and pairwise
agreement computation. 

Output: votes.db 

Usage:
  python pipeline/pipeline.py              # full run
  python pipeline/pipeline.py --clean-only # skip agreement computation

Database output (data/processed/votes.db):
  ┌─ LOOKUP TABLES ──────────────────────────────────────────────┐
  │  countries     — ms_code, country_name, first_year, last_year│
  │  categories    — category_id, category_name                  │
  │  ideal_points  — ms_code, year, ideal_point, q5, q95         │
  │  resolution_counts — year, n_resolutions                     │
  ├─ FACT TABLES ────────────────────────────────────────────────┤
  │  agreement_overall      — year, ms_code1, ms_code2, ...      │
  │  agreement_by_category  — year, category_id, ms_code1, ...   │
  ├─ VIEWS ──────────────────────────────────────────────────────┤
  │  consensus_overall      — per-country avg agreement per year │
  │  consensus_by_category  — per-country avg per year+category  │
  ├─ MATERIALIZED TABLES ────────────────────────────────────────┤
  │  mat_consensus_overall      — pre-computed snapshot of view  │
  │  mat_consensus_by_category  — pre-computed snapshot of view  │
  └──────────────────────────────────────────────────────────────┘
"""

import sys
import os
import sqlite3
import pandas as pd
import numpy as np
from itertools import combinations
from subject_map import SUBJECT_MAP

UN_VOTES_PATH    = "data/raw/2026_02_06_ga_voting.csv"
IDEAL_POINTS_PATH = "data/raw/dataverse_files/Idealpointestimates1946-2025.csv"
DB_PATH          = "data/processed/votes.db"
MIN_SHARED_VOTES = 5

CLEAN_ONLY = "--clean-only" in sys.argv

def section(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def subsection(title):
    print(f"\n── {title} " + "─" * (60 - len(title)))


# ─────────────────────────────────────────────────────────────────────────────
#  PART 1 — CLEANING
# ─────────────────────────────────────────────────────────────────────────────

section("1. LOADING RAW DATA")

print("  Loading UN votes...")
un = pd.read_csv(UN_VOTES_PATH, low_memory=False)
print(f"  UN votes loaded      : {len(un):,} rows")

print("  Loading ideal points...")
ip = pd.read_csv(IDEAL_POINTS_PATH, low_memory=False)
print(f"  Ideal points loaded  : {len(ip):,} rows")


# ── 2. Clean UN votes ─────────────────────────────────────────────────────────

section("2. CLEANING UN VOTES")

# Parse dates
un["date"] = pd.to_datetime(un["date"], errors="coerce")
un["year"] = un["date"].dt.year

# Standardise vote column
un["ms_vote"] = un["ms_vote"].str.strip().str.upper()

subsection("Vote distribution")
print(un["ms_vote"].value_counts(dropna=False).to_string())

# Drop columns not needed for analysis (undl_link kept intentionally)
drop_cols = ["draft", "committee_report", "vote_note", "meeting"]
un = un.drop(columns=[c for c in drop_cols if c in un.columns])

# Canonical country name — most recent name per code
canonical_names = (
    un.sort_values("date")
    .groupby("ms_code")["ms_name"]
    .last()
    .rename("country_name")
)
un = un.drop(columns=["ms_name"]).join(canonical_names, on="ms_code")

# Numeric vote encoding: Y=1, N=-1, A=0, X=NaN
vote_map = {"Y": 1, "N": -1, "A": 0, "X": np.nan}
un["vote_num"] = un["ms_vote"].map(vote_map)
print(f"\n  Rows with valid numeric vote : {un['vote_num'].notna().sum():,}")
print(f"  Rows excluded (absent/X)     : {un['vote_num'].isna().sum():,}")


# ── 3. Subject classification ─────────────────────────────────────────────────

section("3. SUBJECT CLASSIFICATION")

def map_subject(subject_str):
    """
    Returns (broad_category, subcategory) for a raw subjects string.
    Subcategory is the first segment of the first UN tag (before '--'),
    title-cased. Falls back to ('Uncategorized', None) if subjects is NaN,
    or ('Other', first_tag) if no keyword matches.
    """
    if pd.isna(subject_str):
        return "Uncategorized", None
    tags = [t.strip() for t in subject_str.split("|")]
    first_tag = tags[0]
    subcategory = first_tag.split("--")[0].strip().title()
    for tag in tags:
        tag_upper = tag.upper()
        for keyword, category in SUBJECT_MAP:
            if keyword in tag_upper:
                return category, subcategory
    return "Other", subcategory

result = un["subjects"].apply(map_subject)
un["subject_category"]    = result.apply(lambda x: x[0])
un["subject_subcategory"] = result.apply(lambda x: x[1])

subsection("Category distribution")
cat_counts = un["subject_category"].value_counts()
cat_pcts   = (cat_counts / len(un) * 100).round(1)
print(pd.DataFrame({"count": cat_counts, "pct%": cat_pcts}).to_string())


# ── 4. Country code remaps ────────────────────────────────────────────────────

section("4. COUNTRY CODE REMAPS")

# West Germany (GER) → DEU in ideal points file
remap = {"GER": "DEU"}
un["ms_code_join"] = un["ms_code"].replace(remap)
print(f"  Remapped GER → DEU for join ({(un['ms_code']=='GER').sum()} rows)")


# ── 5. Join with ideal points ─────────────────────────────────────────────────

section("5. JOINING WITH IDEAL POINTS")

ip_join = (
    ip[["iso3c", "year", "IdealPointFP", "NVotesFP", "Q5%FP", "Q95%FP"]]
    .rename(columns={"iso3c": "ms_code_join"})
)
un_joined = un.merge(ip_join, on=["ms_code_join", "year"], how="left")

matched   = un_joined["IdealPointFP"].notna().sum()
unmatched = un_joined["IdealPointFP"].isna().sum()
print(f"  Matched   : {matched:,} ({matched/len(un_joined)*100:.1f}%)")
print(f"  Unmatched : {unmatched:,} ({unmatched/len(un_joined)*100:.1f}%)")


# ── 6. Build lookup tables ────────────────────────────────────────────────────

section("6. BUILDING LOOKUP TABLES")

# Country index
country_index = (
    un_joined.groupby("ms_code")
    .agg(
        country_name       = ("country_name", "last"),
        first_year         = ("year", "min"),
        last_year          = ("year", "max"),
        total_votes        = ("ms_vote", "count"),
        latest_ideal_point = ("IdealPointFP", "last"),
    )
    .reset_index()
)
print(f"  Countries : {len(country_index)}")

# Lean ideal points — one row per country per year
ideal_points_lean = (
    un_joined[["ms_code", "year", "IdealPointFP", "Q5%FP", "Q95%FP"]]
    .dropna(subset=["IdealPointFP"])
    .drop_duplicates(subset=["ms_code", "year"])
    .sort_values(["ms_code", "year"])
    .rename(columns={
        "IdealPointFP": "ideal_point",
        "Q5%FP":        "q5",
        "Q95%FP":       "q95",
    })
)
print(f"  Ideal point rows : {len(ideal_points_lean):,}")

# Resolution counts per year
un_voted_all = un_joined[un_joined["vote_num"].notna()].copy()
res_counts = (
    un_voted_all.groupby("year")["resolution"]
    .nunique()
    .reset_index()
    .rename(columns={"resolution": "n_resolutions"})
)
print(f"  Resolution count rows : {len(res_counts)}")

# Categories — exclude Uncategorized and Other
all_categories = sorted(
    un_joined["subject_category"]
    .dropna()
    .loc[lambda s: ~s.isin(["Uncategorized", "Other"])]
    .unique()
)
categories_df = pd.DataFrame({
    "category_id":   range(1, len(all_categories) + 1),
    "category_name": all_categories,
})
cat_to_id = dict(zip(categories_df["category_name"], categories_df["category_id"]))
print(f"  Categories : {len(categories_df)}")

# Resolution counts per year per category
res_counts_by_category = (
    un_voted_all[~un_voted_all["subject_category"].isin(["Uncategorized", "Other"])]
    .groupby(["year", "subject_category"])["resolution"]
    .nunique()
    .reset_index()
    .rename(columns={"resolution": "n_resolutions"})
)
res_counts_by_category["category_id"] = res_counts_by_category["subject_category"].map(cat_to_id)
res_counts_by_category = res_counts_by_category.drop(columns=["subject_category"])
print(f"  Resolution counts by category rows : {len(res_counts_by_category)}")

# ─────────────────────────────────────────────────────────────────────────────
#  PART 2 — AGREEMENT COMPUTATION (skipped with --clean-only)
# ─────────────────────────────────────────────────────────────────────────────

if CLEAN_ONLY:
    print("\n  --clean-only flag set — skipping agreement computation.")
    overall      = None
    by_category  = None
else:

    # ── 7. Core agreement function ────────────────────────────────────────────

    section("7. COMPUTING PAIRWISE AGREEMENT")

    def compute_agreement(df, group_cols, min_shared=5):
        records = []
        groups = df.groupby(group_cols)
        total_groups = len(groups)

        for i, (group_key, group_df) in enumerate(groups):
            if i % 10 == 0:
                print(f"    Processing group {i+1}/{total_groups} : {group_key}", end="\r")

            pivot = group_df.pivot_table(
                index="resolution",
                columns="ms_code",
                values="vote_num",
                aggfunc="first"
            )

            countries = pivot.columns.tolist()
            if len(countries) < 2:
                continue

            vote_matrix = pivot.values
            n_countries = len(countries)

            for idx1, idx2 in combinations(range(n_countries), 2):
                v1 = vote_matrix[:, idx1]
                v2 = vote_matrix[:, idx2]

                both_voted = ~(np.isnan(v1) | np.isnan(v2))
                n_shared   = both_voted.sum()

                if n_shared < min_shared:
                    continue

                n_agree   = (v1[both_voted] == v2[both_voted]).sum()
                agreement = n_agree / n_shared

                record = {
                    "ms_code1"  : countries[idx1],
                    "ms_code2"  : countries[idx2],
                    "n_shared"  : int(n_shared),
                    "agreement" : round(float(agreement), 4),
                }
                if isinstance(group_key, tuple):
                    for col, val in zip(group_cols, group_key):
                        record[col] = val
                else:
                    record[group_cols[0]] = group_key

                records.append(record)

        print()
        return pd.DataFrame(records)

    # Overall
    subsection("Overall agreement")
    overall      = compute_agreement(un_voted_all, ["year"], min_shared=5)
    print(f"  Pairs computed : {len(overall):,}")
    print(f"  Year range     : {overall['year'].min()} – {overall['year'].max()}")

    subsection("Agreement distribution")
    print(overall["agreement"].describe(percentiles=[.1, .25, .5, .75, .9]).round(3).to_string())

    subsection("Most similar pairs in latest year")
    latest = overall[overall["year"] == overall["year"].max()]
    print(latest.nlargest(10, "agreement")[["ms_code1", "ms_code2", "n_shared", "agreement"]].to_string(index=False))

    subsection("Most dissimilar pairs in latest year")
    print(latest.nsmallest(10, "agreement")[["ms_code1", "ms_code2", "n_shared", "agreement"]].to_string(index=False))

    # Per category
    subsection("Per-category agreement")
    un_cat = un_voted_all[~un_voted_all["subject_category"].isin(["Uncategorized", "Other"])]
    print(f"  Rows used : {len(un_cat):,}")

    by_category_raw = compute_agreement(un_cat, ["year", "subject_category"], min_shared=2)

    # Replace category string with integer foreign key
    by_category = by_category_raw.copy()
    by_category["category_id"] = by_category["subject_category"].map(cat_to_id)
    by_category = by_category.drop(columns=["subject_category"])

    subsection("Median agreement by category")
    print(
        by_category_raw.groupby("subject_category")["agreement"]
        .median()
        .sort_values(ascending=False)
        .round(3)
        .to_string()
    )


# ─────────────────────────────────────────────────────────────────────────────
#  PART 3 — EXPORT TO SQLITE
# ─────────────────────────────────────────────────────────────────────────────

section("8. EXPORTING TO SQLITE")

os.makedirs("data/processed", exist_ok=True)
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

conn = sqlite3.connect(DB_PATH)

# ── Lookup tables ─────────────────────────────────────────────────────────────

print("  Writing countries...")
country_index[["ms_code", "country_name", "first_year", "last_year"]].to_sql(
    "countries", conn, if_exists="replace", index=False)

print("  Writing categories...")
categories_df.to_sql("categories", conn, if_exists="replace", index=False)

print("  Writing ideal_points...")
ideal_points_lean.to_sql("ideal_points", conn, if_exists="replace", index=False)

print("  Writing resolution_counts...")
res_counts.to_sql("resolution_counts", conn, if_exists="replace", index=False)

print("  Writing resolution_counts_by_category...")
res_counts_by_category[["year", "category_id", "n_resolutions"]].to_sql(
    "resolution_counts_by_category", conn, if_exists="replace", index=False)
conn.execute("CREATE INDEX idx_rcbc_year ON resolution_counts_by_category(year)")
conn.execute("CREATE INDEX idx_rcbc_cat  ON resolution_counts_by_category(category_id)")

# ── Fact tables (only if full run) ────────────────────────────────────────────

if not CLEAN_ONLY:
    print("  Writing agreement_overall...")
    overall[["year", "ms_code1", "ms_code2", "n_shared", "agreement"]].to_sql(
        "agreement_overall", conn, if_exists="replace", index=False)

    print("  Writing agreement_by_category...")
    by_category[["year", "category_id", "ms_code1", "ms_code2", "n_shared", "agreement"]].to_sql(
        "agreement_by_category", conn, if_exists="replace", index=False)

# ── Indexes ───────────────────────────────────────────────────────────────────

print("  Adding indexes...")
conn.execute("CREATE INDEX idx_ip_year   ON ideal_points(year)")
conn.execute("CREATE INDEX idx_ip_code   ON ideal_points(ms_code)")

if not CLEAN_ONLY:
    conn.execute("CREATE INDEX idx_oa_year   ON agreement_overall(year)")
    conn.execute("CREATE INDEX idx_oa_c1     ON agreement_overall(ms_code1)")
    conn.execute("CREATE INDEX idx_oa_c2     ON agreement_overall(ms_code2)")
    conn.execute("CREATE INDEX idx_cat_year  ON agreement_by_category(year)")
    conn.execute("CREATE INDEX idx_cat_catid ON agreement_by_category(category_id)")
    conn.execute("CREATE INDEX idx_cat_c1    ON agreement_by_category(ms_code1)")
    conn.execute("CREATE INDEX idx_cat_c2    ON agreement_by_category(ms_code2)")

# ── Views (only if full run) ──────────────────────────────────────────────────

if not CLEAN_ONLY:
    print("  Creating views...")

    conn.execute("""
    CREATE VIEW consensus_overall AS
    SELECT
        year,
        ms_code,
        ROUND(AVG(agreement), 4) AS consensus,
        COUNT(*)                 AS n_pairs
    FROM (
        SELECT year, ms_code1 AS ms_code, agreement FROM agreement_overall
        UNION ALL
        SELECT year, ms_code2 AS ms_code, agreement FROM agreement_overall
    )
    GROUP BY year, ms_code
    """)

    conn.execute("""
    CREATE VIEW consensus_by_category AS
    SELECT
        a.year,
        c.category_name,
        a.ms_code,
        ROUND(AVG(a.agreement), 4) AS consensus,
        COUNT(*)                   AS n_pairs
    FROM (
        SELECT year, category_id, ms_code1 AS ms_code, agreement
        FROM agreement_by_category
        UNION ALL
        SELECT year, category_id, ms_code2 AS ms_code, agreement
        FROM agreement_by_category
    ) a
    JOIN categories c ON a.category_id = c.category_id
    GROUP BY a.year, c.category_name, a.ms_code
    """)

    conn.execute("""
    CREATE VIEW resolution_counts_named AS
    SELECT r.year, c.category_name, r.n_resolutions
    FROM resolution_counts_by_category r
    JOIN categories c ON r.category_id = c.category_id
    """)

# ── Materialized tables (only if full run) ────────────────────────────────────

if not CLEAN_ONLY:
    print("  Materializing views...")

    conn.execute("""
    CREATE TABLE mat_consensus_overall AS
    SELECT * FROM consensus_overall
    """)

    conn.execute("""
    CREATE TABLE mat_consensus_by_category AS
    SELECT * FROM consensus_by_category
    """)

    conn.execute("CREATE INDEX idx_mco_year  ON mat_consensus_overall(year)")
    conn.execute("CREATE INDEX idx_mco_code  ON mat_consensus_overall(ms_code)")
    conn.execute("CREATE INDEX idx_mcbc_year ON mat_consensus_by_category(year)")
    conn.execute("CREATE INDEX idx_mcbc_cat  ON mat_consensus_by_category(category_name)")
    conn.execute("CREATE INDEX idx_mcbc_code ON mat_consensus_by_category(ms_code)")

conn.commit()

# ── Summary ───────────────────────────────────────────────────────────────────

subsection("Table row counts")
tables = ["countries", "categories", "ideal_points", "resolution_counts"]
if not CLEAN_ONLY:
    tables += [
        "agreement_overall", "agreement_by_category",
        "mat_consensus_overall", "mat_consensus_by_category",
    ]
for t in tables:
    count = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"  {t:35s} : {count:,}")

conn.close()

size_mb = os.path.getsize(DB_PATH) / 1024 / 1024
print(f"\n  Exported: {DB_PATH} ({size_mb:.1f} MB)")
if CLEAN_ONLY:
    print("  Note: agreement tables omitted (--clean-only mode)")
print("\n  Done.")



