# Plant Whisperer

An IoT + Deep Neural Network + Generative AI system that senses a plant's environment, predicts when it will need water, and tells you in the plant's own voice.

**The DNN decides what is happening. The GenAI explains it.**

## How it works

```
Sensors -> ESP32 -> Flask server + DNN -> Claude -> Telegram bot + web dashboard
```

| Layer | What it does |
|---|---|
| IoT | An ESP32 reads soil moisture, temperature, humidity and light, and posts JSON over WiFi every 30 s |
| DNN | A small Keras MLP (5 -> 32 -> 16 -> 1) predicts the hours until the soil reaches the 25% dry threshold |
| GenAI | Claude turns the sensor facts and the prediction into a short message in the plant's voice |

The plant speaks only when its mood changes (thirsty below 25% soil moisture, drowning above 80%, otherwise happy). If there is no API key or the call fails, built-in message templates are used.

## Project status

| Part | Status |
|---|---|
| ESP32 firmware | Written, not yet tested on hardware |
| DNN | Trained on synthetic data (validation MAE about 0.7 h on that data) |
| Server, LLM and Telegram pipeline | Working, tested end to end with the simulator |
| Web dashboard | Working |
| Hardware assembly and sensor calibration | Pending |
| Fine-tuning on real sensor data | Pending |

Note: the DNN currently learns an assumed drying formula, not real plant behaviour. Its real-world accuracy has not been measured.

## Repository structure

```
server.py                         Flask server: DNN inference, mood logic, Claude and Telegram, dashboard API
simulator.py                      Fake ESP32 that streams a realistic scenario (no hardware needed)
train.py                          Generates synthetic data and trains the DNN
app.html                          Web dashboard (served by server.py at /)
plant_model.keras, norm.npz       Trained model and input normalisation values
firmware/plant_esp32/             ESP32 firmware (Arduino IDE)
docs/                             Presentation and project report
requirements.txt
```

## Quick start (no hardware needed)

Requires Python 3.9 to 3.12.

```bash
pip install -r requirements.txt

# terminal 1
python server.py

# terminal 2
python simulator.py
```

Open http://localhost:5000. The status in the corner shows "Live from server". The simulated plant dries out, becomes thirsty, is watered, becomes too wet, and dries again.

Open `http://<your-computer-ip>:5000` from a phone on the same WiFi to use it as a mobile app.

## Optional: Claude messages and Telegram

Set these environment variables before starting the server. Never put keys in the code or commit them.

```bash
# Windows (cmd)
set ANTHROPIC_API_KEY=your_key
set TG_TOKEN=your_telegram_bot_token
set TG_CHAT_ID=your_chat_id

# Mac / Linux
export ANTHROPIC_API_KEY=your_key
export TG_TOKEN=your_telegram_bot_token
export TG_CHAT_ID=your_chat_id
```

Without them the server still runs and uses built-in messages.

## Hardware

| Component | Pin | Approx. cost (INR) |
|---|---|---|
| ESP32 dev board | - | 450 |
| Soil moisture sensor | GPIO34 | 80 |
| DHT11 | GPIO4 | 120 |
| LDR + 10k resistor (voltage divider) | GPIO35 | 30 |
| Breadboard + jumper wires | - | 150 |
| **Total** | | **about 830** |

All sensors run at 3.3 V. Prices are rough estimates.

1. Open `firmware/plant_esp32/plant_esp32.ino` in the Arduino IDE (install the ESP32 board package and the "DHT sensor library" and "Adafruit Unified Sensor" libraries).
2. Set `WIFI_SSID`, `WIFI_PASS` and your computer's IP in `SERVER`. Do not commit your real WiFi password.
3. Calibrate the sensors: note the raw soil value in dry air and in water, then update `SOIL_DRY_RAW` and `SOIL_WET_RAW` (and the LDR values) in `server.py` and `simulator.py`.

## Retraining the model

```bash
python train.py
```

This writes `plant_model.keras` and `norm.npz`. The server logs every reading to `log.csv`, which can later be used to fine-tune the model on real data.

## Limitations

- Trained on synthetic data, so predictions are not yet validated on real plants.
- DHT11 accuracy is limited, the ESP32 ADC is nonlinear, and resistive soil probes corrode.
- The server computer must be running and reachable; the LLM needs internet access and an API key.
- The model treats all plants alike (no species or pot size).

## Roadmap

- Fine-tune on logged real data, or try an LSTM on time series
- Automatic watering with a pump
- Multi-plant dashboard
- On-device inference on the ESP32 (TinyML)
