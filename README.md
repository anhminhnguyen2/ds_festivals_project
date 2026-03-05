# ds_festivals_project

The purpose of this project is to help music lovers to predict the line up of their next festivals. The data will be collected from previous year's line up and the popularity of the artists to accurately predict the current/next year line up.

Tutorials videos from [YouTube](https://www.youtube.com):
- Ken Jee's [Data Science Project from Scratch](https://www.youtube.com/@KenJee_ds) series. 
- Alex The Analyst for [web scraping](https://youtu.be/8dTpNajxaH0?si=alUzpn-dE3lk3T28) and [data cleaning]
    (https://www.youtube.com/watch?v=bDhvCp3_lYw)
- Akamai Developer for [how to implement Spotify's API](https://youtu.be/WAmEZBEeNmg?si=J_uIipxrSFJi0QFS)
- [All Machine Learning algorithms explained](https://youtu.be/E0Hmnixke2g?si=49J7HuTpBgAEqolA)

# GOAL: 
Identify the most popular genre and group of artist for the past year and predict the line-up in the future base on genre and artist popularity

# PLAN
The Plan: Building a "Propensity to Play" Model
Since you only have 4 years of history (2022–2025) to predict the 5th year (2026), we cannot use complex time-series forecasting. Instead, we will build a Binary Classification Model.

We will restructure your data so the model asks: "Given an artist's history up to Year X, what is the probability they play in Year X+1?"

1. Data Structuring (The most important part)
We need to turn your single row per artist into multiple "training examples."

Input: History up to 2024 -> Target: Did they play in 2025? (This helps the model "learn" the pattern).
Input: History up to 2025 -> Target: Predict for 2026 (This is our final goal).
2. Feature Engineering (Teaching the model your logic)
We will create specific columns to represent the rules you described:

Cadence Patterns:
Years_Since_Last_Played: If it's been 1 year, maybe they skip. If 2, maybe they return.
Played_Last_Year: (Boolean) Strong negative signal for some.
Played_2_Years_Ago: (Boolean) Strong positive signal for "Big" artists.
Artist Tier:
Total_Followers / Streams: To distinguish "Big" vs "Small" artists automatically so the model knows which cadence applies.
Residency Conflict:
Residency_Count_2026: From your 2026_vegas_recidency.csv. If this is high, probability drops.
3. The Recommended Model: Gradient Boosting (XGBoost or LightGBM)
Why?
Handles "Interaction" well: It can learn rules like "IF artist is BIG AND played 2 years ago, THEN high probability" vs "IF artist is SMALL AND played last year, THEN low probability." Linear regression struggles with these specific "IF/THEN" combos.
Works with small data: Unlike Deep Learning, it works well with tabluar data of this size (hundreds/thousands of artists).
Feature Importance: It will tell you exactly which factor drove the decision (e.g., "Agency" vs "Residency").
Step-by-Step Implementation Plan
I will now update the notebook to follow this logic.

Load Data: Import your stats and residency files.
Transform Data: Convert the years_played column (currently strings like "2022, 2024") into a year-by-year grid (2022, 2023, 2024, 2025).
Create Features: Calculate the "lag" features (e.g., played_t_minus_1, played_t_minus_2).
Train Model: Train on predicting 2025 (using 2022-2024 data).
Predict 2026: Feed 2022-2025 data to predict 2026.
* From CoPilot

1. raw_probability (The Statistical Prediction)
This is calculated by the Random Forest Classifier model trained in cell 6. It looks at historical patterns to generate a probability between 0 and 1.

The model uses these 8 input features (factors) to determine the score:

played_prev_year: Did they play in 2025? (Strongest predictor usually: if they played last year, they are often less likely to play again due to rotation).
played_2_years_ago: Did they play in 2024?
played_3_years_ago: Did they play in 2023?
total_past_appearances: How many times have they played in total recently? (Frequent flyers are more likely to return).
consecutive_years: Have they played 2 or 3 years in a row? (High consecutively often lowers probability due to "burnout").
is_insomniac: Are they managed by Insomniac Records? (Insomniac tends to book their own artists).
log_followers: How famous are they? (Logarithm of follower count).
streams: Streaming popularity.
2. final_probability (The Adjusted Prediction)
This takes the raw_probability and applies "Business Logic" rules defined in the adjust_score function in cell 7:

Insomniac Boost: If is_insomniac is true, the score is multiplied by 1.3 (+30%).
Reasoning: The festival organizer favors their own talent.
Residency Penalty: If the artist has a Vegas Residency (found in 2026_vegas_recidency.csv), the score is multiplied by 0.7 (-30%).
Reasoning: Exclusive residency contracts often prevent artists from playing nearby festivals.

Area to improve: 
- How many residencies one artist have? if more than 1 or 2 then penalty => reduce possibility by 40%
- 