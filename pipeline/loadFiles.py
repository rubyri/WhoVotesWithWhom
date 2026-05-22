"""
UN General Assembly Voting Data — Initial Inspection
=====================================================
Loads the primary UN voting dataset and the Voeten ideal point estimates,
runs basic inspection, and reports potential data quality issues.

Expected files:
  - 2026_02_06_ga_voting.csv
  - dataverse_files/Idealpointestimates1946-2025.csv

  Generated with Sonnet 4.6
"""

import pandas as pd
import numpy as np

# ── Configuration ────────────────────────────────────────────────────────────

UN_VOTES_PATH     = "data/raw/2026_02_06_ga_voting.csv"
IDEAL_POINTS_PATH = "data/raw/dataverse_files/Idealpointestimates1946-2025.csv"

# ── Helpers ───────────────────────────────────────────────────────────────────

def section(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def subsection(title):
    print(f"\n── {title} " + "─" * (60 - len(title)))


# ── 1. Load data ──────────────────────────────────────────────────────────────

section("1. LOADING DATA")

print("\nLoading UN voting data ...")
un = pd.read_csv(UN_VOTES_PATH, low_memory=False)
print(f"  Rows: {len(un):,}  |  Columns: {un.shape[1]}")

print("\nLoading Voeten ideal point estimates ...")
ip = pd.read_csv(IDEAL_POINTS_PATH, low_memory=False)
print(f"  Rows: {len(ip):,}  |  Columns: {ip.shape[1]}")


# ── 2. Basic structure ────────────────────────────────────────────────────────

section("2. COLUMN OVERVIEW")

subsection("UN votes — dtypes")
print(un.dtypes.to_string())

subsection("Ideal points — dtypes")
print(ip.dtypes.to_string())


# ── 3. Missing values ─────────────────────────────────────────────────────────

section("3. MISSING VALUES")

subsection("UN votes — null counts")
null_un = un.isnull().sum()
null_un = null_un[null_un > 0]
print(null_un.to_string() if len(null_un) else "  No missing values found.")

subsection("Ideal points — null counts")
null_ip = ip.isnull().sum()
null_ip = null_ip[null_ip > 0]
print(null_ip.to_string() if len(null_ip) else "  No missing values found.")


# ── 4. Vote value distribution ────────────────────────────────────────────────

section("4. VOTE VALUE DISTRIBUTION (ms_vote)")

vote_counts = un["ms_vote"].value_counts(dropna=False)
vote_pct    = (vote_counts / len(un) * 100).round(2)
vote_summary = pd.DataFrame({"count": vote_counts, "pct": vote_pct})
print(vote_summary.to_string())


# ── 5. Temporal coverage ──────────────────────────────────────────────────────

section("5. TEMPORAL COVERAGE")

# Parse date column
un["date"] = pd.to_datetime(un["date"], errors="coerce")
un["year"] = un["date"].dt.year

subsection("UN votes — year range")
print(f"  Earliest: {un['year'].min()}  |  Latest: {un['year'].max()}")
print(f"  Date parse failures: {un['date'].isnull().sum():,}")

subsection("UN votes — votes per year (first and last 5)")
vpy = un.groupby("year").size().rename("n_votes")
print("  First 5 years:")
print(vpy.head().to_string())
print("  Last 5 years:")
print(vpy.tail().to_string())

subsection("Ideal points — year range")
print(f"  Earliest: {ip['year'].min()}  |  Latest: {ip['year'].max()}")


# ── 6. Country coverage ───────────────────────────────────────────────────────

section("6. COUNTRY COVERAGE")

subsection("UN votes")
print(f"  Unique ms_code values : {un['ms_code'].nunique()}")
print(f"  Unique ms_name values : {un['ms_name'].nunique()}")

subsection("Ideal points")
print(f"  Unique iso3c values   : {ip['iso3c'].nunique()}")
print(f"  Unique Countryname    : {ip['Countryname'].nunique()}")


# ── 7. Subject tag coverage ───────────────────────────────────────────────────

section("7. SUBJECT TAG COVERAGE")

total = len(un)
has_subject = un["subjects"].notna().sum()
print(f"  Rows with subject tag : {has_subject:,} ({has_subject/total*100:.1f}%)")
print(f"  Rows without          : {total - has_subject:,} ({(total-has_subject)/total*100:.1f}%)")

subsection("Top 20 subject tags")
# Tags can be pipe-separated — split and explode to count individually
tags = (
    un["subjects"]
    .dropna()
    .str.split("|")
    .explode()
    .str.strip()
)
print(tags.value_counts().head(20).to_string())


# ── 8. Resolution-level stats ─────────────────────────────────────────────────

section("8. RESOLUTION-LEVEL STATS")

resolutions = un.drop_duplicates(subset="resolution")
print(f"  Unique resolutions: {len(resolutions):,}")

subsection("Agreement rate distribution (total_yes / total_ms)")
resolutions = resolutions.copy()
resolutions["agree_rate"] = resolutions["total_yes"] / resolutions["total_ms"]
desc = resolutions["agree_rate"].describe(percentiles=[.1, .25, .5, .75, .9])
print(desc.round(3).to_string())
print("\n  NOTE: High median agreement rate is expected — see proposal section 3.2.")


# ── 9. Ideal point distribution ───────────────────────────────────────────────

section("9. IDEAL POINT DISTRIBUTION")

desc_ip = ip["IdealPointFP"].describe(percentiles=[.1, .25, .5, .75, .9])
print(desc_ip.round(3).to_string())

subsection("Countries with highest ideal points (most Western-aligned, latest year)")
latest_year = ip["year"].max()
ip_latest = ip[ip["year"] == latest_year].sort_values("IdealPointFP", ascending=False)
print(ip_latest[["Countryname", "iso3c", "IdealPointFP"]].head(10).to_string(index=False))

subsection("Countries with lowest ideal points (least Western-aligned, latest year)")
print(ip_latest[["Countryname", "iso3c", "IdealPointFP"]].tail(10).to_string(index=False))


# ── 10. Join feasibility check ────────────────────────────────────────────────

section("10. JOIN FEASIBILITY: ms_code (UN) vs iso3c (Ideal Points)")

un_codes = set(un["ms_code"].dropna().unique())
ip_codes = set(ip["iso3c"].dropna().unique())

matched   = un_codes & ip_codes
only_un   = un_codes - ip_codes
only_ip   = ip_codes - un_codes

print(f"  UN codes              : {len(un_codes)}")
print(f"  Ideal point iso3c     : {len(ip_codes)}")
print(f"  Matched               : {len(matched)}")
print(f"  Only in UN (no match) : {len(only_un)}")
print(f"  Only in ideal points  : {len(only_ip)}")

if only_un:
    print(f"\n  UN codes with no ideal point match (first 30):")
    print("  ", sorted(only_un)[:30])
