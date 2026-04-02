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
    
    return model, scaler, feature_columns

def get_crop_recommendation(nitrogen, phosphorus, potassium, temperature, humidity, ph, rainfall):
    """Get crop recommendation based on soil and weather parameters"""
    
    model, scaler, features = load_model()
    
    if model is None:
        # Fallback logic if model not trained
        return get_fallback_recommendation(nitrogen, phosphorus, potassium, temperature, humidity, ph, rainfall)
    
    # Prepare input features
    input_data = np.array([[nitrogen, phosphorus, potassium, temperature, humidity, ph, rainfall]])
    
    # Scale features
    input_scaled = scaler.transform(input_data)
    
    # Get prediction and probability
    prediction = model.predict(input_scaled)[0]
    probabilities = model.predict_proba(input_scaled)[0]
    confidence = max(probabilities)
    
    return {
        'crop': prediction,
        'confidence': float(confidence),
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
    """Fallback rule-based recommendation system"""
    
    # Simple rule-based recommendations
    if temp > 25 and humidity > 70 and rainfall > 200:
        crop = "Rice"
        confidence = 0.85
    elif temp > 20 and temp < 30 and humidity > 60 and rainfall > 100:
        crop = "Maize"
        confidence = 0.80
    elif temp > 18 and temp < 28 and humidity < 70 and rainfall < 100:
        crop = "Wheat"
        confidence = 0.75
    elif n > 80 and p > 60 and k > 70:
        crop = "Sugarcane"
        confidence = 0.70
    elif temp > 25 and humidity > 50 and ph < 7.0:
        crop = "Cotton"
        confidence = 0.72
    elif temp < 25 and humidity > 60 and rainfall > 150:
        crop = "Tea"
        confidence = 0.78
    else:
        crop = "Vegetables (Mixed)"
        confidence = 0.65
    
    return {
        'crop': crop,
        'confidence': confidence,
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