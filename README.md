# ds_festivals_project

The purpose of this project is to help music lovers to predict the line up of their next festivals. The data will be collected from previous year's line up and the popularity of the artists to accurately predict the current/next year line up.

Tutorials videos from [YouTube](https://www.youtube.com):
- [Ken Jee](https://www.youtube.com/@KenJee_ds)'s Data Science Project from Scratch series. 
- [Alex The Analyst](https://youtu.be/8dTpNajxaH0?si=alUzpn-dE3lk3T28) for web scraping and data cleaning
    https://www.youtube.com/watch?v=bDhvCp3_lYw 


# GOAL: 
Identify the most popular genre and group of artist for the past year and predict the line-up in the future base on genre and artist popularity


# APPROACH: 
Using Spotify's API to determent the ranking of popularity for artist and genre for the recent years (2022-2025), combine with the data from past festival to determine the result.

# Initial Roadmap (from ChatGPT)

**1. Problem Definition & Success Criteria**

Goal

Identify the most popular music genres and artist groups in the past year.

Predict future festival line-ups based on genre trends and artist popularity.

Key Questions

Which genres dominated streaming popularity in the last year?

Which artists consistently rank high across years?

How do festival line-ups correlate with streaming popularity?

Which genres/artists are likely to appear in future line-ups?

Success Metrics

Accuracy of popularity rankings (Spotify metrics)

Strength of correlation between Spotify popularity and festival appearances

Reasonable, explainable predictions for future line-ups

**2. Data Collection**

2.1 Spotify API Data (2022–2025)

Data to Collect

Artist popularity score

Genre(s) per artist

Follower count

Track popularity

Release dates

Yearly snapshots (to track trends)

Endpoints

Artists

Tracks

Audio Features (optional for deeper analysis)

Search endpoint (to identify trending artists per year)

Output

Artist-level dataset

Genre-level dataset aggregated by year

2.2 Festival Line-Up Data

Sources

Public festival websites

Kaggle datasets

Web scraping (if allowed)

Wikipedia archives

Data to Collect

Festival name

Year

Artist name

Genre (mapped from Spotify)

Artist position (headliner vs supporting)

Output

Festival appearances per artist per year

**3. Data Cleaning & Preparation**

3.1 Cleaning

Remove duplicate artists

Normalize artist names across datasets

Handle missing genres or popularity scores

Convert popularity metrics to consistent scales

3.2 Feature Engineering

Genre popularity per year (mean or weighted popularity)

Artist trend score (change in popularity year-over-year)

Festival frequency score (number of appearances)

Combined popularity index:

combined_score = (spotify_popularity * weight1) + (festival_appearances * weight2)

**4. Exploratory Data Analysis (EDA)**

4.1 Genre Analysis

Top genres per year (2022–2025)

Growth/decline of genres over time

Genre diversity in festivals vs Spotify trends

4.2 Artist Analysis

Top artists by popularity

Artists with fastest growth

Artists repeatedly appearing in festivals

4.3 Visualizations

Line charts: genre popularity over time

Bar charts: top artists per year

Heatmaps: genre vs festival frequency

**5. Modeling & Prediction**

5.1 Popularity Forecasting

Approaches

Time-series models (rolling averages, ARIMA, Prophet)

Regression models (popularity as a function of time and festival presence)

5.2 Line-Up Prediction

Method

Rank artists by predicted popularity score

Group predictions by genre

Select top artists per genre as “likely line-up candidates”

Optional ML Models

Random Forest / XGBoost for popularity prediction

Clustering (K-Means) to group artists by popularity trajectory

**6. Validation & Evaluation**

Compare predicted line-ups to recent real festival line-ups

Measure overlap percentage

Analyze false positives (popular but not booked artists)

Explain why predictions make sense (interpretability)

**7. Results & Insights**

Deliverables

Most popular genres in the past year

Most influential artist groups

Predicted future festival line-ups

Key trends (emerging genres, declining genres)

**8. Tools & Tech Stack**

Language: Python

Libraries: Pandas, NumPy, Matplotlib, Seaborn, Scikit-learn

API: Spotify Web API

Data Storage: CSV / SQLite

Visualization: Jupyter Notebook / Tableau (optional)

**9. Limitations & Ethics**

Spotify popularity ≠ real-world fan attendance

Festival booking influenced by cost, exclusivity, and region

Genre labeling can be inconsistent

API data bias toward streaming audiences

**10. Future Improvements**

Add social media metrics (TikTok, YouTube)

Regional festival analysis

Ticket sales data

NLP analysis on music reviews or lyrics