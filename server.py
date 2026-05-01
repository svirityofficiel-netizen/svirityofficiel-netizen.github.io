import os
import time
import threading
import requests
from flask import Flask, jsonify

app = Flask(__name__)

BASE = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(BASE, "PROXY-Preparation-1.txt")
TEST_URL = "http://clients3.google.com/generate_204"
TIMEOUT = 5

live_proxies = []
ranked_proxies = []


def check(proxy):
    try:
        if "://" not in proxy:
            proxy = "http://" + proxy
        start = time.time()
        r = requests.get(TEST_URL, proxies={"http": proxy, "https": proxy}, timeout=TIMEOUT)
        elapsed = round((time.time() - start) * 1000)
        if r.status_code in (200, 204):
            return proxy, elapsed
    except Exception:
        pass
    return None, None


def get_country(ip):
    try:
        r = requests.get(f"http://ip-api.com/json/{ip}?fields=country,countryCode", timeout=3)
        data = r.json()
        return data.get("country", "Unknown"), data.get("countryCode", "??")
    except Exception:
        return "Unknown", "??"


def checker_loop():
    global live_proxies
    while True:
        if not os.path.exists(INPUT_FILE):
            time.sleep(10)
            continue

        with open(INPUT_FILE, "r") as f:
            proxies = [line.strip() for line in f if line.strip()]

        results = []
        for proxy in proxies:
            proxy, elapsed = check(proxy)
            if proxy:
                results.append({"proxy": proxy, "ms": elapsed})
            time.sleep(1)

        live_proxies = results


def ranker_loop():
    global ranked_proxies
    while True:
        time.sleep(30)
        if not live_proxies:
            continue

        enriched = []
        for item in live_proxies:
            proxy = item["proxy"]
            ip = proxy.split("://")[-1].split(":")[0]
            country, code = get_country(ip)
            enriched.append({
                "proxy": proxy,
                "ms": item["ms"],
                "country": country,
                "country_code": code
            })
            time.sleep(1)

        ranked_proxies = sorted(enriched, key=lambda x: x["ms"])


threading.Thread(target=checker_loop, daemon=True).start()
threading.Thread(target=ranker_loop, daemon=True).start()


@app.route("/", methods=["GET"])
def get_live():
    proxies = [item["proxy"] for item in live_proxies]
    return jsonify({"count": len(proxies), "proxies": proxies})


@app.route("/txt", methods=["GET"])
def get_live_txt():
    proxies = "\n".join(item["proxy"] for item in live_proxies)
    return proxies, 200, {"Content-Type": "text/plain"}


@app.route("/ranked", methods=["GET"])
def get_ranked():
    return jsonify({"count": len(ranked_proxies), "proxies": ranked_proxies})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
