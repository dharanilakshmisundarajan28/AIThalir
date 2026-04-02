#!/usr/bin/env python3
"""
Direct model training script for Crop Recommendation System
Run this file to train the ML model
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
import joblib
import os
import sys
import warnings
warnings.filterwarnings('ignore')

def create_synthetic_data():
    """Create synthetic training data if real dataset not available"""
    print("📊 Creating synthetic training data...")
    np.random.seed(42)
    
    # Define crops and their optimal parameters
    crops_data = {
        'rice': {'N': (80, 140), 'P': (40, 80), 'K': (50, 100), 'temp': (20, 35), 'humid': (70, 90), 'ph': (5.5, 7.0), 'rain': (150, 300)},
        'maize': {'N': (60, 120), 'P': (30, 70), 'K': (40, 80), 'temp': (15, 30), 'humid': (50, 75), 'ph': (6.0, 7.5), 'rain': (50, 150)},
        'chickpea': {'N': (40, 80), 'P': (20, 60), 'K': (30, 70), 'temp': (18, 28), 'humid': (45, 65), 'ph': (6.5, 8.0), 'rain': (40, 80)},
        'kidneybeans': {'N': (50, 90), 'P': (30, 70), 'K': (40, 80), 'temp': (18, 26), 'humid': (55, 75), 'ph': (6.0, 7.5), 'rain': (60, 120)},
        'pigeonpeas': {'N': (40, 80), 'P': (20, 60), 'K': (30, 70), 'temp': (20, 30), 'humid': (50, 70), 'ph': (6.5, 7.5), 'rain': (50, 100)},
        'mothbeans': {'N': (30, 70), 'P': (15, 50), 'K': (25, 65), 'temp': (22, 32), 'humid': (40, 60), 'ph': (6.0, 7.5), 'rain': (30, 70)},
        'mungbean': {'N': (40, 80), 'P': (20, 60), 'K': (30, 70), 'temp': (20, 30), 'humid': (50, 70), 'ph': (6.0, 7.5), 'rain': (50, 100)},
        'blackgram': {'N': (40, 80), 'P': (20, 60), 'K': (30, 70), 'temp': (22, 32), 'humid': (55, 75), 'ph': (6.0, 7.5), 'rain': (60, 110)},
        'lentil': {'N': (35, 75), 'P': (15, 55), 'K': (25, 65), 'temp': (15, 25), 'humid': (45, 65), 'ph': (6.0, 7.5), 'rain': (40, 90)},
        'pomegranate': {'N': (40, 80), 'P': (20, 60), 'K': (30, 70), 'temp': (20, 30), 'humid': (50, 70), 'ph': (5.5, 7.0), 'rain': (60, 120)},
        'banana': {'N': (60, 120), 'P': (40, 80), 'K': (50, 100), 'temp': (20, 30), 'humid': (65, 85), 'ph': (5.5, 7.0), 'rain': (100, 200)},
        'mango': {'N': (40, 80), 'P': (20, 60), 'K': (30, 70), 'temp': (22, 32), 'humid': (55, 75), 'ph': (5.5, 7.5), 'rain': (80, 160)},
        'grapes': {'N': (30, 70), 'P': (15, 55), 'K': (25, 65), 'temp': (18, 28), 'humid': (50, 70), 'ph': (6.0, 7.5), 'rain': (50, 100)},
        'watermelon': {'N': (40, 80), 'P': (20, 60), 'K': (30, 70), 'temp': (22, 32), 'humid': (60, 80), 'ph': (6.0, 7.5), 'rain': (40, 80)},
        'muskmelon': {'N': (40, 80), 'P': (20, 60), 'K': (30, 70), 'temp': (22, 32), 'humid': (60, 80), 'ph': (6.0, 7.5), 'rain': (40, 80)},
        'apple': {'N': (20, 60), 'P': (10, 40), 'K': (20, 60), 'temp': (10, 22), 'humid': (60, 80), 'ph': (6.0, 7.0), 'rain': (70, 140)},
        'orange': {'N': (30, 70), 'P': (15, 55), 'K': (25, 65), 'temp': (15, 25), 'humid': (55, 75), 'ph': (5.5, 7.0), 'rain': (80, 160)},
        'papaya': {'N': (50, 100), 'P': (30, 70), 'K': (40, 80), 'temp': (22, 32), 'humid': (65, 85), 'ph': (6.0, 7.0), 'rain': (100, 200)},
        'coconut': {'N': (40, 80), 'P': (20, 60), 'K': (50, 100), 'temp': (22, 32), 'humid': (70, 90), 'ph': (5.5, 7.5), 'rain': (150, 300)},
        'cotton': {'N': (50, 100), 'P': (30, 70), 'K': (40, 80), 'temp': (22, 35), 'humid': (50, 70), 'ph': (6.0, 7.5), 'rain': (60, 120)},
        'jute': {'N': (60, 120), 'P': (40, 80), 'K': (50, 100), 'temp': (22, 32), 'humid': (70, 90), 'ph': (5.5, 7.0), 'rain': (150, 300)},
        'coffee': {'N': (40, 80), 'P': (20, 60), 'K': (30, 70), 'temp': (18, 26), 'humid': (70, 90), 'ph': (5.5, 6.5), 'rain': (150, 250)}
    }
    
    data = []
    for crop, params in crops_data.items():
        # Generate 100 samples per crop
        for _ in range(100):
            N = np.random.uniform(params['N'][0], params['N'][1])
            P = np.random.uniform(params['P'][0], params['P'][1])
            K = np.random.uniform(params['K'][0], params['K'][1])
            temp = np.random.uniform(params['temp'][0], params['temp'][1])
            humid = np.random.uniform(params['humid'][0], params['humid'][1])
            ph = np.random.uniform(params['ph'][0], params['ph'][1])
            rain = np.random.uniform(params['rain'][0], params['rain'][1])
            
            # Add some noise
            N += np.random.normal(0, 5)
            P += np.random.normal(0, 5)
            K += np.random.normal(0, 5)
            temp += np.random.normal(0, 2)
            humid += np.random.normal(0, 5)
            ph += np.random.normal(0, 0.3)
            rain += np.random.normal(0, 10)
            
            data.append([N, P, K, temp, humid, ph, rain, crop])
    
    df = pd.DataFrame(data, columns=['N', 'P', 'K', 'temperature', 'humidity', 'ph', 'rainfall', 'label'])
    print(f"✅ Created synthetic dataset with {len(df)} samples")
    return df

def load_or_create_dataset():
    """Try to load real dataset, create synthetic if not available"""
    try:
        # Try to download from Kaggle
        import kagglehub
        print("📥 Attempting to download dataset from Kaggle...")
        path = kagglehub.dataset_download("atharvaingle/crop-recommendation-dataset")
        dataset_path = os.path.join(path, 'Crop_recommendation.csv')
        
        if os.path.exists(dataset_path):
            df = pd.read_csv(dataset_path)
            print(f"✅ Loaded real dataset with {len(df)} samples")
            return df
        else:
            raise FileNotFoundError("Dataset not found")
    except Exception as e:
        print(f"⚠️ Could not download real dataset: {e}")
        print("🔄 Creating synthetic dataset instead...")
        return create_synthetic_data()

def train_model():
    """Main training function"""
    print("\n" + "="*60)
    print("🌾 CROP RECOMMENDATION MODEL TRAINING")
    print("="*60 + "\n")
    
    # Load dataset
    df = load_or_create_dataset()
    
    print(f"\n📊 Dataset Info:")
    print(f"   - Total samples: {len(df)}")
    print(f"   - Features: {', '.join(df.columns[:-1])}")
    print(f"   - Target crops: {df['label'].nunique()} different crops")
    print(f"   - Crops: {', '.join(df['label'].unique())}")
    
    # Prepare features and labels
    feature_columns = ['N', 'P', 'K', 'temperature', 'humidity', 'ph', 'rainfall']
    X = df[feature_columns]
    y = df['label']
    
    # Scale features
    print("\n📈 Scaling features...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Split data
    print("✂️ Splitting data into train/test sets...")
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"   - Training samples: {len(X_train)}")
    print(f"   - Test samples: {len(X_test)}")
    
    # Train Random Forest Classifier
    print("\n🤖 Training Random Forest Classifier...")
    rf_model = RandomForestClassifier(
        n_estimators=150,
        max_depth=20,
        min_samples_split=4,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
        verbose=1
    )
    
    rf_model.fit(X_train, y_train)
    
    # Evaluate model
    print("\n📊 Model Evaluation:")
    y_pred = rf_model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"   ✅ Accuracy: {accuracy * 100:.2f}%")
    
    print("\n📋 Classification Report:")
    print(classification_report(y_test, y_pred))
    
    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': feature_columns,
        'importance': rf_model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print("\n🔍 Feature Importance:")
    for _, row in feature_importance.iterrows():
        print(f"   - {row['feature']}: {row['importance']*100:.2f}%")
    
    # Save model and artifacts
    model_dir = os.path.join(os.path.dirname(__file__), 'app', 'ml')
    os.makedirs(model_dir, exist_ok=True)
    
    print("\n💾 Saving model artifacts...")
    joblib.dump(rf_model, os.path.join(model_dir, 'crop_model.pkl'))
    joblib.dump(scaler, os.path.join(model_dir, 'crop_scaler.pkl'))
    joblib.dump(feature_columns, os.path.join(model_dir, 'feature_columns.pkl'))
    
    print(f"   ✅ Model saved to: {model_dir}/crop_model.pkl")
    print(f"   ✅ Scaler saved to: {model_dir}/crop_scaler.pkl")
    print(f"   ✅ Features saved to: {model_dir}/feature_columns.pkl")
    
    # Test with sample input
    print("\n🧪 Testing model with sample inputs:")
    test_samples = [
        {'N': 90, 'P': 60, 'K': 70, 'temperature': 28, 'humidity': 75, 'ph': 6.5, 'rainfall': 200},
        {'N': 50, 'P': 30, 'K': 40, 'temperature': 22, 'humidity': 55, 'ph': 7.0, 'rainfall': 80},
        {'N': 40, 'P': 25, 'K': 35, 'temperature': 25, 'humidity': 65, 'ph': 6.8, 'rainfall': 60}
    ]
    
    for i, sample in enumerate(test_samples, 1):
        input_data = np.array([[sample['N'], sample['P'], sample['K'], 
                               sample['temperature'], sample['humidity'], 
                               sample['ph'], sample['rainfall']]])
        input_scaled = scaler.transform(input_data)
        prediction = rf_model.predict(input_scaled)[0]
        proba = rf_model.predict_proba(input_scaled)[0]
        confidence = max(proba)
        
        print(f"\n   Sample {i}:")
        print(f"      Parameters: N={sample['N']}, P={sample['P']}, K={sample['K']}, "
              f"Temp={sample['temperature']}°C, Humidity={sample['humidity']}%, "
              f"pH={sample['ph']}, Rainfall={sample['rainfall']}mm")
        print(f"      🌾 Recommended Crop: {prediction}")
        print(f"      📊 Confidence: {confidence*100:.1f}%")
    
    print("\n" + "="*60)
    print("✅ MODEL TRAINING COMPLETED SUCCESSFULLY!")
    print("="*60 + "\n")
    
    return rf_model, scaler, feature_columns

if __name__ == '__main__':
    try:
        train_model()
    except Exception as e:
        print(f"\n❌ Error during training: {e}")
        sys.exit(1)