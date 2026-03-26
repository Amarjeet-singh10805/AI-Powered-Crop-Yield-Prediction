import pandas as pd
import numpy as np
import pickle
import os
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error

df = pd.read_csv("crop_yield.csv")
df.columns = df.columns.str.strip()

for col in ['Crop', 'Season', 'State']:
    df[col] = df[col].astype(str).str.strip()

df = df[df['Yield'] < df['Yield'].quantile(0.99)]
df = df.dropna()

print(f"Dataset shape: {df.shape}")
print(f"Unique crops: {df['Crop'].nunique()}")
print(f"Unique states: {df['State'].nunique()}")
print(f"Unique seasons: {df['Season'].nunique()}")
print(f"Year range: {df['Crop_Year'].min()} - {df['Crop_Year'].max()}")

le_crop = LabelEncoder()
le_season = LabelEncoder()
le_state = LabelEncoder()

df['Crop_enc'] = le_crop.fit_transform(df['Crop'])
df['Season_enc'] = le_season.fit_transform(df['Season'])
df['State_enc'] = le_state.fit_transform(df['State'])

features = ['Crop_enc', 'Season_enc', 'State_enc', 'Area', 'Annual_Rainfall', 'Fertilizer', 'Pesticide']
X = df[features]
y = df['Yield']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = GradientBoostingRegressor(n_estimators=200, learning_rate=0.1, max_depth=5, random_state=42)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
r2 = r2_score(y_test, y_pred)
mae = mean_absolute_error(y_test, y_pred)
print(f"\nModel R² Score: {r2:.4f}")
print(f"Model MAE:      {mae:.4f}")

os.makedirs("model", exist_ok=True)
with open("model/crop_model.pkl", "wb") as f:
    pickle.dump({
        "model": model,
        "le_crop": le_crop,
        "le_season": le_season,
        "le_state": le_state,
        "crops": sorted(df['Crop'].unique().tolist()),
        "seasons": sorted(df['Season'].unique().tolist()),
        "states": sorted(df['State'].unique().tolist()),
        "year_min": int(df['Crop_Year'].min()),
        "year_max": int(df['Crop_Year'].max()),
    }, f)

print("\nModel saved to model/crop_model.pkl")
