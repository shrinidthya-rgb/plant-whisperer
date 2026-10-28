"""Plant Whisperer server: ESP32 -> DNN -> Claude -> Telegram.
pip install flask tensorflow numpy anthropic requests
Env vars: ANTHROPIC_API_KEY, TG_TOKEN, TG_CHAT_ID
Run: python server.py   (ESP32 posts to http://<laptop-ip>:5000/reading)
"""
import os, time, collections, csv
import numpy as np, requests, anthropic
from flask import Flask, request, jsonify, send_file
from tensorflow import keras

# ---- calibrate these two by reading your sensor in dry air vs a glass of water ----
SOIL_DRY_RAW, SOIL_WET_RAW = 3200, 1400
LDR_DARK_RAW, LDR_BRIGHT_RAW = 3800, 300   # depends on your LDR wiring; flip if reversed

TG_TOKEN = os.getenv("TG_TOKEN"); TG_CHAT = os.getenv("TG_CHAT_ID")
client = anthropic.Anthropic() if os.getenv("ANTHROPIC_API_KEY") else None  # offline fallback if no key
LLM = "claude-haiku-4-5-20251001"

model = keras.models.load_model("plant_model.keras")
norm = np.load("norm.npz")
app = Flask(__name__)
history = collections.deque(maxlen=60)   # (timestamp, soil_pct)
state = {"mood": None, "last": {}, "series": [], "msg": ""}

def pct(v, lo, hi):
    return float(np.clip((v - lo) / (hi - lo) * 100, 0, 100))

def drop_rate():
    """% moisture lost per hour over the last ~2 hours."""
    now = history[-1][0] if history else time.time()   # latest reading time (works with simulated time)
    pts = [(t, s) for t, s in history if now - t < 7200]
    if len(pts) < 2: return 0.5
    (t0, s0), (t1, s1) = pts[0], pts[-1]
    if t1 - t0 < 60: return 0.5
    return max((s0 - s1) / ((t1 - t0) / 3600), 0.05)

def mood_of(soil):
    return "thirsty" if soil < 25 else "drowning" if soil > 80 else "happy"

def say(text):
    print("PLANT:", text)
    if TG_TOKEN and TG_CHAT:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                      json={"chat_id": TG_CHAT, "text": text}, timeout=10)

def fallback(d):
    return {"thirsty": f"Soil is at {d['soil']:.0f}%. I will be crispy in about {d['hours']:.0f} hours. Water me, human.",
            "drowning": f"{d['soil']:.0f}% is a bit much. Please put the watering can down.",
            "happy": f"All good at {d['soil']:.0f}%. I will need water in about {d['hours']:.0f} hours."}[d["mood"]]

def plant_voice(d, user_msg=None):
    if client is None: return fallback(d)
    try:
        return _llm(d, user_msg)
    except Exception as e:
        print("LLM error, using fallback:", e); return fallback(d)

def _llm(d, user_msg=None):
    facts = (f"soil moisture {d['soil']:.0f}%, temp {d['temp']}C, humidity {d['hum']}%, "
             f"light {d['light']:.0f}%, mood {d['mood']}, DNN predicts soil hits 'dry' in "
             f"{d['hours']:.1f} hours.")
    prompt = (f"Sensor facts: {facts}\n" +
              (f"The human asks: {user_msg}" if user_msg else
               "Write one short message (max 2 sentences) to your human about how you feel and what you need."))
    r = client.messages.create(
        model=LLM, max_tokens=150,
        system="You are a witty, slightly dramatic houseplant. Stay in character, be brief, "
               "and base everything strictly on the sensor facts given. Never invent numbers.",
        messages=[{"role": "user", "content": prompt}])
    return r.content[0].text

@app.post("/reading")
def reading():
    j = request.get_json()
    soil = pct(j["soil_raw"], SOIL_DRY_RAW, SOIL_WET_RAW)   # 0=dry, 100=wet
    light = pct(j["ldr_raw"], LDR_DARK_RAW, LDR_BRIGHT_RAW)
    if history and soil - history[-1][1] > 10: history.clear()   # plant was watered: restart the trend
    ts = j.get("ts", time.time())   # simulator can send its own clock
    history.append((ts, soil))

    x = np.array([[soil, j["temp"], j["hum"], light, drop_rate()]], dtype="float32")
    hours = float(model.predict((x - norm["mean"]) / norm["std"], verbose=0)[0][0])
    d = dict(soil=soil, temp=j["temp"], hum=j["hum"], light=light,
             hours=max(hours, 0), mood=mood_of(soil))
    state["last"] = d
    state["series"] = (state["series"] + [soil])[-60:]

    with open("log.csv", "a", newline="") as f:
        csv.writer(f).writerow([time.time(), *d.values()])

    if d["mood"] != state["mood"]:       # speak only when mood changes
        state["mood"] = d["mood"]
        state["msg"] = plant_voice(d)
        say(state["msg"])
    return jsonify(d)

@app.get("/ask")
def ask():
    """Chat with the plant: http://localhost:5000/ask?q=how are you?"""
    if not state["last"]: return "No readings yet.", 503
    return plant_voice(state["last"], request.args.get("q", "How are you?"))

@app.get("/")
def index():
    return send_file("app.html")          # the phone/laptop dashboard

@app.get("/latest")
def latest():
    if not state["last"]: return jsonify(error="no data yet"), 503
    return jsonify({**state["last"], "series": state["series"], "msg": state["msg"]})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
