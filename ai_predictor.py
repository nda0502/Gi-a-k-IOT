import joblib

_model = joblib.load("env_model_10m.pkl")

def predict_next_env(temp_now, humidity, uv):
    pred = _model.predict([[float(temp_now), float(humidity), float(uv)]])[0]
    return float(pred[0]), float(pred[1]), float(pred[2])
