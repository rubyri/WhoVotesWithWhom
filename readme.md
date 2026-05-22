# Who Votes With Whom
**Geopolitical Alignment in the UN General Assembly**

Interactive visualization of UN General Assembly voting patterns, 1946–2025.

---

## Setup

### Step 1 — Inspect the data
```
python loadFiles.py
```
Loads the raw UN voting CSV and ideal point estimates, prints basic statistics and a join feasibility check.

### Step 2 — Clean and join
```
python cleaning.py
```
Cleans the raw data, assigns subject categories, joins with ideal point estimates, and exports three files:
- `un_clean.csv`
- `un_with_idealpoints.csv`
- `country_index.csv`

### Step 3 — Compute similarity scores
```
python similarityscores.py
```
Computes pairwise voting agreement scores between all country pairs, overall and per subject category. Exports:
- `agreement_overall.csv`
- `agreement_by_category.csv`
- `agreement_matrix_YYYY.json`

---

## Running the Visualization

From the project folder, start a local server:
```
python -m http.server 8000
```

Then open your browser and go to:
```
http://localhost:8000/map.html
```

---

## Data Sources

- UN Dag Hammarskjöld Library — *General Assembly Voting Data*, version 5, February 2026. [digitallibrary.un.org](https://digitallibrary.un.org/record/4060887)
- Voeten, Strezhnev, Bailey — *UN General Assembly Ideal Point Estimates*, Harvard Dataverse. [doi:10.7910/DVN/LEJUQZ](https://doi.org/10.7910/DVN/LEJUQZ)