import time
import hmac
import hashlib
import requests
from datetime import datetime

from localdata.config.setting import BINANCE_API_KEY, BINANCE_API_SECRET, BINANCE_BASE_URL, PROXY_URL


def get_signature(query_string: str, secret: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


def get_account():
    timestamp = int(time.time() * 1000)
    query_string = f"timestamp={timestamp}"
    signature = get_signature(query_string, BINANCE_API_SECRET)

    url = f"{BINANCE_BASE_URL}/api/v3/account?{query_string}&signature={signature}"
    headers = {"X-MBX-APIKEY": BINANCE_API_KEY}

    response = requests.get(url, headers=headers, proxies={"http": PROXY_URL, "https": PROXY_URL})
    print(f"Status: {response.status_code}")

    ts = datetime.now().strftime("%y%m%d_%H%M%S")
    filename = f"localdata/data/account/spot_account_{ts}.json"
    with open(filename, "w") as f:
        f.write(response.text)
    print(f"Saved to {filename}")


if __name__ == "__main__":
    get_account()
