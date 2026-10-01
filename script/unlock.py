import argparse
import hashlib
import json
import linecache
import os
import platform
import random
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

for package_name in ("ntplib", "pytz", "urllib3", "icmplib", "colorama", "linecache"):
    try:
        __import__(package_name)
    except ImportError:
        print(f"Installing package {package_name}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])

os.system("cls" if os.name == "nt" else "clear")

import ntplib
import pytz
import urllib3
from icmplib import ping
from colorama import Fore, Style, init

init(autoreset=True)
col_g = Fore.GREEN
col_gb = Style.BRIGHT + Fore.GREEN
col_b = Fore.BLUE
col_bb = Style.BRIGHT + Fore.BLUE
col_y = Fore.YELLOW
col_yb = Style.BRIGHT + Fore.YELLOW
col_r = Fore.RED
col_rb = Style.BRIGHT + Fore.RED

BEIJING_TZ = pytz.timezone("Asia/Shanghai")

script_version = "flow-fixed-v1"

STATUS_URL = "https://sgp-api.buy.mi.com/bbs/api/global/user/bl-switch/state"
APPLY_URL = "https://sgp-api.buy.mi.com/bbs/api/global/apply/bl-auth"

NTP_SERVERS = [
    "ntp0.ntp-servers.net", "ntp1.ntp-servers.net", "ntp2.ntp-servers.net",
    "ntp3.ntp-servers.net", "ntp4.ntp-servers.net", "ntp5.ntp-servers.net",
    "ntp6.ntp-servers.net",
]

USER_AGENTS = [
    "okhttp/4.12.0",
    "okhttp/4.11.0 (Linux; Android 14)",
    "Dalvik/2.1.0 (Linux; U; Android 14)",
]


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def read_token_and_shift(line_number):
    token = linecache.getline("token.txt", line_number).strip()
    if not token:
        print(col_r + "❌ No token on that line" + Fore.RESET)
        sys.exit(1)
    try:
        shift_ms = float(linecache.getline("timeshift.txt", line_number).strip())
    except:
        shift_ms = 0.0
    return token, shift_ms / 1000  # ms -> seconds


def generate_device_id():
    seed = f"{random.random()}-{time.time()}-{random.randint(1, 10000)}"
    return hashlib.sha1(seed.encode("utf-8")).hexdigest().upper()


def make_cookie(token, device_id):
    return f"new_bbs_serviceToken={token};versionCode=500411;versionName=5.4.11;deviceId={device_id};"


def fetch_beijing_time():
    client = ntplib.NTPClient()
    for server in NTP_SERVERS:
        try:
            response = client.request(server, version=3)
            return datetime.fromtimestamp(response.tx_time, timezone.utc).astimezone(BEIJING_TZ)
        except Exception as exc:
            print(col_y + f"server {server} failed: {exc}" + Fore.RESET)
    print(col_r + "❌ All NTP servers failed" + Fore.RESET)
    return None


def synced_beijing_time(origin_beijing, origin_counter):
    return origin_beijing + timedelta(seconds=time.time() - origin_counter)


def wait_for_window(origin_beijing, origin_counter, shift_seconds):
    target = (origin_beijing + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    target -= timedelta(seconds=shift_seconds)
    print(col_yb + "⏳ Waiting for the daily reset..." + Fore.RESET)
    while True:
        now = synced_beijing_time(origin_beijing, origin_counter)
        remaining = (target - now).total_seconds()
        if remaining <= 0:
            print(col_gb + "🚀 Flood window open" + Fore.RESET)
            return now
        time.sleep(min(0.1, remaining - 0.4) if remaining > 1 else 0.001)


class Session:
    def __init__(self):
        self.http = urllib3.PoolManager(maxsize=5, timeout=urllib3.Timeout(connect=1.5, read=5.0))

    def request(self, method, url, headers):
        request_headers = dict(headers)
        request_headers.update({
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
            "Origin": "https://i.mi.com",
            "Referer": "https://i.mi.com/forum/",
            "User-Agent": random.choice(USER_AGENTS),
            "Connection": "close",
        })
        body = '{"is_retry":true}'.encode("utf-8") if method == "POST" else None
        try:
            return self.http.request(method, url, headers=request_headers, body=body, preload_content=False)
        except Exception as exc:
            print(col_r + f"🌐 Network error: {exc}" + Fore.RESET)
            return None


def check_unlock_status(session, cookie):
    response = session.request("GET", STATUS_URL, {"Cookie": cookie})
    if response is None:
        print(col_r + "❌ Network error - status unavailable" + Fore.RESET)
        return False
    try:
        response_data = json.loads(response.data.decode("utf-8"))
    except Exception as exc:
        print(col_r + f"❌ Status parse failed: {exc}" + Fore.RESET)
        return False
    finally:
        response.release_conn()
    if response_data.get("code") == 100004:
        print(col_rb + "❌ COOKIE EXPIRED - stopping" + Fore.RESET)
        return False
    data = response_data.get("data", {})
    is_pass = data.get("is_pass")
    button_state = data.get("button_state")
    print(col_g + f"[Account]: is_pass={is_pass}, button_state={button_state}" + Fore.RESET)
    print(col_g + "[FULL STATUS]:" + Fore.RESET)
    print(json.dumps(response_data, indent=2, ensure_ascii=False))
    if is_pass == 4 and button_state in (1, 2, 3):
        print(col_gb + "✅ READY TO SEND REQUESTS!" + Fore.RESET)
        return True
    print(col_r + "❌ Account not ready - exiting" + Fore.RESET)
    return False


def send_burst(session, cookie, test, origin_beijing=None, origin_counter=None):
    max_requests = 10
    print(col_yb + f"{'🔥 TEST' if test else '🚀 LIVE'} BURST: {max_requests} requests max" + Fore.RESET)
    for _ in range(max_requests):
        request_time = datetime.now(BEIJING_TZ) if test else synced_beijing_time(origin_beijing, origin_counter)
        print(col_g + f"[📡 REQ {request_time.strftime('%H:%M:%S.%f')}]" + Fore.RESET)
        response = session.request("POST", APPLY_URL, {"Cookie": cookie})
        if not response:
            time.sleep(0.1 if test else random.uniform(0.005, 0.015))
            continue
        try:
            response_data = json.loads(response.data.decode("utf-8"))
        finally:
            response.release_conn()
        print(col_g + "[FULL RESPONSE]:" + Fore.RESET)
        print(json.dumps(response_data, indent=2, ensure_ascii=False))
        code = response_data.get("code")
        data = response_data.get("data", {})
        apply_result = data.get("apply_result")
        if code == 0 and apply_result == 1:
            print(col_gb + "🎉 APPROVED! Checking status..." + Fore.RESET)
            return check_unlock_status(session, cookie)
        if code == 0 and apply_result in (3, 4):
            print(col_y + f"⏰ Blocked until {data.get('deadline_format', 'unknown')}" + Fore.RESET)
        if code == 100003:
            print(col_y + "🔄 Possible approval - checking status..." + Fore.RESET)
            return check_unlock_status(session, cookie)
        time.sleep(0.1 if test else random.uniform(0.005, 0.015))
    print(col_g + f"✅ Burst complete: {max_requests} requests sent" + Fore.RESET)
    return False


def parse_args():
    parser = argparse.ArgumentParser(description="Xiaomi Bootloader Unlock Script")
    parser.add_argument("--test", action="store_true",
                        help="send requests now, without waiting for 00:00 Beijing time")
    parser.add_argument("--token", type=int, help="token line number to use")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.token:
        token_number = args.token
    else:
        token_number = int(input(col_g + "[Token line number]: " + Fore.RESET))

    token, shift_seconds = read_token_and_shift(token_number)
    clear_screen()

    print(col_yb + f"{script_version}_token_#{token_number}:" + Fore.RESET)
    if args.test:
        print(col_yb + "[TEST MODE ACTIVE - SENDS NOW]" + Fore.RESET)
    print(col_y + "Checking account status..." + Fore.RESET)

    session = Session()
    cookie = make_cookie(token, generate_device_id())

    print(col_y + "\n🔍 Checking account status (1 attempt)..." + Fore.RESET)
    if not check_unlock_status(session, cookie):
        input(col_r + "\n❌ Status check failed. Press Enter to exit..." + Fore.RESET)
        return

    if args.test:
        print(col_yb + "\n=== 🚀 TEST MODE: Sending NOW ===" + Fore.RESET)
        send_burst(session, cookie, test=True)
    else:
        origin_beijing = fetch_beijing_time()
        origin_counter = time.time()
        wait_for_window(origin_beijing, origin_counter, shift_seconds)
        send_burst(session, cookie, test=False,
                   origin_beijing=origin_beijing, origin_counter=origin_counter)

    input(col_y + "\n👉 Press Enter to exit..." + Fore.RESET)


if __name__ == "__main__":
    main()
