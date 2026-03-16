import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score
import joblib

# Load dataset
df = pd.read_csv("../dataset/crime_data.csv")
# Convert categorical columns
df['time_of_day'] = df['time_of_day'].map({'Day':0,'Night':1})
df['crowd_density'] = df['crowd_density'].map({'Low':0,'Medium':1,'High':2})

# Features (ignore location column)
X = df[['crime_rate',
        'population_density',
        'street_light',
        'cctv',
        'police_distance',
        'time_of_day',
        'crowd_density']]

# Target
y = df['safety_label']

# Encode target labels
label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y_encoded,
    test_size=0.2,
    random_state=42,
    stratify=y_encoded
)

# Train model
model = RandomForestClassifier(
    n_estimators=100,
    random_state=42
)

model.fit(X_train, y_train)

# Test model
y_pred = model.predict(X_test)

accuracy = accuracy_score(y_test, y_pred)

print("Model accuracy:", accuracy)

# Save model
joblib.dump(model, "safetymodel.pkl")
joblib.dump(label_encoder, "label_encoder.pkl")

print("Model and encoder saved successfully.")