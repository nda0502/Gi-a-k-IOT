import pandas as pd
import joblib
from sklearn.multioutput import MultiOutputRegressor
from sklearn.ensemble import RandomForestRegressor

CSV = "weather_log.csv"
MODEL_OUT = "env_model_10m.pkl"
K = 10  # 10 phút vì 1 bước = 1 phút (timer 60s)

df = pd.read_csv(CSV)

X = df[["temp_now", "humidity", "uv"]].astype(float)
y = df[["temp_now", "humidity", "uv"]].shift(-K)
y.columns = ["temp_next", "hum_next", "uv_next"]

data = pd.concat([X, y], axis=1).dropna()
X = data[["temp_now", "humidity", "uv"]].values
y = data[["temp_next", "hum_next", "uv_next"]].values

base = RandomForestRegressor(n_estimators=400, random_state=42, n_jobs=-1)
model = MultiOutputRegressor(base)
model.fit(X, y)

joblib.dump(model, MODEL_OUT)
print("✅ Saved:", MODEL_OUT, "| samples:", len(X))
