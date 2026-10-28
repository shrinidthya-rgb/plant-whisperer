"""Train the DNN on synthetic drying data. Run in Colab or locally.
pip install tensorflow numpy
Predicts: hours until soil moisture falls to the 'dry' threshold (25%).
Inputs:   soil_pct, temp, humidity, light_pct, drop_rate (%/hour)
"""
import numpy as np
from tensorflow import keras

rng = np.random.default_rng(0)
N = 40000
DRY = 25.0

soil  = rng.uniform(20, 95, N)
temp  = rng.uniform(15, 40, N)
hum   = rng.uniform(25, 90, N)
light = rng.uniform(0, 100, N)

# simple physical-ish drying model (% moisture lost per hour)
true_rate = np.clip(0.25 + 0.07*(temp-20) + 0.02*light - 0.015*(hum-50), 0.08, None)
obs_rate  = np.clip(true_rate * rng.normal(1, 0.15, N), 0.05, None)  # what the sensor trend shows
hours = np.clip((soil - DRY) / true_rate, 0, 72)

X = np.stack([soil, temp, hum, light, obs_rate], 1).astype("float32")
y = hours.astype("float32")
mean, std = X.mean(0), X.std(0)
Xn = (X - mean) / std

model = keras.Sequential([
    keras.layers.Input((5,)),
    keras.layers.Dense(32, activation="relu"),
    keras.layers.Dense(16, activation="relu"),
    keras.layers.Dense(1),
])
model.compile("adam", "mse", metrics=["mae"])
model.fit(Xn, y, epochs=30, batch_size=128, validation_split=0.15, verbose=2)

model.save("plant_model.keras")
np.savez("norm.npz", mean=mean, std=std)
print("Saved plant_model.keras + norm.npz")
# Tip: after collecting real readings for a few hours, fine-tune on them for extra credit.
