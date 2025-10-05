import os
import sys
import json
import requests
import pandas as pd
import numpy as np
from datetime import date, timedelta, datetime
import joblib
from tensorflow.keras.models import load_model

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

MODEL_MASTER_PATH = "Models/v2.5.keras"
MODEL_FORECASTER_PATH = "Models/v2.5_tail.keras"
MODEL_LABELER_PATH = "models/v2.5_head.keras"
SCALER_FEATURE_PATH = "Scalers/v2.5_scaler.gz"
SCALER_TARGET_PATH = "Scalers/v2.5_head_target_scaler.gz"
REFERENCE_CSV_PATH = "reference.csv"

OPTIMAL_THRESHOLDS = {
    'label_very_hot': 0.26,
    'label_very_cold': 0.28,
    'label_very_uncomfortable': 0.29,
    'label_very_wet': 0.17,
    'label_very_windy': 0.33
}

BASE_FEATURES_TO_REQUEST = [
    "weather_code", "temperature_2m_max", "temperature_2m_min", "apparent_temperature_max",
    "apparent_temperature_mean", "precipitation_sum", "snowfall_sum",
    "precipitation_hours", "wind_speed_10m_max", "wind_gusts_10m_max",
    "shortwave_radiation_sum", "et0_fao_evapotranspiration",
    "relative_humidity_2m_mean", "surface_pressure_mean", "cloud_cover_mean"
]

# --- Functions ---
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

def calculate_amplified_percentage(probability, threshold):
    if probability < threshold:
        return (probability / threshold) * 50 if threshold > 0 else 50.0
    else:
        return 50 + ((probability - threshold) / (1 - threshold)) * 50 if threshold < 1.0 else 100.0

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

def fetch_and_label_past_years(city_data, target_date_str, labeler_model, feature_scaler, training_feature_order, base_features, years=25):
    base_url = "https://archive-api.open-meteo.com/v1/archive"
    today = date.today()
    current_year = today.year
    target_date_obj = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    month, day = target_date_obj.month, target_date_obj.day

    results = []

    for year in range(current_year, current_year - years, -1):
        try:
            target_date = date(year, month, day)
        except ValueError:
            continue

        start_date = target_date - timedelta(days=7)
        end_date = target_date
        params = {
            "latitude": city_data["latitude"],
            "longitude": city_data["longitude"],
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "daily": ",".join(BASE_FEATURES_TO_REQUEST),
            "timezone": "auto"
        }

        r = requests.get(base_url, params=params)
        if r.status_code != 200:
            continue
        data = r.json()
        if "daily" not in data:
            continue

        df = pd.DataFrame(data["daily"])
        if df.empty or len(df) < 8:
            continue

        processed_df = process_dataframe_features(df, city_data, base_features)
        single_day_ordered_df = processed_df[training_feature_order].iloc[-1:]
        scaled_features = feature_scaler.transform(single_day_ordered_df)
        probabilities = labeler_model.predict(scaled_features, verbose=0)[0]

        result_row = {
            "year": year,
            "date": target_date.strftime("%Y-%m-%d"),
            "city": city_data["city"],
            "likelihoods": {}
        }
        for i, label in enumerate(OPTIMAL_THRESHOLDS.keys()):
            amp_pct = calculate_amplified_percentage(probabilities[i], OPTIMAL_THRESHOLDS[label])
            clean_label = label.replace('label_', '').replace('_', ' ').title()
            result_row["likelihoods"][clean_label] = float(round(amp_pct, 1))
        results.append(result_row)

    return results

# --- Load models once ---
try:
    master_model = load_model(MODEL_MASTER_PATH)
    labeler_model = load_model(MODEL_LABELER_PATH)
    feature_scaler = joblib.load(SCALER_FEATURE_PATH)
    reference_df = pd.read_csv(REFERENCE_CSV_PATH)
    label_cols = [col for col in reference_df.columns if 'label_' in col]
    TRAINING_FEATURE_ORDER = [col for col in reference_df.columns if col not in ['time', 'date', 'day_of_year'] + label_cols]
    BASE_FEATURES = [col for col in TRAINING_FEATURE_ORDER if not (
        'rolling' in col or 'lag' in col or 'is_' in col or col in [
            'latitude', 'altitude', 'longitude_sin', 'longitude_cos',
            'day_sin', 'day_cos', 'precipitation_intensity'
        ])]
except Exception as e:
    print(json.dumps({"error": f"Fatal: Could not load model files. Details: {e}"}))
    sys.exit(1)

# --- Persistent loop for stdin/stdout ---
for line in sys.stdin:
    try:
        req = json.loads(line.strip())
        city_data = {
            "city": req["city"],
            "latitude": float(req["lat"]),
            "longitude": float(req["lon"]),
            "elevation": float(req["alt"])
        }
        date_str = req["date"]

        results = fetch_and_label_past_years(
            city_data,
            target_date_str=date_str,
            labeler_model=labeler_model,
            feature_scaler=feature_scaler,
            training_feature_order=TRAINING_FEATURE_ORDER,
            base_features=BASE_FEATURES,
            years=int(req.get("years", 25))
        )

        print(json.dumps({"results": results}))
        sys.stdout.flush()
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.stdout.flush()
