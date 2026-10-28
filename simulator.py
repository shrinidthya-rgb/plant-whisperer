"""Fake ESP32: streams a realistic scenario to the server so you can demo with NO hardware.
Run the server first (python server.py), then: python simulator.py
Scenario: plant dries -> thirsty -> you water it -> drowning -> dries back to happy.
"""
import time, random, requests
URL = "http://localhost:5000/reading"
SOIL_DRY_RAW, SOIL_WET_RAW = 3200, 1400     # keep equal to server.py
LDR_DARK_RAW, LDR_BRIGHT_RAW = 3800, 300
DELAY = float(__import__("os").getenv("DELAY","2"))          # real seconds between readings
STEP = 3600        # simulated seconds per reading (1 hour)

soil, sim_t = 65.0, time.time()
for tick in range(int(__import__("os").getenv("TICKS","60"))):
    if soil < 20:            # the human waters the plant
        print(">>> watering the plant"); soil = 92.0
    temp = round(30 + random.uniform(-0.5, 0.5), 1)
    hum = round(45 + random.uniform(-2, 2), 1)
    light = 60 + random.uniform(-5, 5)
    soil_raw = SOIL_DRY_RAW + (SOIL_WET_RAW - SOIL_DRY_RAW) * soil / 100
    ldr_raw = LDR_DARK_RAW + (LDR_BRIGHT_RAW - LDR_DARK_RAW) * light / 100
    r = requests.post(URL, json={"soil_raw": int(soil_raw), "ldr_raw": int(ldr_raw),
                                 "temp": temp, "hum": hum, "ts": sim_t}, timeout=30).json()
    print(f"soil {r['soil']:.0f}%  mood={r['mood']:<8}  predicted hours to dry={r['hours']:.1f}")
    soil -= random.uniform(1.6, 2.4)   # fast drying so the demo moves quickly
    sim_t += STEP
    time.sleep(DELAY)
