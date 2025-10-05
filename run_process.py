import os
import sys
import json
import requests
import pandas as pd
import numpy as np
from datetime import date, timedelta, datetime
import joblib

# Suppress TensorFlow logging before import
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
from tensorflow.keras.models import load_model

# --- Constants ---
MODEL_MASTER_PATH = "Models/v2.5.keras"
MODEL_LABELER_PATH = "Models/v2.5_head.keras"
SCALER_FEATURE_PATH = "Scalers/v2.5_scaler.gz"
REFERENCE_CSV_PATH = "reference.csv"

OPTIMAL_THRESHOLDS = {
    'label_very_hot': 0.26, 'label_very_cold': 0.28,
    'label_very_uncomfortable': 0.29, 'label_very_wet': 0.17,
    'label_very_windy': 0.33
}

BASE_FEATURES_TO_REQUEST = [
    "weather_code", "temperature_2m_max", "temperature_2m_min", "apparent_temperature_max",
    "apparent_temperature_mean", "precipitation_sum", "snowfall_sum",
    "precipitation_hours", "wind_speed_10m_max", "wind_gusts_10m_max",
    "shortwave_radiation_sum", "et0_fao_evapotranspiration",
    "relative_humidity_2m_mean", "surface_pressure_mean", "cloud_cover_mean"
]

# --- Functions (unchanged from your version) ---
def make_weather_codes(df):
    code = df['weather_code']
    df['is_fog'] = np.where(code.between(40, 49), 1, 0)
    df['is_drizzle'] = np.where(code.between(50, 59), 1, 0)
    df['is_rain'] = np.where(code.between(60, 69) | code.between(80, 82), 1, 0)
    df['is_snow'] = np.where(code.between(70, 79) | code.between(85, 86), 1, 0)
    df['is_thunderstorm'] = np.where(code.between(90, 99), 1, 0)
    def get_intensity(c):
        last_digit = c % 10
        if last_digit in [0, 1, 2]: return 1
        if last_digit in [3, 4, 5, 6]: return 2
        if last_digit in [7, 8, 9]: return 3
        return 0
    precip_mask = (df['is_drizzle'] == 1) | (df['is_rain'] == 1) | (df['is_snow'] == 1)
    df['precipitation_intensity'] = 0
    if precip_mask.any():
        df.loc[precip_mask, 'precipitation_intensity'] = code[precip_mask].apply(get_intensity)
    return df

def make_trends(df, base_features):
    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values('time').reset_index(drop=True)
    for feature in base_features:
        if feature in df.columns:
            df[f'{feature}_rolling_mean_3'] = df[feature].rolling(window=3, min_periods=1).mean()
            df[f'{feature}_rolling_mean_7'] = df[feature].rolling(window=7, min_periods=1).mean()
            df[f'{feature}_rolling_std_7'] = df[feature].rolling(window=7, min_periods=1).std()
            df[f'{feature}_lag_1'] = df[feature].shift(1)
            df[f'{feature}_lag_7'] = df[feature].shift(7)
    df = df.bfill().ffill()
    return df

def process_dataframe_features(df, city_data, base_features):
    processed_df = make_weather_codes(df.copy())
    processed_df = make_trends(processed_df, base_features)
    processed_df["latitude"] = city_data["latitude"]
    processed_df["altitude"] = city_data["elevation"]
    lon_rad = np.radians(city_data["longitude"])
    processed_df["longitude_sin"] = np.sin(lon_rad)
    processed_df["longitude_cos"] = np.cos(lon_rad)
    processed_df['time'] = pd.to_datetime(processed_df['time'])
    processed_df['day_of_year'] = processed_df['time'].dt.dayofyear
    processed_df['day_sin'] = np.sin(2 * np.pi * processed_df['day_of_year'] / 365.25)
    processed_df['day_cos'] = np.cos(2 * np.pi * processed_df['day_of_year'] / 365.25)
    return processed_df

def calculate_amplified_percentage(probability, threshold):
    if probability < threshold:
        return (probability / threshold) * 50 if threshold > 0 else 50.0
    return 50 + ((probability - threshold) / (1 - threshold)) * 50 if threshold < 1.0 else 100.0

def format_results(probabilities, city_name, date_str):
    results = {"city": city_name, "date": date_str, "likelihoods": {}}
    labels = list(OPTIMAL_THRESHOLDS.keys())
    for i, label in enumerate(labels):
        prob = probabilities[i]
        thresh = OPTIMAL_THRESHOLDS[label]
        amp_pct = calculate_amplified_percentage(prob, thresh)
        clean_label = label.replace('label_', '').replace('_', ' ').title()
        results["likelihoods"][clean_label] = float(round(amp_pct, 1))
    return results

def get_historical_day(city_data, target_date_str, labeler_model, feature_scaler, training_feature_order, base_features):
    target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    start_date = target_date - timedelta(days=7)
    params = {"latitude": city_data["latitude"], "longitude": city_data["longitude"], "start_date": start_date.strftime("%Y-%m-%d"), "end_date": target_date.strftime("%Y-%m-%d"), "daily": BASE_FEATURES_TO_REQUEST, "timezone": "auto"}
    response = requests.get("https://archive-api.open-meteo.com/v1/archive", params=params)
    historical_df = pd.DataFrame(response.json()['daily'])
    if len(historical_df) < 8: return {"error": "Not enough historical data"}
    processed_df = process_dataframe_features(historical_df, city_data, base_features)
    single_day_ordered_df = processed_df[training_feature_order].iloc[-1:]
    scaled_features = feature_scaler.transform(single_day_ordered_df)
    probabilities = labeler_model.predict(scaled_features, verbose=0)[0]
    return format_results(probabilities, city_data['city'], date_str=target_date_str)

def get_todays_forecast(city_data, master_model, feature_scaler, training_feature_order, base_features):
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=24)
    params = {"latitude": city_data["latitude"], "longitude": city_data["longitude"], "start_date": start_date.strftime("%Y-%m-%d"), "end_date": end_date.strftime("%Y-%m-%d"), "daily": BASE_FEATURES_TO_REQUEST, "timezone": "auto"}
    response = requests.get("https://archive-api.open-meteo.com/v1/archive", params=params)
    historical_df = pd.DataFrame(response.json()['daily'])
    if len(historical_df) < 25: return {"error": "Not enough historical data for today's forecast"}
    processed_df = process_dataframe_features(historical_df, city_data, base_features)
    ordered_sequence_df = processed_df[training_feature_order]
    scaled_sequence = feature_scaler.transform(ordered_sequence_df)
    sequence_to_predict = np.expand_dims(scaled_sequence, axis=0)
    probabilities = master_model.predict(sequence_to_predict, verbose=0)[0]
    return format_results(probabilities, city_data['city'], date_str=date.today().strftime("%Y-%m-%d"))

def get_future_forecast(city_data, labeler_model, feature_scaler, training_feature_order, base_features, forecast_days):
    history_end_date = date.today() - timedelta(days=1)
    history_start_date = history_end_date - timedelta(days=7)
    params_hist = {"latitude": city_data["latitude"], "longitude": city_data["longitude"], "start_date": history_start_date.strftime("%Y-%m-%d"), "end_date": history_end_date.strftime("%Y-%m-%d"), "daily": BASE_FEATURES_TO_REQUEST, "timezone": "auto"}
    response_hist = requests.get("https://archive-api.open-meteo.com/v1/archive", params=params_hist)
    historical_df = pd.DataFrame(response_hist.json().get('daily', {}))
    params_future = {"latitude": city_data["latitude"], "longitude": city_data["longitude"], "forecast_days": forecast_days, "daily": BASE_FEATURES_TO_REQUEST, "timezone": "auto"}
    response_future = requests.get("https://api.open-meteo.com/v1/forecast", params=params_future)
    future_df = pd.DataFrame(response_future.json().get('daily', {}))
    if future_df.empty: return {"error": "Future forecast API returned no data"}
    combined_df = pd.concat([historical_df, future_df], ignore_index=True)
    processed_full_df = process_dataframe_features(combined_df, city_data, base_features)
    target_date = date.today() + timedelta(days=forecast_days - 1)
    target_date_str = target_date.strftime("%Y-%m-%d")
    mask = pd.to_datetime(combined_df['time']).dt.strftime("%Y-%m-%d") == target_date_str
    if not mask.any(): return {"error": f"No forecast data found for {target_date_str}"}
    single_day_ordered_df = processed_full_df.loc[mask, training_feature_order]
    if single_day_ordered_df.empty: return {"error": f"Processed dataframe missing features for {target_date_str}"}
    scaled_features = feature_scaler.transform(single_day_ordered_df)
    probabilities = labeler_model.predict(scaled_features, verbose=0)[0]
    return format_results(probabilities, city_data['city'], date_str=target_date_str)

# --- Load models once ---
try:
    master_model = load_model(MODEL_MASTER_PATH)
    labeler_model = load_model(MODEL_LABELER_PATH)
    feature_scaler = joblib.load(SCALER_FEATURE_PATH)
    reference_df = pd.read_csv(REFERENCE_CSV_PATH)
    label_cols = [col for col in reference_df.columns if 'label_' in col]
    TRAINING_FEATURE_ORDER = [col for col in reference_df.columns if col not in ['time', 'date', 'day_of_year'] + label_cols]
    BASE_FEATURES = [col for col in TRAINING_FEATURE_ORDER if not ('rolling' in col or 'lag' in col or 'is_' in col or col in ['latitude', 'altitude', 'longitude_sin', 'longitude_cos', 'day_sin', 'day_cos', 'precipitation_intensity'])]
except Exception as e:
    print(json.dumps({"error": f"Fatal: Could not load model files. Details: {e}"}))
    sys.exit(1)

# --- Persistent loop for stdin/stdout ---
for line in sys.stdin:
    try:
        req = json.loads(line.strip())
        city_data = {"city": req["city"], "latitude": float(req["lat"]), "longitude": float(req["lon"]), "elevation": float(req["alt"])}
        date_str = req["date"]
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        today = date.today()

        if target_date < today:
            result = get_historical_day(city_data, date_str, labeler_model, feature_scaler, TRAINING_FEATURE_ORDER, BASE_FEATURES)
        elif target_date == today:
            result = get_todays_forecast(city_data, master_model, feature_scaler, TRAINING_FEATURE_ORDER, BASE_FEATURES)
        else:
            forecast_days = (target_date - today).days + 1
            if not 1 <= forecast_days <= 16:
                result = {"error": "Date is too far in the future. Can only forecast up to 16 days."}
            else:
                result = get_future_forecast(city_data, labeler_model, feature_scaler, TRAINING_FEATURE_ORDER, BASE_FEATURES, forecast_days)

        print(json.dumps(result))
        sys.stdout.flush()
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.stdout.flush()
