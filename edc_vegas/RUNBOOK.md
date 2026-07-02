# EDC Vegas Prediction — Runbook

Step-by-step guide for running the pipeline each year, plus the recurring
popularity-snapshot process that feeds future growth features.

There are two loops:

| Loop | Cadence | Purpose |
|------|---------|---------|
| [Annual prediction cycle](#annual-prediction-cycle) | Once a year | Rebuild the dataset, train, predict, evaluate |
| [Metrics snapshot sweep](#metrics-snapshot-sweep-monthly) | Monthly | Collect popularity metrics over time → growth features |

---

## File naming conventions

The notebooks find their inputs by year-based file names. For a target year `{Y}`:

| File | Created by | Used by |
|------|-----------|---------|
| `data/extract/{Y}_edc_lineup.csv` | notebook 1 (scrape) | notebook 2 |
| `data/extract/{Y}_vegas_recidency.csv` | manual/scraped residency list | notebook 6 (required) |
| `data/extract/{Y-1}_producer_rank.csv` | producer top-100 scrape | notebook 6 (optional — feature is 0 if missing) |
| `data/main/COMPLETE_edc_artist_and_stats.csv` | notebook 4 | notebooks 5, 6 |
| `data/result_prediction/edc_{Y}_prediction.csv` | notebook 6 | notebook 7 |
| `compare_to_{Y}/` (lineup, prediction, results CSVs) | notebook 7 | final evaluation |
| `data/metrics_snapshots/artist_stats_{YYYY-MM-DD}.csv` | `artist_metrics.py` (one per monthly sweep) | notebook 3 auto-detects the latest |

Artist names are normalized everywhere with the same rule: **lowercase, trimmed,
`&` → `and`, collapsed whitespace**. If you add a new data source, apply the same
normalization or names won't join.

---

## Annual prediction cycle

Example below uses predicting **EDC 2027**. Do this after the previous festival
(May) and before the lineup announcement (usually late winter).

### 1. Scrape the newest completed lineup — `notebook/1.collect_data.ipynb`

Scrape the 2026 lineup (the year that just happened) so it becomes training
history. Also re-scrape agency rosters if you want fresher `is_insomniac` /
`has_agency` flags.

> ⚠️ Scrape the lineup page **after the festival**, when it shows the complete
> final lineup (~370–440 unique artists). Early-announcement scrapes are
> partial (~260) and will understate an artist's history.

### 2. Combine lineups — `notebook/2.combining_data.ipynb`

Merges all per-year lineup CSVs → `artist_counts_2022_2026.csv` with
`total_appearances` and `years_played` per artist.

### 3. Refresh popularity stats — `artist_metrics.py` + `notebook/3.clean_dups.ipynb`

Run a full metrics sweep (see [snapshot section](#metrics-snapshot-sweep-monthly)
for how the script behaves), then run notebook 3 — it auto-detects the newest
raw snapshot, converts suffixes (`8.72M` → `8720000`), and fills NaN with 0.

### 4. Rebuild the master dataset — `notebook/4.merge_csv.ipynb`

Merges stats + appearance counts + agency rosters →
`data/main/COMPLETE_edc_artist_and_stats.csv`. This is the model's entire
candidate pool: **an artist not in this file can never be predicted**, so the
more sources feed it, the higher the recall ceiling (in 2026, 57% of the actual
lineup was missing from the pool — see README "Expand the Candidate Pool").

### 5. Prepare target-year context files

- `data/extract/2027_vegas_recidency.csv` — artists with Vegas club residencies
  (columns: `artist,recidency_club`). Required by notebook 6.
- `data/extract/2026_producer_rank.csv` — producer top-100 (columns:
  `rank,artist`). Optional; skip it and the feature is all zeros.

### 6. Train & predict — `notebook/6.build_model.ipynb`

1. Set `current_year = 2027` in the first cell.
2. Run all cells. Everything else adapts automatically:
   - `HISTORY_YEARS` becomes 2022–2026
   - training slices become 2024, 2025, **and 2026** (one new slice per year — this is
     why step 1 matters)
   - features are rebuilt per slice from what was known *before* each target year
3. Output: `data/result_prediction/edc_2027_prediction.csv`, top
   `TARGET_LINEUP_SIZE = 430` artists flagged with `result = 1`.

Model settings (Random Forest, 300 trees, depth 6, balanced class weights) were
chosen by a seed-robustness backtest against the actual 2026 lineup — don't
re-tune casually; single-run F1 differences under ~1 point are noise.

### 7. Evaluate after the lineup drops — `notebook/7.compare_w_actual_lineup_for_curr_year.ipynb`

1. Set `current_year = 2027` in the first cell.
2. Run all cells. It scrapes the official lineup page (if the scrape fails it
   keeps the existing CSV), normalizes and dedupes names on both sides, and
   prints Recall / Precision / F1.
3. Re-run it again after the festival when the page shows the complete lineup —
   the numbers against the full lineup are the honest ones.

**2026 benchmark to beat: Precision 30.47%, Recall 29.91%, F1 30.18%**
(131 of 438 artists correctly predicted).

---

## Metrics snapshot sweep (monthly)

Goal: build a time series of popularity metrics per artist so the model can use
**growth** (momentum), not just static counts. Static counts miss fast-rising
artists who get booked before their numbers look big.

### How `artist_metrics.py` works

- Scrapes **every artist in the database**: the union of the master dataset
  (`COMPLETE_edc_artist_and_stats.csv`) and the deduplicated lineup list
  (`edc_artists_no_duplicates.csv`), names normalized (~1,050 artists).
- Opens a **visible** Chromium window (Playwright) and scrapes each artist's
  Songstats page: Followers, Streams, Playlists, Playlist Reach, Charts,
  Shazams, Videos, Views, DJ Supports. No Spotify API needed.
- Output: `data/metrics_snapshots/artist_stats_YYYY-MM-DD.csv` — one file per
  monthly sweep, dated when the sweep started, so the file name tells you when
  you last collected.
- **Resume is automatic and month-aware:**
  - Re-running within the same month continues the unfinished sweep — artists
    already collected are skipped, artists that **errored are retried** (they
    no longer count as "done").
  - When the sweep is complete, the script says so and exits instead of
    silently collecting nothing.
  - In a new month a fresh snapshot file starts automatically. No manual
    archiving or renaming needed.

Setup (once): `pip install playwright pandas` then `playwright install chromium`.

### Sweep procedure

```
python artist_metrics.py              # scrape all remaining artists (default)
python artist_metrics.py --batch 50   # or cap this session at 50 artists
python artist_metrics.py --new        # force a fresh sweep (overwrites today's)
```

Run it (repeatedly, if using `--batch` or if a session crashes) until it prints
`Sweep complete for this month.` Each artist takes ~15–30s, so a full ~1,050
artist sweep is several hours of scraping — progress is saved every 10 artists,
so interrupting with Ctrl-C is always safe.

> ⚠️ **Finish a sweep within the month it starts.** The script keys sweeps to
> the calendar month: a sweep left unfinished when the month rolls over is
> abandoned, and the new month starts from scratch. Starting in the first week
> of each month leaves plenty of slack.

### Practical tips for the cadence

- **Consistency beats frequency.** A complete sweep every month is worth more
  than partial, irregular sweeps. Growth features are deltas — a missing
  artist in one snapshot means no delta for them.
- **Expand the candidate pool first.** History can't be collected
  retroactively, so add new candidate sources (other Insomniac festivals,
  refreshed agency rosters) *before* accumulating months of snapshots — new
  artists are picked up automatically once they appear in the source CSVs.
- **The decisive window is roughly August–January** — bookings are negotiated in
  the fall and the lineup drops in late winter. Snapshots in that window feed
  the features that matter; summer sweeps mostly add baseline.

### Using the snapshots (once ≥ 2 exist)

Add growth features in notebook 6's feature-preparation cell, e.g.:

```python
snap_now = pd.read_csv('../data/metrics_snapshots/artist_stats_2026-10-01.csv')
snap_old = pd.read_csv('../data/metrics_snapshots/artist_stats_2026-07-01.csv')
# after cleaning suffixes + normalizing names, per artist:
# followers_growth_3m = (followers_now - followers_old) / max(followers_old, 1)
# streams_growth_3m   = (streams_now - streams_old) / max(streams_old, 1)
```

Then add the growth columns to `build_slice()` alongside the other popularity
features. One caveat to check at that point: growth computed in 2026–2027 is a
*current* snapshot applied to *historical* training slices (2024/2025 targets),
so the model sees slightly leaky training values. It's the same approximation
already made for the static popularity features; once several years of
snapshots exist, training slices can use growth as it was *before each target
year*, which removes the approximation.
