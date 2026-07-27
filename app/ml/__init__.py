import joblib
import numpy as np
import os
from pathlib import Path

# Get the directory of this file
model_dir = Path(__file__).parent

# Load model and scaler
model_path = model_dir / 'crop_model.pkl'
scaler_path = model_dir / 'crop_scaler.pkl'
features_path = model_dir / 'feature_columns.pkl'

# Global variables
model = None
scaler = None
feature_columns = None

def load_model():
    """Load the trained model and scaler"""
    global model, scaler, feature_columns
    
    if model is None and model_path.exists():
        model = joblib.load(model_path)
        scaler = joblib.load(scaler_path)
        feature_columns = joblib.load(features_path)
        if hasattr(model, 'n_jobs'):
            model.n_jobs = 1
    
    return model, scaler, feature_columns

def get_crop_recommendation(nitrogen, phosphorus, potassium, temperature, humidity, ph, rainfall):
    """Return up to three crops, ordered by Random Forest probability."""
    
    model, scaler, features = load_model()
    
    if model is None:
        # Fallback logic if model not trained
        return get_fallback_recommendation(nitrogen, phosphorus, potassium, temperature, humidity, ph, rainfall)
    
    # Prepare input features
    input_data = np.array([[nitrogen, phosphorus, potassium, temperature, humidity, ph, rainfall]])
    
    # Scale features
    input_scaled = scaler.transform(input_data)
    
    probabilities = model.predict_proba(input_scaled)[0]
    top_indices = np.argsort(probabilities)[-3:][::-1]
    recommendations = [
        {
            'crop': str(model.classes_[index]),
            'probability': round(float(probabilities[index]) * 100, 2)
        }
        for index in top_indices
    ]
    
    return {
        'recommendations': recommendations,
        'parameters': {
            'nitrogen': nitrogen,
            'phosphorus': phosphorus,
            'potassium': potassium,
            'temperature': temperature,
            'humidity': humidity,
            'ph': ph,
            'rainfall': rainfall
        }
    }

def get_fallback_recommendation(n, p, k, temp, humidity, ph, rainfall):
    """Return fallback crops when the trained model is unavailable."""
    
    # Simple rule-based recommendations
    if temp > 25 and humidity > 70 and rainfall > 200:
        crop = "Rice"
    elif temp > 20 and temp < 30 and humidity > 60 and rainfall > 100:
        crop = "Maize"
    elif temp > 18 and temp < 28 and humidity < 70 and rainfall < 100:
        crop = "Wheat"
    elif n > 80 and p > 60 and k > 70:
        crop = "Sugarcane"
    elif temp > 25 and humidity > 50 and ph < 7.0:
        crop = "Cotton"
    elif temp < 25 and humidity > 60 and rainfall > 150:
        crop = "Tea"
    else:
        crop = "Vegetables (Mixed)"
    fallback_crops = [crop] + [
        candidate for candidate in ('Rice', 'Maize', 'Wheat', 'Cotton', 'Sugarcane', 'Tea')
        if candidate != crop
    ][:2]
    fallback_probabilities = (85.0, 10.0, 5.0)
    
    return {
        'recommendations': [
            {'crop': candidate, 'probability': probability}
            for candidate, probability in zip(fallback_crops, fallback_probabilities)
        ],
        'parameters': {
            'nitrogen': n,
            'phosphorus': p,
            'potassium': k,
            'temperature': temp,
            'humidity': humidity,
            'ph': ph,
            'rainfall': rainfall
        }
    }

# Try to load model on import
load_model()
