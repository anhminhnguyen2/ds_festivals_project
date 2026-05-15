# ds_festivals_project

The purpose of this project is to help music lovers to predict the line up of their next festivals. The data will be collected from previous year's line up and the popularity of the artists to accurately predict the current/next year line up.

Tutorials videos from [YouTube](https://www.youtube.com):
- Ken Jee's [Data Science Project from Scratch](https://www.youtube.com/@KenJee_ds) series. 
- Alex The Analyst for [web scraping](https://youtu.be/8dTpNajxaH0?si=alUzpn-dE3lk3T28) and [data cleaning]
    (https://www.youtube.com/watch?v=bDhvCp3_lYw)
- Akamai Developer for [how to implement Spotify's API](https://youtu.be/WAmEZBEeNmg?si=J_uIipxrSFJi0QFS)
- [All Machine Learning algorithms explained](https://youtu.be/E0Hmnixke2g?si=49J7HuTpBgAEqolA)

## Project Structure

The project is organized into two festival sub-projects, each in its own folder:

```
ds_festivals_project/
├── edc_vegas/           # EDC Las Vegas lineup prediction (primary project)
│   ├── notebook/        # Jupyter notebooks (steps 1–7)
│   └── data/            # Raw and processed CSVs
└── tomorrowland/        # Tomorrowland historical EDA (secondary project)
    ├── notebook/        # Jupyter notebooks
    └── data/            # Raw and processed CSVs
```

---

## EDC Vegas — Full Project Walkthrough

### Step 1: Data Collection & Web Scraping (`1.collect_data.ipynb`)

Scraped artist names from two source types using **BeautifulSoup** and **Selenium** (headless Chrome for JavaScript-heavy pages):

**EDC Vegas Official Lineups (2022–2025):**
| Year | Artists Collected |
|------|-------------------|
| 2022 | 1,413 |
| 2023 | 1,110 |
| 2024 | 1,275 |
| 2025 | 1,287 |
| **Total** | **5,085 records** |

**Top EDM Talent Agency Rosters:**
| Agency                           | Artists                  |
|----------------------------------|--------------------------|
| UTA (United Talent Agency)       | 1,842                    |
| CAA (Creative Artists Agency)    | 227                      |
| Wasserman                        | 647                      |
| Corson Agency                    | 207                      |
| **Total**                        | **2,923 unique artists** |

All artist names were normalized to lowercase, stripped of whitespace, and had `&` replaced with `and` for consistent matching across sources.

---

### Step 2: Combining & Aggregating Data (`2.combining_data.ipynb`)

- Merged all per-year EDC lineup CSVs into a single dataset (deduplicated on year + artist) → **1,477 rows**
- Computed `total_appearances` (2022–2025) and `years_played` for each artist
- Top repeat performers: Armin Van Buuren, Kaskade, Deorro, Lady Faith, Bunny, Jessica Audiffred (all 4 appearances)
- Combined all agency rosters into `artists_agency.csv`

---

### Step 3: Deduplication & Cleaning (`3.clean_dups.ipynb`)

- Removed year column and deduplicated on artist name → **1,477 → 1,046 unique artists**
- Cleaned the artist statistics CSV:
  - Removed error columns
  - Converted human-readable suffixes to numeric (e.g., `"8.72M"` → `8,720,000`, `"468K"` → `468,000`)
  - Replaced NaN values with `0`

---

### Step 4: Master Dataset Creation (`4.merge_csv.ipynb`)

Merged three datasets into a single comprehensive table:
1. `edc_artist_stats_cleaned.csv` — Spotify/streaming popularity metrics
2. `artist_counts_2022_2025.csv` — Appearance history
3. `artists_agency.csv` — Agency affiliations

**Key decisions:**
- When an artist appeared in multiple agency rosters, kept the non-Insomniac entry (Insomniac is EDC's organizer — being on their roster doesn't mean external booking power)
- Result after final deduplication: **973 unique artists** with complete feature data

**Final dataset columns:** `artist`, `followers`, `streams`, `playlists`, `playlist_reach`, `charts`, `shazams`, `videos`, `views`, `dj_supports`, `total_appearances`, `years_played`, `agency`

---

### Step 5: Exploratory Data Analysis (`5.eda.ipynb`)

Visualized distributions using Matplotlib and Seaborn:
- **Agency distribution**: Pie chart of Insomniac vs. independent/other agency artists
- **Top 100 by streams**: Stacked bar chart (12×20 figure), axes formatted with B/M/K suffixes
- **Top 100 by followers**: Coral bar chart
- **Top 100 by appearances**: Seagreen bar chart

Key observations:
- Follower counts range from ~6 to 8.72M — extreme skew requiring log transformation
- Stream counts similarly right-skewed (a handful of mega-artists dominate)
- Most artists appear only 1–2 times; multi-year regulars are rare

---

### Step 6: Feature Engineering & Model Building (`6.build_model.ipynb`)

**Feature engineering:**

| Feature | Description |
|---------|-------------|
| `played_2022`–`played_2025` | Binary flags per year |
| `played_prev_year` | Did they play the year before the target? |
| `played_2_years_ago`, `played_3_years_ago` | Historical booking pattern |
| `total_past_appearances` | Total times played before target year |
| `consecutive_years` | How many years in a row they've played (burnout proxy) |
| `log_followers` | Log-scaled follower count (handles 6 → 8.72M range) |
| `streams` | Raw stream count |
| `is_insomniac` | Binary flag for Insomniac agency roster |

**Model:**
- **Algorithm**: Random Forest Classifier (`scikit-learn`)
- **Parameters**: `n_estimators=100`, `max_depth=6`, `class_weight='balanced'`, `random_state=42`
- `class_weight='balanced'` was critical — most artists (973) don't play EDC, so the naive model would just predict "no" for everyone
- Training was structured historically: features derived from 2022–2024 data, target = `played_2025`

**Feature importance rankings (from the trained model):**

| Rank | Feature | Importance |
|------|---------|------------|
| 1 | `total_past_appearances` | 37.4% |
| 2 | `log_followers` | 15.7% |
| 3 | `streams` | 13.3% |
| 4 | `played_3_years_ago` | 13.2% |
| 5 | `played_2_years_ago` | 7.5% |
| 6 | `consecutive_years` | 5.0% |
| 7 | `played_prev_year` | 4.9% |
| 8 | `is_insomniac` | 3.0% |

**Post-prediction adjustments applied to raw probabilities:**
- **Insomniac roster**: +45% boost
- **Large artist** (`log_followers` > 75th percentile) with `consecutive_years = 1`: +25% (likely start of Year 2 in a 2-year booking cycle)
- **Large artist** with `consecutive_years ≥ 2`: −25% (likely taking a break after multi-year run)
- **Vegas residency**: −30% (residency conflicts with festival appearance)
- All scores capped at 1.0

**Output**: Top 285 artists by adjusted probability score → `2026_edc_predictions.csv`

---

### Step 7: Evaluation Against Actual 2026 Lineup (`7.compare_w_actual_lineup26.ipynb`)

The actual 2026 EDC Las Vegas lineup was scraped after its release and compared against predictions. Standard accuracy was intentionally ignored — guessing "no one plays" yields ~97% accuracy and tells us nothing useful (the **True Negative Illusion**).

**Results:**

| Metric | Value |
|--------|-------|
| Actual lineup size | 264 artists |
| Predicted lineup size | 288 artists |
| True Positives (correct) | **41** |
| False Negatives (missed) | 223 |
| False Positives (wrong predictions) | 247 |
| **Recall** | **15.53%** |
| **Precision** | **14.24%** |
| **F1 Score** | **14.86%** |

**41 correctly predicted artists included:** Above & Beyond, Armin Van Buuren, Tiësto, Seven Lions, Fisher, FISHER, Meduza, Boys Noize, Paul Van Dyk, Joseph Capriati, Indira Paganotto, Lady Faith, Liquid Stranger, Lilly Palmer, and 27 others.

The model captured major headliners and multi-year regulars well, but struggled with debut bookings and artists whose social metrics don't reflect EDC-specific booking patterns.


## For Future Predictions (EDC 2027 & Beyond)

### 1. Fix Feature Engineering — Let the Model Learn the Rules

The biggest opportunity: remove the manual post-processing adjustments and bake them into training features instead.

- **Insomniac agency** currently gets a hardcoded +45% boost. Adding `is_insomniac` as a training feature (it's already there but ranked last at 3%) with more training data would let the model learn the actual weight rather than guessing.
- **Vegas residency** is currently a manual −30% penalty. Adding a `has_residency` boolean feature lets the algorithm determine the real impact.
- **Genre & Stage**: Scrape artist genre data and map it to EDC's stage curators (NeonGARDEN → Techno/House, BassPOD → Dubstep). An artist's genre alignment with a stage is a strong booking signal.
- **Popularity Velocity**: Static follower/stream counts miss momentum. Adding 6-month follower growth % would surface fast-rising artists who get booked before their metrics look "big."
- **Tour Conflicts**: If an artist has a confirmed booking in Europe during EDC weekend, their probability should be near 0. Scraping conflicting tour dates would dramatically cut False Positives.

### 2. Expand Training Data with More Time Slices

Currently the model trains on one block (2022–2024 → predict 2025). Creating staggered iterations multiplies the training data:
- Row block 1: 2022–2023 features → predict 2024
- Row block 2: 2022–2024 features → predict 2025

This captures seasonal booking shifts and gives the model more examples of what "getting booked" actually looks like across different years.

### 3. Upgrade the Algorithm & Tuning

- **Gradient Boosting**: Move from Random Forest to **XGBoost**, **LightGBM**, or **CatBoost** — tree ensemble models built for tabular data that typically yield a 5–10% F1 improvement out of the box.
- **Hyperparameter Search**: Use `GridSearchCV` or `RandomizedSearchCV` over tree depth, estimator count, and learning rate rather than relying on defaults.
- **Precision-Recall Curve Threshold**: Instead of capping at top 285 artists arbitrarily, plot the PR curve on a validation set and pick the threshold that mathematically maximizes F1.

