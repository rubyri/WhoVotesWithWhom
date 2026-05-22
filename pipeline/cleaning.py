"""
UN General Assembly Voting Data 
=========================================================
Outputs:
  - un_clean.csv            : cleaned UN votes, one row per country-resolution
  - un_with_idealpoints.csv : UN votes joined with ideal point estimates
  - country_index.csv       : one row per country with metadata

This file only needs to be run once to produce the cleaned and joined datasets. 

The subject mapping is done manually and can be changed.

"""

import pandas as pd
import numpy as np

UN_VOTES_PATH     = "data/raw/2026_02_06_ga_voting.csv"
IDEAL_POINTS_PATH = "data/raw/dataverse_files/Idealpointestimates1946-2025.csv"


# ── Subject mapping ───────────────────────────────────────────────────────────
# Keys are matched against the uppercased raw subject string (substring match).
# Order matters — first match wins. More specific keys should come before
# broader ones (e.g. "MIDDLE EAST--NUCLEAR" before "MIDDLE EAST").

SUBJECT_MAP = [
    # ── Social, Humanitarian & Cultural (Third Committee) ─────────────────────
    ("HUMAN RIGHTS",                                    "Social, Humanitarian & Cultural"),
    ("RACIAL DISCRIMINATION",                           "Social, Humanitarian & Cultural"),
    ("RIGHTS OF THE CHILD",                             "Social, Humanitarian & Cultural"),
    ("WOMEN'S ADVANCEMENT",                             "Social, Humanitarian & Cultural"),
    ("WOMEN--",                                         "Social, Humanitarian & Cultural"),
    ("INDIGENOUS PEOPLE",                               "Social, Humanitarian & Cultural"),
    ("TORTURE",                                         "Social, Humanitarian & Cultural"),
    ("REFUGEES",                                        "Social, Humanitarian & Cultural"),
    ("MIGRATION",                                       "Social, Humanitarian & Cultural"),
    ("ELECTIONS",                                       "Social, Humanitarian & Cultural"),
    ("SOCIAL DEVELOPMENT",                              "Social, Humanitarian & Cultural"),
    ("SOCIAL CONDITIONS",                               "Social, Humanitarian & Cultural"),
    ("HEALTH",                                          "Social, Humanitarian & Cultural"),
    ("HUMAN SETTLEMENTS",                               "Social, Humanitarian & Cultural"),
    ("CULTURE--",                                       "Social, Humanitarian & Cultural"),
    ("CULTURAL PROPERTY",                               "Social, Humanitarian & Cultural"),
    ("FOOD",                                            "Social, Humanitarian & Cultural"),
    ("RIGHT TO FOOD",                                   "Social, Humanitarian & Cultural"),
    ("FOOD SECURITY",                                   "Social, Humanitarian & Cultural"),
    ("SCIENCE AND TECHNOLOGY--HUMAN RIGHTS",            "Social, Humanitarian & Cultural"),

    # ── Palestine & Middle East (UN Plenary — special status) ─────────────────
    ("TERRITORIES OCCUPIED BY ISRAEL",                  "Palestine & Middle East"),
    ("UNRWA",                                           "Palestine & Middle East"),
    ("PALESTINE QUESTION",                              "Palestine & Middle East"),
    ("MIDDLE EAST SITUATION",                           "Palestine & Middle East"),
    ("MIDDLE EAST--",                                   "Palestine & Middle East"),
    ("GOLAN HEIGHTS",                                   "Palestine & Middle East"),

    # ── Disarmament & International Security (First Committee) ────────────────
    ("DISARMAMENT",                                     "Disarmament & International Security"),
    ("NUCLEAR WEAPON",                                  "Disarmament & International Security"),
    ("NUCLEAR NON-PROLIFERATION",                       "Disarmament & International Security"),
    ("NUCLEAR-WEAPON-FREE ZONES",                       "Disarmament & International Security"),
    ("NON-NUCLEAR-WEAPON STATES",                       "Disarmament & International Security"),
    ("FISSIONABLE MATERIALS",                           "Disarmament & International Security"),
    ("DEPLETED URANIUM",                                "Disarmament & International Security"),
    ("COMPREHENSIVE NUCLEAR-TEST-BAN",                  "Disarmament & International Security"),
    ("ARMS RACE",                                       "Disarmament & International Security"),
    ("ARMS TRANSFERS",                                  "Disarmament & International Security"),
    ("CONVENTIONAL ARMS",                               "Disarmament & International Security"),
    ("CONVENTIONAL WEAPONS",                            "Disarmament & International Security"),
    ("MILITARY BUDGETS",                                "Disarmament & International Security"),
    ("VERIFICATION",                                    "Disarmament & International Security"),
    ("LANDMINES",                                       "Disarmament & International Security"),
    ("CLUSTER MUNITIONS",                               "Disarmament & International Security"),
    ("CHEMICAL WEAPONS",                                "Disarmament & International Security"),
    ("CHEMICAL AND BIOLOGICAL WARFARE",                 "Disarmament & International Security"),
    ("BIOLOGICAL WEAPONS",                              "Disarmament & International Security"),
    ("WEAPONS OF MASS DESTRUCTION",                     "Disarmament & International Security"),
    ("BALLISTIC MISSILES",                              "Disarmament & International Security"),
    ("IAEA",                                            "Disarmament & International Security"),
    ("WEAPONS--OUTER SPACE",                            "Disarmament & International Security"),
    ("ARMS RACE--OUTER SPACE",                          "Disarmament & International Security"),
    ("OUTER SPACE--ARMS RACE",                          "Disarmament & International Security"),
    ("OUTER SPACE--CONFIDENCE-BUILDING",                "Disarmament & International Security"),
    ("PEACE--CONVENTIONAL DISARMAMENT",                 "Disarmament & International Security"),
    ("SCIENCE AND TECHNOLOGY--INTERNATIONAL SECURITY",  "Disarmament & International Security"),
    ("SCIENCE AND TECHNOLOGY--DISARMAMENT",             "Disarmament & International Security"),
    ("INFORMATION--INTERNATIONAL SECURITY",             "Disarmament & International Security"),

    # ── Special Political & Decolonization (Fourth Committee) ────────────────
    ("DECOLONIZATION",                                  "Special Political & Decolonization"),
    ("SELF-DETERMINATION",                              "Special Political & Decolonization"),
    ("NON-SELF-GOVERNING TERRITORIES",                  "Special Political & Decolonization"),
    ("COLONIAL COUNTRIES",                              "Special Political & Decolonization"),
    ("APARTHEID",                                       "Special Political & Decolonization"),
    ("NAMIBIA",                                         "Special Political & Decolonization"),
    ("COMORIAN ISLAND",                                 "Special Political & Decolonization"),
    ("FALKLAND ISLANDS",                                "Special Political & Decolonization"),
    ("NATIONAL LIBERATION MOVEMENTS",                   "Special Political & Decolonization"),

    # ── Economic & Financial (Second Committee) ───────────────────────────────
    ("SUSTAINABLE DEVELOPMENT",                         "Economic & Financial"),
    ("AGENDA 21",                                       "Economic & Financial"),
    ("INTERNATIONAL TRADE",                             "Economic & Financial"),
    ("EXTERNAL DEBT",                                   "Economic & Financial"),
    ("COMMODITIES",                                     "Economic & Financial"),
    ("INDUSTRIAL DEVELOPMENT",                          "Economic & Financial"),
    ("TAXATION",                                        "Economic & Financial"),
    ("LAW OF THE SEA",                                  "Economic & Financial"),
    ("GLOBALIZATION",                                   "Economic & Financial"),
    ("ECONOMIC ASSISTANCE",                             "Economic & Financial"),
    ("ECONOMIC COOPERATION",                            "Economic & Financial"),
    ("ECONOMIC DEVELOPMENT",                            "Economic & Financial"),
    ("NEW INTERNATIONAL ECONOMIC ORDER",                "Economic & Financial"),
    ("DEVELOPMENT FINANCE",                             "Economic & Financial"),
    ("POVERTY",                                         "Economic & Financial"),
    ("AGRICULTURE",                                     "Economic & Financial"),
    ("AFRICA--DEVELOPMENT",                             "Economic & Financial"),
    ("SCIENCE AND TECHNOLOGY--DEVELOPMENT",             "Economic & Financial"),
    ("INFORMATION TECHNOLOGY--DEVELOPMENT",             "Economic & Financial"),

    # ── Environment & Climate ─────────────────────────────────────────────────
    ("CLIMATE CHANGE",                                  "Environment & Climate"),
    ("ENVIRONMENT",                                     "Environment & Climate"),
    ("STORMS",                                          "Environment & Climate"),
    ("DISASTER",                                        "Environment & Climate"),
    ("MARINE ECOSYSTEMS",                               "Environment & Climate"),
    ("SUSTAINABLE ENERGY",                              "Environment & Climate"),

    # ── International Peace & Security (UN Agenda section 1) ─────────────────
    ("INTERNATIONAL SECURITY",                          "International Peace & Security"),
    ("REGIONAL SECURITY",                               "International Peace & Security"),
    ("PEACE",                                           "International Peace & Security"),
    ("ARMED CONFLICTS",                                 "International Peace & Security"),
    ("CUBA--UNITED STATES",                             "International Peace & Security"),
    ("NICARAGUA--UNITED STATES",                        "International Peace & Security"),
    ("INDIAN OCEAN--ZONES OF PEACE",                    "International Peace & Security"),
    ("SOUTH ATLANTIC OCEAN REGION--ZONES OF PEACE",     "International Peace & Security"),
    ("UKRAINE--POLITICAL",                              "International Peace & Security"),
    ("AGGRESSION",                                      "International Peace & Security"),
    ("TERRORISM",                                       "International Peace & Security"),
    ("PEACEKEEPING",                                    "International Peace & Security"),
    ("CRIME PREVENTION",                                "International Peace & Security"),
    ("ILLICIT TRAFFIC",                                 "International Peace & Security"),
    ("UN DISENGAGEMENT OBSERVER FORCE",                 "International Peace & Security"),
    ("COLLECTIVE SECURITY",                             "International Peace & Security"),
    ("FORCE IN INTERNATIONAL RELATIONS",                "International Peace & Security"),
    ("ECONOMIC SANCTIONS",                              "International Peace & Security"),
    ("SITUATION",                                       "International Peace & Security"),

    # ── Global Governance (own construct) ────────────────────────────────────
    ("OUTER SPACE--PRINCIPLES",                         "Global Governance"),
    ("OUTER SPACE--PEACEFUL USES",                      "Global Governance"),
    ("ANTARCTICA",                                      "Global Governance"),
    ("INTERNET",                                        "Global Governance"),
    ("CYBERSPACE",                                      "Global Governance"),
    ("ORGANIZATION FOR SECURITY AND COOPERATION",       "Global Governance"),
    ("INTERNATIONAL CRIMINAL COURT",                    "Global Governance"),
    ("DISPUTE SETTLEMENT",                              "Global Governance"),
    ("GOOD NEIGHBOURLINESS",                            "Global Governance"),
    ("INFORMATION",                                     "Global Governance"),

    # ── Administrative, Budgetary & Legal (Fifth + Sixth Committee) ──────────
    ("UN--FINANCIAL SITUATION",                         "Administrative, Budgetary & Legal"),
    ("UN. ECONOMIC AND SOCIAL COUNCIL",                 "Administrative, Budgetary & Legal"),
    ("UN INTERIM FORCE",                                "Administrative, Budgetary & Legal"),
    ("UN CONFERENCES",                                  "Administrative, Budgetary & Legal"),
    ("UN--BUDGET",                                      "Administrative, Budgetary & Legal"),
    ("UN CHARTER",                                      "Administrative, Budgetary & Legal"),
    ("UN SYSTEM",                                       "Administrative, Budgetary & Legal"),
    ("UN REFORM",                                       "Administrative, Budgetary & Legal"),
    ("UNITED NATIONS--REFORM",                          "Administrative, Budgetary & Legal"),
    ("ORGANIZATION FOR DEMOCRACY",                      "Administrative, Budgetary & Legal"),
    ("UN. COMMITTEE",                                   "Administrative, Budgetary & Legal"),
    ("COUNCIL OF EUROPE--UN",                           "Administrative, Budgetary & Legal"),
    ("LEAGUE OF ARAB STATES",                           "Administrative, Budgetary & Legal"),
    ("PUBLIC INFORMATION",                              "Administrative, Budgetary & Legal"),
    ("PEACEKEEPING OPERATIONS--FIN",                    "Administrative, Budgetary & Legal"),
    ("PEACEKEEPING OPERATIONS--REIMB",                  "Administrative, Budgetary & Legal"),
    ("PEACE AND SECURITY--CODE",                        "Administrative, Budgetary & Legal"),
]


def map_subject(subject_str):
    """
    Returns (broad_category, subcategory) for a raw subjects string.
    Subcategory is the first segment of the first UN tag (before '--'),
    title-cased. Falls back to ('Uncategorized', None) if subjects is NaN,
    or ('Other', first_tag) if no keyword matches.
    """
    if pd.isna(subject_str):
        return "Uncategorized", None

    # All tags for this resolution (pipe-separated)
    tags = [t.strip() for t in subject_str.split("|")]

    # Subcategory = first segment of first tag, title-cased
    first_tag = tags[0]
    subcategory = first_tag.split("--")[0].strip().title()

    # Find broad category - first keyword match across all tags
    for tag in tags:
        tag_upper = tag.upper()
        for keyword, category in SUBJECT_MAP:
            if keyword in tag_upper:
                return category, subcategory

    return "Other", subcategory


# ── 1. Load ───────────────────────────────────────────────────────────────────

un = pd.read_csv(UN_VOTES_PATH, low_memory=False)
ip = pd.read_csv(IDEAL_POINTS_PATH, low_memory=False)
print(f"  UN votes loaded      : {len(un):,} rows")
print(f"  Ideal points loaded  : {len(ip):,} rows")


# ── 2. Clean UN votes ─────────────────────────────────────────────────────────

# Parse date and extract year
un["date"] = pd.to_datetime(un["date"], errors="coerce")
un["year"] = un["date"].dt.year

# Standardise vote column - uppercase, strip whitespace
un["ms_vote"] = un["ms_vote"].str.strip().str.upper()

print(un["ms_vote"].value_counts(dropna=False).to_string())

# Drop columns not needed for analysis 
drop_cols = ["draft", "committee_report", "vote_note", "meeting"]
un = un.drop(columns=[c for c in drop_cols if c in un.columns])
print(f"\n  Dropped columns      : {drop_cols}")
print(f"  Remaining columns    : {list(un.columns)}")

# Canonical country name - most recent name per code
name_variants = (
    un.groupby("ms_code")["ms_name"]
    .nunique()
    .sort_values(ascending=False)
)
print(name_variants[name_variants > 1].head(10).to_string())

canonical_names = (
    un.sort_values("date")
    .groupby("ms_code")["ms_name"]
    .last()
    .rename("country_name")
)
un = un.drop(columns=["ms_name"]).join(canonical_names, on="ms_code")

# Numeric vote encoding
# Y=1, N=-1, A=0, X=NaN (absent - excluded from agreement calculations)
vote_map = {"Y": 1, "N": -1, "A": 0, "X": np.nan}
un["vote_num"] = un["ms_vote"].map(vote_map)
print("  Y → 1  |  N → -1  |  A → 0  |  X → NaN (excluded)")
print(f"  Rows with valid numeric vote : {un['vote_num'].notna().sum():,}")
print(f"  Rows excluded (absent/X)     : {un['vote_num'].isna().sum():,}")


# ── 3. Subject classification ─────────────────────────────────────────────────

result = un["subjects"].apply(map_subject)
un["subject_category"]    = result.apply(lambda x: x[0])
un["subject_subcategory"] = result.apply(lambda x: x[1])

cat_counts = un["subject_category"].value_counts()
cat_pcts   = (cat_counts / len(un) * 100).round(1)
summary = pd.DataFrame({"count": cat_counts, "pct%": cat_pcts})
print(summary.to_string())

other_tags = (
    un[un["subject_category"] == "Other"]["subjects"]
    .dropna()
    .str.split("|")
    .explode()
    .str.strip()
)
print(other_tags.value_counts().head(20).to_string())


# ── 4. Manual country code remaps before join ─────────────────────────────────

# West Germany (GER) → DEU in ideal points file
# Serbia (SRB) → check if present under SCG (Serbia & Montenegro) pre-2006
remap = {"GER": "DEU"}

# Check SRB in ideal points
srb_in_ip = ip[ip["iso3c"] == "SRB"]
scg_in_ip = ip[ip["iso3c"] == "SCG"]
print(f"  SRB rows in ideal points : {len(srb_in_ip)}")
print(f"  SCG rows in ideal points : {len(scg_in_ip)}")
if len(scg_in_ip) > 0:
    print(f"  SCG year range           : {scg_in_ip['year'].min()}–{scg_in_ip['year'].max()}")
    # Don't remap SRB → SCG as they are distinct entities; just note the gap

# Apply remaps to a join-key column (don't modify original ms_code)
un["ms_code_join"] = un["ms_code"].replace(remap)
print(f"\n  Remapped GER → DEU for join ({(un['ms_code']=='GER').sum()} rows)")


# ── 5. Join with ideal points ─────────────────────────────────────────────────

ip_join = ip[["iso3c", "year", "IdealPointFP", "NVotesFP", "Q5%FP", "Q95%FP"]].copy()
ip_join = ip_join.rename(columns={"iso3c": "ms_code_join"})

un_joined = un.merge(ip_join, on=["ms_code_join", "year"], how="left")

matched   = un_joined["IdealPointFP"].notna().sum()
unmatched = un_joined["IdealPointFP"].isna().sum()
print(f"  Matched   : {matched:,} ({matched/len(un_joined)*100:.1f}%)")
print(f"  Unmatched : {unmatched:,} ({unmatched/len(un_joined)*100:.1f}%)")

unmatched_codes = (
    un_joined[un_joined["IdealPointFP"].isna()]["ms_code"]
    .value_counts()
    .head(15)
)
print(unmatched_codes.to_string())


# ── 6. Build country index ────────────────────────────────────────────────────

country_index = (
    un_joined.groupby("ms_code")
    .agg(
        country_name        = ("country_name", "last"),
        first_year          = ("year", "min"),
        last_year           = ("year", "max"),
        total_votes         = ("ms_vote", "count"),
        latest_ideal_point  = ("IdealPointFP", "last"),
    )
    .reset_index()
)
print(f"  Countries in index : {len(country_index)}")
print(f"\n  Sample (sorted by latest ideal point, descending):")
print(
    country_index.sort_values("latest_ideal_point", ascending=False)
    .head(10)[["ms_code", "country_name", "first_year", "latest_ideal_point"]]
    .to_string(index=False)
)


# ── 7. Export ─────────────────────────────────────────────────────────────────

un_clean_cols = [
    "undl_id", "ms_code", "country_name", "ms_vote", "vote_num",
    "date", "year", "session", "resolution", "title",
    "agenda_title", "subjects", "subject_category", "subject_subcategory",
    "total_yes", "total_no", "total_abstentions", "total_non_voting", "total_ms",
    "undl_link"
]
un[un_clean_cols].to_csv("data/processed/un_clean.csv", index=False)
print("  Exported: un_clean.csv")

joined_cols = un_clean_cols + ["IdealPointFP", "NVotesFP", "Q5%FP", "Q95%FP"]
un_joined[joined_cols].to_csv("data/processed/un_with_idealpoints.csv", index=False)
print("  Exported: un_with_idealpoints.csv")

country_index.to_csv("data/processed/country_index.csv", index=False)
print("  Exported: country_index.csv")


# import pandas as pd
# un = pd.read_csv("un_clean.csv", low_memory=False)

# # Find all unique subject tags containing a keyword
# keyword = "CULTURE"
# matches = (
#     un["subjects"]
#     .dropna()
#     .str.split("|")
#     .explode()
#     .str.strip()
#     .loc[lambda s: s.str.upper().str.contains(keyword)]
#     .value_counts()
# )
# print(matches.head(20))
