import argparse
import hashlib
import json
import linecache
import os
import platform
import random
import sys
import time
from datetime import datetime, timedelta, timezone

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


def parse_args():
    parser = argparse.ArgumentParser(description="Xiaomi Bootloader Unlock Script")
    parser.add_argument("--test", action="store_true",
                        help="send requests now, without waiting for 00:00 Beijing time")
    return parser.parse_args()


