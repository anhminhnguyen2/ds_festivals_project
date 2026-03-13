# ds_festivals_project

The purpose of this project is to help music lovers to predict the line up of their next festivals. The data will be collected from previous year's line up and the popularity of the artists to accurately predict the current/next year line up.

Tutorials videos from [YouTube](https://www.youtube.com):
- Ken Jee's [Data Science Project from Scratch](https://www.youtube.com/@KenJee_ds) series. 
- Alex The Analyst for [web scraping](https://youtu.be/8dTpNajxaH0?si=alUzpn-dE3lk3T28) and [data cleaning]
    (https://www.youtube.com/watch?v=bDhvCp3_lYw)
- Akamai Developer for [how to implement Spotify's API](https://youtu.be/WAmEZBEeNmg?si=J_uIipxrSFJi0QFS)
- [All Machine Learning algorithms explained](https://youtu.be/E0Hmnixke2g?si=49J7HuTpBgAEqolA)

## Project Process & Methodology

Here is a breakdown of the end-to-end data science lifecycle completed for the EDC Vegas prediction:

1. **Data Collection & Web Scraping**: Scraped historical EDC Vegas lineups (2022-2025) and related festival/agency data using BeautifulSoup to capture artist histories.
2. **API Integration**: Used the Spotify API to pull artist metadata (follower counts, total streams) to measure baseline popularity.
3. **Data Cleaning & Merging**: Resolved text duplicates, standardized artist names, and merged datasets into a singular comprehensive dataset (`COMPLETE_edc_artist_and_stats.csv`).
4. **Feature Engineering**: 
   - Transformed artist datasets into long/panel format.
   - Created binary flags for years played previously (`played_2022`, `played_2023`, etc.).
   - Added custom features: Insomniac agency management boolean, rolling consecutive years played, total past appearances.
   - Handled massive ranges in numeric data using Log Scaling (`log_followers`).
5. **Model Building**: 
   - Built a Random Forest Classifier using `scikit-learn`.
   - Structured training data to look into the past (e.g., predicting 2025 based upon 2022-2024 knowledge).
   - Addressed the massive class imbalance (most DJs don't play EDC) by using `class_weight='balanced'`.
   - Applied dynamic filtering to output a realistically capped list of artists (e.g., ~285 artists).
6. **Model Evaluation**: 
   - Scraped the newly released *actual* 2026 EDC lineup.
   - Mapped actual results side-by-side with predicted results.
   - Evaluated true model performance using **Recall**, **Precision**, and **F1-Score**. Standard accuracy was discarded to avoid the "True Negative Illusion" (where guessing no one plays yields high accuracy).

## For Future Predictions (EDC 2027 & Beyond)

To improve F1 scores and predictive capability for future year predictions:

### 1. Enhance Feature Engineering & Let the Model Learn
- **Stop Manual Post-Processing**: Instead of manually adjusting probabilities for rules like "Vegas Residency (-30%)" or "Insomniac Agency (+45%)" at the end, add `has_residency` and `agency` directly into the training features. Let the algorithm detect the exact penalty/boost mathematically.
- **Genre & Stage Matching**: Collect artist genres and group them by EDC's stage curators (NeonGARDEN = Techno/House, BassPOD = Dubstep).
- **Tour Overlaps (Geographic Availability)**: If an artist has a confirmed booking in Europe during EDC weekend, their probability is near 0. Scraping conflicting tour dates will dramatically reduce False Positives.
- **Popularity Velocity**: Base static numbers like `streams` are good, but factoring in *momentum* (e.g., 6-month follower growth percentage) helps capture viral artists who are likely to get booked over stagnant ones. Can use artists' metrics from this prediction to calculate the follower, stream, and popularity growth in the next prediction.

### 2. Expand Training Data Structure
- **Create More Time Slices**: Currently, the model is trained on a single block (predicting 2025). Extract more records by creating multiple staggered iterations (e.g., row 1: predict 2024 from 22-23; row 2: predict 2025 from 22-24). This drastically increases the volume of training data and captures seasonal booking shifts better.

### 3. Move to Advanced Algorithms & Tuning
- **Gradient Boosting**: Transition from Random Forest to powerful tree-based models engineered for tabular data like **XGBoost**, **LightGBM**, or **CatBoost**. They typically yield an immediate 5-10% bump in F1 score.
- **Hyperparameter Grid Search**: Use `GridSearchCV` or `RandomizedSearchCV` to dynamically test dozens of parameter combinations (like tree depths and estimator counts) rather than using out-of-the-box defaults.
- **Precision-Recall (PR) Curve Optimization**: Instead of picking an arbitrary probability threshold (like `> 0.5` or capping at top 285), plot a PR curve on validation sets to mathematically find the specific threshold that maximizes the F1 Score.

