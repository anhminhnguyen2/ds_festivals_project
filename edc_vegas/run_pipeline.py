"""One-button pipeline runner for the EDC Vegas lineup prediction.

Runs the headless part of the pipeline end to end:

    notebook 2  combine lineup CSVs        -> artist counts
    notebook 3  clean latest raw snapshot  -> cleaned stats
    notebook 4  merge everything           -> master dataset
    notebook 6  train + predict            -> edc_{year}_prediction.csv
    notebook 7  evaluate vs actual lineup  (skipped gracefully if unavailable)

NOT included (interactive, run separately when needed):
    notebook 1        lineup / agency scraping
    artist_metrics.py monthly Songstats metrics sweep

Usage:
    python run_pipeline.py                # predict the next festival edition
    python run_pipeline.py --year 2027    # predict a specific year
    python run_pipeline.py --skip-data    # reuse existing master, just retrain
    python run_pipeline.py --skip-eval    # don't run the evaluation notebook
"""
import argparse
import glob
import os
import re
import subprocess
import sys
import time
from datetime import datetime

import nbformat
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
NB_DIR = os.path.join(SCRIPT_DIR, 'notebook')
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')


def norm_name(s):
    s = str(s).lower().strip().replace('&', 'and')
    return re.sub(r'\s+', ' ', s)


def default_year():
    """EDC Vegas happens in May; after May you're working on next year's edition."""
    today = datetime.now()
    return today.year + 1 if today.month > 5 else today.year


def banner(text):
    print(f"\n{'=' * 62}\n  {text}\n{'=' * 62}")


def set_current_year(nb_name, year):
    """Rewrite `current_year = XXXX` in the notebook's parameter cell."""
    path = os.path.join(NB_DIR, nb_name)
    nb = nbformat.read(path, as_version=4)
    for cell in nb.cells:
        if cell.cell_type == 'code' and 'current_year' in cell.source:
            new_src = re.sub(r'current_year\s*=\s*\d{4}', f'current_year = {year}',
                             cell.source, count=1)
            if new_src != cell.source:
                cell.source = new_src
                nbformat.write(nb, path)
            return
    raise RuntimeError(f"Could not find 'current_year = ...' in {nb_name}")


def run_notebook(nb_name):
    path = os.path.join(NB_DIR, nb_name)
    t0 = time.time()
    result = subprocess.run(
        [sys.executable, '-m', 'jupyter', 'nbconvert', '--to', 'notebook',
         '--execute', '--inplace', '--ExecutePreprocessor.timeout=1200', path],
        capture_output=True, text=True)
    elapsed = time.time() - t0
    if result.returncode != 0:
        print(f"  FAILED after {elapsed:.0f}s. nbconvert output (tail):")
        print('\n'.join(result.stderr.splitlines()[-25:]))
        return False
    print(f"  OK ({elapsed:.0f}s)")
    return True


def preflight(year, skip_data):
    problems = []

    residency = os.path.join(DATA_DIR, 'extract', f'{year}_vegas_recidency.csv')
    if not os.path.exists(residency):
        problems.append(
            f"Missing {os.path.relpath(residency, SCRIPT_DIR)} - notebook 6 needs the "
            f"Vegas residency list for {year} (columns: artist,recidency_club).")

    if not skip_data:
        if not glob.glob(os.path.join(DATA_DIR, 'extract', '*_edc_lineup.csv')):
            problems.append("No *_edc_lineup.csv files in data/extract/ - run notebook 1 first.")
        has_raw_stats = (glob.glob(os.path.join(DATA_DIR, 'metrics_snapshots', 'artist_stats_*.csv'))
                         or [f for f in glob.glob(os.path.join(DATA_DIR, 'main', 'edc_artist_stats_*.csv'))
                             if '_cleaned' not in f])
        if not has_raw_stats:
            problems.append("No raw metrics snapshot found - run artist_metrics.py first.")

    if not os.path.exists(os.path.join(DATA_DIR, 'extract', f'{year - 1}_producer_rank.csv')):
        print(f"  Note: no {year - 1}_producer_rank.csv - the producer_rank_score "
              f"feature will be 0 (this is allowed).")

    return problems


def print_summary(year, eval_ran):
    pred_path = os.path.join(DATA_DIR, 'result_prediction', f'edc_{year}_prediction.csv')
    df = pd.read_csv(pred_path)
    picked = df[df['result'] == 1]
    banner(f"EDC {year} PREDICTION SUMMARY")
    print(f"Scored {len(df)} artists, predicted lineup: {len(picked)}")
    print(f"Full ranking: {os.path.relpath(pred_path, SCRIPT_DIR)}\n")
    print("Top 15 by probability:")
    top = df.sort_values('probability', ascending=False).head(15)
    for _, row in top.iterrows():
        print(f"  {row['probability']:.3f}  {row['artist']}")

    if not eval_ran:
        return
    compare_dir = os.path.join(SCRIPT_DIR, f'compare_to_{year}')
    act_path = os.path.join(compare_dir, f'{year}_edc_lineup.csv')
    prd_path = os.path.join(compare_dir, f'{year}_edc_prediction.csv')
    if not (os.path.exists(act_path) and os.path.exists(prd_path)):
        print(f"\nNo evaluation files for {year} yet (lineup not announced?).")
        return
    actual = set(pd.read_csv(act_path)['artist'].dropna().map(norm_name))
    pred = set(pd.read_csv(prd_path)['artist'].dropna().map(norm_name))
    tp = len(actual & pred)
    precision, recall = tp / len(pred), tp / len(actual)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
    print(f"\nEvaluation vs actual {year} lineup ({len(actual)} artists):")
    print(f"  Correct: {tp}   Precision: {precision:.1%}   Recall: {recall:.1%}   F1: {f1:.1%}")


def main():
    parser = argparse.ArgumentParser(description="Run the EDC prediction pipeline end to end.")
    parser.add_argument('--year', type=int, default=default_year(),
                        help="festival year to predict (default: next edition)")
    parser.add_argument('--skip-data', action='store_true',
                        help="skip notebooks 2-4 and reuse the existing master dataset")
    parser.add_argument('--skip-eval', action='store_true',
                        help="skip the evaluation notebook (7)")
    args = parser.parse_args()

    banner(f"EDC VEGAS PIPELINE - predicting {args.year}")
    problems = preflight(args.year, args.skip_data)
    if problems:
        print("\nCannot run:")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)

    if not args.skip_data:
        for name, label in [('2.combining_data.ipynb', 'Combine lineup data'),
                            ('3.clean_dups.ipynb', 'Clean latest metrics snapshot'),
                            ('4.merge_csv.ipynb', 'Rebuild master dataset')]:
            banner(f"STEP: {label} ({name})")
            if not run_notebook(name):
                sys.exit(1)
    else:
        print("\n--skip-data: reusing existing master dataset.")

    banner(f"STEP: Train model & predict {args.year} (6.build_model.ipynb)")
    set_current_year('6.build_model.ipynb', args.year)
    if not run_notebook('6.build_model.ipynb'):
        sys.exit(1)

    eval_ran = False
    if not args.skip_eval:
        banner(f"STEP: Evaluate vs actual {args.year} lineup (notebook 7)")
        set_current_year('7.compare_w_actual_lineup_for_curr_year.ipynb', args.year)
        eval_ran = run_notebook('7.compare_w_actual_lineup_for_curr_year.ipynb')
        if not eval_ran:
            print(f"  Evaluation failed - most likely the {args.year} lineup isn't "
                  f"announced yet. The prediction itself is unaffected.")

    print_summary(args.year, eval_ran)


if __name__ == '__main__':
    main()
