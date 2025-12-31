import pandas as pd
import joblib
from sklearn.multioutput import MultiOutputRegressor
from sklearn.ensemble import RandomForestRegressor

CSV = "weather_log.csv"
MODEL_OUT = "env_model.pkl"

df = pd.read_csv(CSV)

X = df[["temp_now", "humidity", "uv"]].astype(float)
y = df[["temp_now", "humidity", "uv"]].shift(-1)
y.columns = ["temp_next", "hum_next", "uv_next"]

data = pd.concat([X, y], axis=1).dropna()
X = data[["temp_now", "humidity", "uv"]].values
y = data[["temp_next", "hum_next", "uv_next"]].values

base = RandomForestRegressor(n_estimators=400, random_state=42, n_jobs=-1)
model = MultiOutputRegressor(base)
model.fit(X, y)

joblib.dump(model, MODEL_OUT)
print("✅ Saved:", MODEL_OUT)
