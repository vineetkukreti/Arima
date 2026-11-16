import pandas as pd
import numpy as np
from xgboost import XGBRegressor
from sklearn.model_selection import LeaveOneOut
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import LabelEncoder

# Load data - skip the blank first row, actual header is row 2
df = pd.read_csv("Data-14.csv", skiprows=1)
df.columns = df.columns.str.strip()
df = df.dropna(how="all", axis=1).dropna(how="all", axis=0)
df["Year"] = df["Year"].astype(int)
df["Product"] = df["Product"].astype(int)
df["Quantity"] = df["Quantity"].astype(int)
print("=== Raw Data ===")
print(df.to_string(index=False))
print(f"\nShape: {df.shape}")
print(f"\nDtypes:\n{df.dtypes}")
print(f"\nQuantity stats:\n{df['Quantity'].describe()}")

# Encode categorical features
le_country = LabelEncoder()
le_container = LabelEncoder()
df["Country_enc"] = le_country.fit_transform(df["Country"])
df["Container_enc"] = le_container.fit_transform(df["Container"])

# Features and target
features = ["Year", "Country_enc", "Product", "Container_enc"]
X = df[features]
y = df["Quantity"]

print("\n=== Feature Matrix ===")
print(X.to_string(index=False))

# --- Train/Test Split: use last 2 years as test ---
train_mask = df["Year"] <= 2022
test_mask = df["Year"] > 2022

X_train, X_test = X[train_mask], X[test_mask]
y_train, y_test = y[train_mask], y[test_mask]

print(f"\nTrain size: {len(X_train)}, Test size: {len(X_test)}")

# Train XGBoost
model = XGBRegressor(
    n_estimators=100,
    max_depth=3,
    learning_rate=0.1,
    random_state=42,
    objective="reg:squarederror",
)
model.fit(X_train, y_train)

# Predictions
y_pred_train = model.predict(X_train)
y_pred_test = model.predict(X_test)

print("\n=== Train Set Results ===")
for i, (actual, pred) in enumerate(zip(y_train, y_pred_train)):
    print(f"  Year {df.loc[y_train.index[i], 'Year']}: Actual={actual:,.0f}, Predicted={pred:,.0f}")
print(f"  MAE:  {mean_absolute_error(y_train, y_pred_train):,.2f}")
print(f"  RMSE: {np.sqrt(mean_squared_error(y_train, y_pred_train)):,.2f}")
print(f"  R²:   {r2_score(y_train, y_pred_train):.4f}")

print("\n=== Test Set Results (2023-2026) ===")
for i, (actual, pred) in enumerate(zip(y_test, y_pred_test)):
    print(f"  Year {df.loc[y_test.index[i], 'Year']}: Actual={actual:,.0f}, Predicted={pred:,.0f}")
print(f"  MAE:  {mean_absolute_error(y_test, y_pred_test):,.2f}")
print(f"  RMSE: {np.sqrt(mean_squared_error(y_test, y_pred_test)):,.2f}")
r2 = r2_score(y_test, y_pred_test)
print(f"  R²:   {r2:.4f}")

# --- Leave-One-Out Cross Validation (small dataset) ---
print("\n=== Leave-One-Out Cross Validation (Full Dataset) ===")
loo = LeaveOneOut()
loo_preds = np.zeros(len(X))
for train_idx, test_idx in loo.split(X):
    m = XGBRegressor(n_estimators=100, max_depth=3, learning_rate=0.1, random_state=42, objective="reg:squarederror")
    m.fit(X.iloc[train_idx], y.iloc[train_idx])
    loo_preds[test_idx] = m.predict(X.iloc[test_idx])

print(f"  LOO MAE:  {mean_absolute_error(y, loo_preds):,.2f}")
print(f"  LOO RMSE: {np.sqrt(mean_squared_error(y, loo_preds)):,.2f}")
print(f"  LOO R²:   {r2_score(y, loo_preds):.4f}")

# Feature importance
print("\n=== Feature Importance ===")
for name, imp in sorted(zip(features, model.feature_importances_), key=lambda x: -x[1]):
    print(f"  {name}: {imp:.4f}")
