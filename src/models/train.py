from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

df = pd.read_csv(f"{Path().resolve().parent.parent}/data/processed/MTD_complete_data.csv")

deleted_cols = ["id", "name", "date", "longitude", "latitude", "length"]

df["date"] = pd.to_datetime(df["date"])
df["hour"] = df["date"].dt.hour
df["day_of_week"] = df["date"].dt.dayofweek
df["month"] = df["date"].dt.month
y = df["traffic_intensity"]
X = df.drop(["traffic_intensity"] + deleted_cols, axis=1)

mask = y < 10000
X = X[mask]
y = y[mask]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = RandomForestRegressor(
    n_estimators=500, max_features=0.5, max_depth=10, min_samples_split=2, min_samples_leaf=1
)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)

print(f"MAE:  {mean_absolute_error(y_test, y_pred):.2f}")
print(f"RMSE: {np.sqrt(mean_squared_error(y_test, y_pred))}")
print(f"R²:   {r2_score(y_test, y_pred):.4f}")

joblib.dump(model, "modelo_trafico.pkl")
