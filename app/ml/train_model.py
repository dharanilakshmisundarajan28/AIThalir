import pandas as pd 
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, accuracy_score
import joblib
import os
import kagglehub


def download_dataset():
    """Download crop recommendation dataset from Kaggle"""
    try:
        path = kagglehub.dataset_download("atharvaingle/crop-recommendation-dataset")
        return os.path.join(path, 'Crop_recommendation.csv')
    except Exception as e:
        print(f"Kaggle download failed: {e}")
        return None


def get_top_3_recommendations(model, scaler, feature_columns, input_data):
    """
    Return top 3 most probable crops using predict_proba()
    """

    input_df = pd.DataFrame([input_data], columns=feature_columns)

    input_scaled = scaler.transform(input_df)

    probabilities = model.predict_proba(input_scaled)[0]

    top_3_indices = np.argsort(probabilities)[-3:][::-1]

    recommendations = []

    for index in top_3_indices:
        recommendations.append({
            "crop": model.classes_[index],
            "probability": round(float(probabilities[index]) * 100, 2)
        })

    return recommendations


def train_crop_recommendation_model():
    """Train Random Forest model for crop recommendation"""

    dataset_path = download_dataset()

    if dataset_path and os.path.exists(dataset_path):
        df = pd.read_csv(dataset_path)

    else:
        # Fallback synthetic dataset
        print("Using synthetic training data...")

        np.random.seed(42)

        crops = [
            'rice', 'maize', 'chickpea', 'kidneybeans',
            'pigeonpeas', 'mothbeans', 'mungbean',
            'blackgram', 'lentil', 'pomegranate',
            'banana', 'mango', 'grapes',
            'watermelon', 'muskmelon', 'apple',
            'orange', 'papaya', 'coconut',
            'cotton', 'jute', 'coffee'
        ]

        data = []

        for crop in crops:

            if crop in ['rice', 'jute']:
                n = np.random.uniform(80, 140)
                p = np.random.uniform(40, 80)
                k = np.random.uniform(50, 100)
                temp = np.random.uniform(20, 35)
                humid = np.random.uniform(70, 90)
                ph = np.random.uniform(5.5, 7.0)
                rain = np.random.uniform(150, 300)

            elif crop in ['wheat', 'maize']:
                n = np.random.uniform(60, 120)
                p = np.random.uniform(30, 70)
                k = np.random.uniform(40, 80)
                temp = np.random.uniform(15, 30)
                humid = np.random.uniform(50, 75)
                ph = np.random.uniform(6.0, 7.5)
                rain = np.random.uniform(50, 150)

            elif crop in ['apple', 'orange', 'grapes']:
                n = np.random.uniform(20, 60)
                p = np.random.uniform(10, 40)
                k = np.random.uniform(20, 60)
                temp = np.random.uniform(15, 28)
                humid = np.random.uniform(40, 70)
                ph = np.random.uniform(6.0, 7.0)
                rain = np.random.uniform(60, 120)

            else:
                n = np.random.uniform(40, 100)
                p = np.random.uniform(20, 60)
                k = np.random.uniform(30, 70)
                temp = np.random.uniform(18, 32)
                humid = np.random.uniform(55, 80)
                ph = np.random.uniform(5.8, 7.2)
                rain = np.random.uniform(80, 200)

            for _ in range(100):

                data.append([
                    n + np.random.normal(0, 5),
                    p + np.random.normal(0, 5),
                    k + np.random.normal(0, 5),
                    temp + np.random.normal(0, 2),
                    humid + np.random.normal(0, 5),
                    ph + np.random.normal(0, 0.3),
                    rain + np.random.normal(0, 10),
                    crop
                ])

        df = pd.DataFrame(
            data,
            columns=[
                'N',
                'P',
                'K',
                'temperature',
                'humidity',
                'ph',
                'rainfall',
                'label'
            ]
        )


    # Feature preparation

    feature_columns = [
        'N',
        'P',
        'K',
        'temperature',
        'humidity',
        'ph',
        'rainfall'
    ]

    X = df[feature_columns]

    y = df['label']


    # Scaling

    scaler = StandardScaler()

    X_scaled = scaler.fit_transform(X)


    # Train-test split

    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled,
        y,
        test_size=0.2,
        random_state=42
    )


    # Random Forest Model

    rf_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=15,
        min_samples_split=5,
        random_state=42,
        n_jobs=-1
    )


    rf_model.fit(
        X_train,
        y_train
    )


    # Evaluation FIX:
    # predict() is used instead of predict_proba()

    y_pred = rf_model.predict(X_test)


    accuracy = accuracy_score(
        y_test,
        y_pred
    )

    print(f"Model Accuracy: {accuracy * 100:.2f}%")


    print("\nClassification Report:")

    print(
        classification_report(
            y_test,
            y_pred
        )
    )


    # Save model, scaler and feature columns

    os.makedirs(
        os.path.dirname(__file__),
        exist_ok=True
    )


    joblib.dump(
        rf_model,
        os.path.join(
            os.path.dirname(__file__),
            'crop_model.pkl'
        )
    )


    joblib.dump(
        scaler,
        os.path.join(
            os.path.dirname(__file__),
            'crop_scaler.pkl'
        )
    )


    joblib.dump(
        feature_columns,
        os.path.join(
            os.path.dirname(__file__),
            'feature_columns.pkl'
        )
    )


    print("Model saved successfully!")

    return rf_model, scaler, feature_columns



if __name__ == '__main__':

    model, scaler, feature_columns = train_crop_recommendation_model()


    # Example call for top 3 recommendations

    sample_input = {
        'N': 90,
        'P': 45,
        'K': 50,
        'temperature': 25,
        'humidity': 80,
        'ph': 6.5,
        'rainfall': 200
    }


    top_3 = get_top_3_recommendations(
        model,
        scaler,
        feature_columns,
        sample_input
    )


    print("\nTop 3 Crop Recommendations:")

    for crop in top_3:
        print(crop)