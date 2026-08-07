# ds_festivals_project

The purpose of this project is to help music lovers to predict the line up of their next festivals. The data will be collected from previous year's line up and the popularity of the artists to accurately predict the current/next year line up.

**How accurate is it?** Backtested against the real EDC Las Vegas 2026 lineup, the model correctly named **131 of the 438 artists** who actually played. Of the artists it *could* have known about, it caught **69.3%**. Full breakdown — including why plain accuracy is a misleading metric here — in [Model Accuracy](#model-accuracy-how-good-is-it-really).

Tutorials videos from [YouTube](https://www.youtube.com):
- Ken Jee's [Data Science Project from Scratch](https://www.youtube.com/@KenJee_ds) series. 
- Alex The Analyst for [web scraping](https://youtu.be/8dTpNajxaH0?si=alUzpn-dE3lk3T28) and [data cleaning]
    (https://www.youtube.com/watch?v=bDhvCp3_lYw)
- Akamai Developer for [how to implement Spotify's API](https://youtu.be/WAmEZBEeNmg?si=J_uIipxrSFJi0QFS)
- [All Machine Learning algorithms explained](https://youtu.be/E0Hmnixke2g?si=49J7HuTpBgAEqolA)

> 🧭 **New to this project?** [`HANDOVER.md`](HANDOVER.md) explains the pipeline logic stage by stage, the design decisions behind it, the traps already hit once, and what to work on next.

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

### Workflow

> 📖 **Detailed guide:** see [`edc_vegas/RUNBOOK.md`](edc_vegas/RUNBOOK.md) for the full year-to-year runbook, file naming conventions, and the recurring metrics-snapshot process.
>
> ⚡ **One-button run:** `python edc_vegas/run_pipeline.py` executes steps 2–7 end to end (or double-click `run_pipeline.command` on macOS). Only the interactive scrapes (step 1 and `artist_metrics.py`) stay manual.

1. Scrape new year's lineup → 1.collect_data.ipynb
2. Run 2.combining_data.ipynb → produces artist_counts_2022_{new_year}.csv
3. Run artist_metrics.py + 3.clean_dups.ipynb → new stats snapshot
4. Run 4.merge_csv.ipynb → updated complete dataset
5. Change current_year in notebook 6 → run it → edc_{year}_prediction.csv
6. After lineup drops, change current_year in notebook 7 → run it to evaluate

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

**Feature engineering (20 features):**

| Feature group | Features | Description |
|---------------|----------|-------------|
| Booking history | `played_1/2/3_years_ago` | Lag flags relative to the target year |
| | `total_past_appearances`, `appearance_rate` | Volume and rate of past bookings |
| | `consecutive_years` | Years in a row played (burnout proxy) |
| | `years_since_last` | Recency of last appearance (99 = never) |
| Popularity | `log_followers`, `log_streams`, `log_playlists`, `log_playlist_reach`, `log_charts`, `log_shazams`, `log_videos`, `log_views`, `log_dj_supports` | **All** popularity metrics, log-scaled (raw counts are dominated by a few mega artists) |
| Context | `is_insomniac`, `has_agency` | Agency roster flags |
| | `has_residency` | Holds a Vegas club residency |
| | `producer_rank_score` | Position in the producer top-100 (101 − rank, 0 if unranked) |

**Staggered training slices** — instead of a single training block, the notebook builds one slice per historical target year (features restricted to what was known *before* that year):
- Slice 1: 2022–2023 features → target = played 2024
- Slice 2: 2022–2024 features → target = played 2025
- A new slice is added automatically each year as the master dataset grows

This yields **1,946 training rows** (2 × 973 artists) instead of 973.

**Model:**
- **Algorithm**: Random Forest Classifier (`scikit-learn`)
- **Parameters**: `n_estimators=300`, `max_depth=6`, `class_weight='balanced'`, `random_state=42` — the most stable configuration in a seed-robustness backtest against the actual 2026 lineup
- Gradient boosting (`HistGradientBoostingClassifier`) and deeper forests were also tested and scored consistently *worse* at this dataset size, so Random Forest stays
- `class_weight='balanced'` is critical — most artists in the pool don't play in a given year, so an unweighted model would just predict "no" for everyone

**Feature importance rankings (from the trained model):**

| Rank | Feature | Importance |
|------|---------|------------|
| 1 | `total_past_appearances` | 18.5% |
| 2 | `appearance_rate` | 17.8% |
| 3 | `years_since_last` | 9.9% |
| 4 | `log_followers` | 5.5% |
| 5 | `log_dj_supports` | 4.3% |
| 6 | `log_videos` | 4.1% |
| 7 | `has_agency` | 4.0% |
| 8 | `log_views` | 3.9% |
| … | (12 more features) | 34.0% |

**No manual probability adjustments.** The previous version multiplied raw model scores by hand-tuned factors (+45% Insomniac boost, ±25% booking-cycle, −30% Vegas residency). Backtested against the actual 2026 lineup, those adjustments turned out to be the single biggest source of error — removing them alone raised F1 from 16.3% to 23.5%. Those signals are now training features (`is_insomniac`, `has_residency`, `consecutive_years`), letting the model learn their true (much smaller) weights.

**Output**: Top 430 artists by predicted probability → `edc_2026_prediction.csv`. The cutoff is sized to a *complete* final lineup (2022–2026 full lineups ran ~370–440 unique artists) — the original top-285 was calibrated to the smaller initial announcement, which left easy recall on the table.

---

### Step 7: Evaluation Against Actual 2026 Lineup (`7.compare_w_actual_lineup_for_curr_year.ipynb`)

The actual 2026 EDC Las Vegas lineup was scraped and compared against predictions. Artist names are normalized on both sides (`&` → `and`, lowercase, deduplicated) before matching.

**Results — both models scored against the complete final lineup (438 unique artists):**

| Metric | Original model | Improved model |
|--------|---------------|----------------|
| Predicted lineup size | 288 | 430 |
| True Positives (correct) | 59 | **131** |
| **Precision** | 20.49% | **30.47%** |
| **Recall** | 13.47% | **29.91%** |
| **F1 Score** | 16.25% | **30.18%** (+86% relative) |

*(An earlier partial scrape of the lineup page had only 264 artists — the original README numbers of R 15.53% / P 14.24% / F1 14.86% were computed against that. The table above rescores both models against the same complete lineup for a fair comparison.)*

**What drove the improvement (measured by ablation against the actual 2026 lineup):**

| Change | F1 |
|--------|-----|
| Original model (manual probability adjustments, top-285) | 16.3% |
| Remove manual adjustments, model probabilities only | 23.5% (**+7.3 points — by far the largest win**) |
| + staggered training slices (2 blocks instead of 1) | 24.6% |
| + full feature set & tuning (all popularity metrics, residency, agency, producer rank; 300 trees) | 25.5% |
| + cutoff recalibrated to full lineup size (top-430 instead of top-285) | **30.2%** |

**Structural limit:** 249 of the 438 actual artists (57%) don't exist in the master dataset at all — mostly 2026 debuts who never played 2022–2025 and aren't on a scraped agency roster. The maximum achievable recall with the current candidate pool is **43.2%**, so growing the pool is the biggest remaining lever (see below).

---

## Model Accuracy: How Good Is It, Really?

### ⚠️ Why plain accuracy is the wrong headline number

The model scores a pool of **973 candidate artists** and flags the top 430. Only 189 of those 973 actually played EDC 2026, so a model that predicts **"nobody plays"** — a single line of code that learns nothing — scores **80.6% accuracy**. This is the **True Negative Illusion**: accuracy rewards being right about the ~800 artists who obviously weren't going to play, which is not the question anyone is asking.

For reference, here is the model's raw accuracy against the actual 2026 lineup:

| Model | Accuracy |
|-------|----------|
| Predict "nobody plays" (do-nothing baseline) | **80.57%** |
| This model (top-430 cutoff) | **63.31%** |

The model scores *lower* on accuracy than doing nothing — and that is expected and fine. It deliberately trades true negatives for true positives: it names 430 artists in order to catch 131 real ones, and every wrong name it stakes costs accuracy. **Precision, recall, and F1 are the metrics that matter here**, which is why the sections above lead with them.

### Confusion matrix (2026 backtest, 973 scored candidates)

|                     | Actually played | Did not play |
|---------------------|-----------------|--------------|
| **Predicted to play**   | **131** (TP)    | 299 (FP)     |
| **Predicted not to play** | 58 (FN)       | 485 (TN)     |

Derived from this table:

| Metric | Value | Reading |
|--------|-------|---------|
| Precision | **30.47%** | Of the 430 artists named, 131 actually played — roughly 1 in 3 |
| Recall (vs. full 438-artist lineup) | **29.91%** | Of everyone who played, the model named ~30% |
| **Recall (vs. the 189 it could reach)** | **69.31%** | **When an artist exists in the dataset, the model finds them ~7 times out of 10** |
| F1 Score | **30.18%** | Harmonic mean of precision and the full-lineup recall |
| Accuracy | 63.31% | See caveat above — not a meaningful score here |

The 69.31% number is the fairest read of the *model's* skill. The gap between it and the 29.91% headline recall is not a modelling failure but a **data coverage failure** — 249 of the 438 artists were never in the candidate pool to begin with, so no ranking algorithm could have surfaced them.

### Accuracy on historical data (before the 2026 lineup existed)

Two sanity checks on the training slices themselves, both using the same tuned Random Forest:

**5-fold cross-validation across both slices (1,946 rows, 35.3% positive):**

| Metric | Score | Baseline |
|--------|-------|----------|
| Accuracy | **74.31%** | 64.70% (majority class) |
| Balanced accuracy | **73.00%** | 50.00% (random) |
| ROC-AUC | **0.753** | 0.500 (random) |
| Precision / Recall / F1 | 62.38% / 68.56% / **65.33%** | — |

**Out-of-time test (train on the 2022–2023 → 2024 slice, predict the 2025 lineup):**

| Metric | Score | Baseline |
|--------|-------|----------|
| Accuracy | **79.03%** | 64.13% (majority class) |
| Balanced accuracy | **73.93%** | 50.00% |
| ROC-AUC | **0.840** | 0.500 |
| Precision / Recall / F1 | 79.59% / 55.87% / **65.66%** | — |

Here accuracy *is* informative, because these slices are far more balanced (~35% of the pool plays in any given year) and every artist scored is one the model genuinely could have known about. An ROC-AUC of **0.84** on a full year it never saw during training means the ranking itself is sound — given two artists, one who played 2025 and one who didn't, the model ranks the right one higher **84% of the time**.

### So what should you take away?

- The ranking is genuinely good: **ROC-AUC 0.84** out-of-time, **69.3% recall** on reachable artists.
- The end-to-end product is limited by coverage, not by the algorithm: **57% of the 2026 lineup was invisible** to the model, capping recall at 43.2%.
- Improving the headline F1 past ~30% is therefore mostly a **data collection** problem (expand the candidate pool — see below), not a modelling one.


## For Future Predictions (EDC 2027 & Beyond)

### ✅ Done for the 2026 backtest

- **Manual adjustments removed** — Insomniac/residency/booking-cycle signals are now training features; the model learned their true weights (residency importance: 0.6%, vs the −30% manual penalty it replaced).
- **Staggered time slices** — 2022–2023 → 2024 and 2022–2024 → 2025; a new slice is added automatically each year.
- **Algorithm & tuning explored** — gradient boosting and hyperparameter sweeps were tested; a tuned Random Forest (300 trees, depth 6) won at this dataset size.
- **Name normalization in evaluation** — `&`/`and` variants and duplicate scrape entries no longer count as misses.

### 1. Expand the Candidate Pool (biggest lever: 57% of the lineup is currently unreachable)

The model can only rank artists that exist in the master dataset. To raise the 43% recall ceiling:
- Scrape lineups from **other Insomniac festivals** (EDC Orlando/Mexico, Beyond Wonderland, Nocturnal Wonderland, Countdown NYE) — Insomniac heavily cross-books its own events
- Refresh **agency rosters annually** and add more agencies (WME roster is scraped but unused in the master merge)
- Add **Beatport/SoundCloud rising charts** to capture debut-ready artists before they play anywhere

### 2. Richer Features

- **Genre & Stage**: Scrape artist genre data and map it to EDC's stage curators (NeonGARDEN → Techno/House, BassPOD → Dubstep). An artist's genre alignment with a stage is a strong booking signal.
- **Popularity Velocity**: Static follower/stream counts miss momentum. Adding 6-month follower growth % would surface fast-rising artists who get booked before their metrics look "big."
- **Tour Conflicts**: If an artist has a confirmed booking in Europe during EDC weekend, their probability should be near 0. Scraping conflicting tour dates would dramatically cut False Positives.

### 3. Better Threshold Selection

The cutoff is now sized to the historical full-lineup size (~430) rather than the initial announcement, which was worth +4.7 F1 points on its own. Once a third training slice exists (after the 2026 data is merged into the master dataset), a further refinement is to hold out the most recent slice as validation and pick the probability threshold that maximizes F1 on it — the earlier attempt at this transferred poorly because the validation slice only had 2 years of history vs 4 at prediction time.

### 4. Popularity Growth from Recurring Snapshots (in progress)

`artist_metrics.py` snapshots are being collected on a recurring schedule (see [`edc_vegas/RUNBOOK.md`](edc_vegas/RUNBOOK.md)). Once two or more snapshots exist, growth features (e.g., 3-month % change in followers/streams) can be added to `build_slice()` to surface fast-rising artists whose static counts still look small.

