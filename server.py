import threading
import time
import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, jsonify

app = Flask(__name__)

BASE = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(BASE, "PROXY-Preparation-1.txt")
OUTPUT_FILE = os.path.join(BASE, "PROXY-live-1.txt")
TEST_URL = "http://httpbin.org/ip"
TIMEOUT = 5
MAX_WORKERS = 50
CHECK_INTERVAL = 60


def check(proxy):
    try:
        if "://" not in proxy:
            proxy = "http://" + proxy
        r = requests.get(TEST_URL, proxies={"http": proxy, "https": proxy}, timeout=TIMEOUT)
        if r.status_code == 200:
            return proxy
    except Exception:
        pass
    return None


def run_checker():
    if not os.path.exists(INPUT_FILE):
        return
    with open(INPUT_FILE, "r") as f:
        proxies = [line.strip() for line in f if line.strip()]
    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(check, p): p for p in proxies}
        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)
    with open(OUTPUT_FILE, "w") as f:
        f.write("\n".join(results))


def scheduler():
    while True:
        run_checker()
        time.sleep(CHECK_INTERVAL)


threading.Thread(target=scheduler, daemon=True).start()


@app.route("/", methods=["GET"])
def get_live():
    if not os.path.exists(OUTPUT_FILE):
        return jsonify({"count": 0, "proxies": []})
    with open(OUTPUT_FILE, "r") as f:
        proxies = [line.strip() for line in f if line.strip()]
    return jsonify({"count": len(proxies), "proxies": proxies})


@app.route("/txt", methods=["GET"])
def get_live_txt():
    if not os.path.exists(OUTPUT_FILE):
        return "", 200, {"Content-Type": "text/plain"}
    with open(OUTPUT_FILE, "r") as f:
        return f.read(), 200, {"Content-Type": "text/plain"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
