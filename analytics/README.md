# Module 2 — Analytics Pipeline (`/analytics`)
**Marks: 50**

This module is Zepto's analyst-to-data-scientist workflow in one pass: profile a dataset, handle its imperfections defensibly, tell a clear visual story about it, and then build and rigorously evaluate a full predictive-modeling pipeline on top of the same data.

## Dataset

- **Source:** Classic Titanic dataset, loaded once via Seaborn's built-in loader: `sns.load_dataset('titanic')`.
- **Note:** This loader requires internet access the first time it runs (it fetches from Seaborn's online data repository and caches locally). Subsequent runs on the same machine reuse the cache.
- **One load only:** The raw dataset is loaded from network/cache **exactly once** for the entire module. Every later step — EDA, modeling, tuning, the regression side-task — builds on that same cleaned data. There is never an independent second `sns.load_dataset('titanic')` call.

## Structure

This is one cohesive pipeline, not two disconnected exercises. A natural layout inside `/analytics`:

```
/analytics
├── 01_eda.ipynb        # loads data, profiles it, cleans it, saves titanic.csv, full EDA story
├── 02_modeling.ipynb   # reads the committed titanic.csv, continues into the modeling pipeline
├── titanic.csv         # committed offline fallback (produced by 01_eda.ipynb)
└── README.md           # this file — written interpretations, comparison tables, recommendation
```

Scripts instead of notebooks, or a single notebook, are equally acceptable — what matters is the single load + continuation structure described above.

---

## Part A — Profiling, Cleaning, and the Data Story

1. **Profile the dataset**
   - Print `df.info()`, `df.describe()`, `df.shape`.
   - Compute and report the percentage of missing values in every column that has any.
   - Immediately after loading, save the DataFrame as a committed offline fallback: `df.to_csv("titanic.csv", index=False)` inside `/analytics`, so the submission can be graded via `pd.read_csv("titanic.csv")` even if `sns.load_dataset(...)` can't reach the internet at grading time.
   - This is the one and only load of the raw dataset — everything below, including the modeling pipeline, works from this same DataFrame or its saved CSV.

2. **Missing-value handling**
   - Threshold rule: **< 5% missing → drop those rows**; **5%–30% missing → impute**.
   - For any column whose missing rate is too high for reliable imputation, explicitly decide to either drop the column or encode "missing" as its own category — and justify the decision in writing.
   - State the exact measured percentage for each affected column before choosing its strategy.

3. **Univariate analysis (`age`, `fare`)**
   - Histogram and box plot for both columns.
   - IQR rule for outliers: points outside `[Q1 − 1.5×IQR, Q3 + 1.5×IQR]`. Report the outlier count for each column.
   - Compute mean, median, and mode for `fare`; state in writing whether its distribution is right-skewed, left-skewed, or symmetric, referencing the mean/median/mode ordering.

4. **Bivariate analysis**
   - Using boolean masking (`&`/`|` combinations), compute and report survival rate by:
     - (a) `sex`
     - (b) `pclass`
     - (c) `sex` and `pclass` together
   - Correlation matrix restricted to exactly these six columns: `survived, pclass, age, sibsp, parch, fare`.
     - Include `survived` (0/1-valued) as the natural numeric target.
     - **Exclude** `adult_male` and `alone` — they're derived/redundant flags, not independent measured features.
   - Render the 6×6 matrix as a heatmap (`sns.heatmap`).
   - Write a short interpretation of the two strongest correlations: rank all off-diagonal pairs by `abs(correlation)` and interpret the top two.

5. **Multivariate "data story"**
   - At least 4 distinct charts (any mix of bar/box/scatter/heatmap/pair-plot) that together build a coherent argument about who was more likely to survive and why.
   - Each chart needs a 2–4 sentence written interpretation — a chart with no interpretation does not count.

6. **Exploratory standardization check (not the modeling pipeline's preprocessing)**
   - Standardize `age` and `fare` using `z = (x − mean) / std` on the full cleaned DataFrame (manually or with `StandardScaler`).
   - Show a before/after comparison (printed means/stds, or overlaid distribution plots) confirming ≈ mean 0, std 1.
   - This is purely an EDA-stage sanity check — it does **not** feed into the modeling pipeline, which does its own train-only scaling.

---

## Part B — Predictive Modeling, Continuing from the Same Cleaned Data

7. **Stratified train/test split**
   - Split first, before any preprocessing. Target: `survived`.
   - Justify why stratification matters given the class balance observed in Task 1.

8. **Preprocessing (fit on training data only)**
   - Handle missing values in the columns used (strategy doesn't need to match Task 2 exactly — state the choice).
   - Encode categorical columns (`sex`, `embarked`) with label or one-hot encoding.
   - Scale numeric features with `StandardScaler`.
   - **Hard rule:** every preprocessing step (imputer, encoder, scaler) is fit only on the training split, then applied transform-only to the test split. Never fit/refit on test data or the full pre-split dataset — that leaks test-set information into training.
   - Recommended: implement with a scikit-learn `Pipeline`/`ColumnTransformer` so fit-on-train / transform-on-test is enforced structurally.

9. **Train three classifiers** on the identical split:
   - Logistic Regression
   - Decision Tree — additionally render with `plot_tree`, labeling feature names and class names
   - Random Forest

10. **Evaluate all three models** with: confusion matrix, accuracy, precision, recall, F1 score, and ROC curve with AUC. Present all metrics side by side in a single comparison table.

11. **Imbalance handling comparison**
    - Report survived/not-survived class balance.
    - Retrain (one of the three models is enough) three ways:
      - (a) baseline / no handling
      - (b) `class_weight='balanced'`
      - (c) SMOTE oversampling — applied **only to the training fold** (to avoid leakage)
    - Compare precision/recall/F1 across the three variants with a short written conclusion on which strategy worked best and why.

12. **Hyperparameter tuning**
    - `GridSearchCV` over the Random Forest's `n_estimators`, `max_depth`, `max_features`.
    - Report the best parameter combination and the out-of-bag (OOB) score.
    - **Important:** `oob_score_` is only populated when `oob_score=True` is passed at construction — construct as `RandomForestClassifier(oob_score=True, ...)` together with the chosen/tuned parameters, or the OOB score won't be available to report.

13. **Regression side-task**
    - Using the same dataset, predict `fare` from the other available features with multivariate linear regression.
    - Report MAE, RMSE, R², and Adjusted R².
    - Produce a residual plot; state in writing whether it shows heteroscedasticity (non-random spread of residuals).

14. **Model comparison table + recommendation**
    - Present the three classifiers' metrics (accuracy, precision, recall, F1, AUC) side by side.
    - Present the regression model's metrics (MAE, RMSE, R², Adjusted R²) side by side, as their **own separate columns** — classification and regression metrics are on different scales and must not be implied to be on one shared scale.
    - Add a 3–5 sentence final written recommendation of which classifier to deploy, referencing specific metric values.

15. **Save the best-performing complete pipeline**
    - Save the fitted preprocessing steps (imputer/encoder/scaler, or the `ColumnTransformer`) together with the final estimator as a single combined object (e.g. a scikit-learn `Pipeline`), via `joblib.dump(full_pipeline, ...)`.
    - Do **not** save the bare estimator alone — the saved artifact must work end-to-end on raw, unpreprocessed new data.
    - Include a short script/cell that reloads it with `joblib.load` and confirms it still predicts correctly on raw input.

---

## Acceptance Criteria

Submission is complete when:

- [ ] Missing-value percentages are reported for every affected column, and each applied strategy explicitly cites the percentage-based threshold rule.
- [ ] `titanic.csv` (via `df.to_csv("titanic.csv", index=False)`) is committed inside `/analytics` as the offline fallback, loadable via `pd.read_csv("titanic.csv")` — and the raw dataset is loaded from network/cache exactly once across the whole module.
- [ ] IQR-based outlier counts are reported for both `age` and `fare`; the `fare` skewness conclusion compares mean, median, and mode.
- [ ] All three bivariate breakdowns (sex, pclass, sex+pclass) report numeric survival rates; the correlation matrix/heatmap uses exactly the six specified columns (`adult_male` and `alone` excluded); the two strongest correlations are named and interpreted.
- [ ] At least 4 multivariate charts are present, each with its own written interpretation, plus the before/after standardization check for both `age` and `fare`.
- [ ] A stratified train/test split is implemented before any preprocessing, with justification referencing class balance.
- [ ] All preprocessing steps are fit only on the training split and applied transform-only to the test split.
- [ ] All three classifiers are trained on the identical split; the decision tree is visualized via `plot_tree` with labeled features/classes; the full metric suite is reported for each classifier.
- [ ] The three-way imbalance comparison (baseline vs. `class_weight='balanced'` vs. SMOTE) is present with a written conclusion; SMOTE is applied to the training fold only.
- [ ] `GridSearchCV` best parameters and OOB score are reported for a `RandomForestClassifier(oob_score=True, ...)`.
- [ ] The regression sub-task reports all four stated metrics and an explicit heteroscedasticity conclusion.
- [ ] The final model comparison table and written recommendation are present, with classifier and regression metrics as separate metric columns.
- [ ] The saved artifact is the complete fitted pipeline (preprocessing + estimator, via `joblib.dump(full_pipeline, ...)`), included or regenerable, demonstrably reloadable, and usable end-to-end on raw new data.

---

## Submission

This module lives at `/analytics` inside the single project repository:

- EDA and modeling code (e.g. `01_eda.ipynb` + `02_modeling.ipynb`, or an equivalent clearly ordered structure)
- The one committed `titanic.csv` offline-fallback file
- Any saved chart images as supporting artifacts
- The saved joblib pipeline file
- This module-level `README.md`, containing every required written interpretation, the model comparison table, and the final recommendation