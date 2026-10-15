# hyperos-auto-apply-script

Grabs a Xiaomi HyperOS bootloader-unlock slot by firing apply requests the instant Xiaomi's
daily queue resets (00:00 Beijing time), using NTP-synchronized clocks.

## Files (`script/`)

| File | Purpose |
| --- | --- |
| `unlock.py` | The script |
| `token.example` / `timeshift.example` | Templates for the two data files |
| `token` | Local-only: one `new_bbs_serviceToken` (cookie value) per line — **gitignored** |
| `timeshift` | Local-only: send offset in milliseconds per line (same line number as the token) — **gitignored** |

Copy the examples to `token` / `timeshift` and fill in your values; the real files contain
account credentials and never leave your machine.

## Requirements

- Python 3 with `pip`
- First run auto-installs: `ntplib`, `pytz`, `urllib3`, `colorama`

## Usage

```bash
cd script
python unlock.py              # wait for 00:00 Beijing time, then burst
python unlock.py --test       # burst immediately, no waiting
python unlock.py --token 2    # use token/timeshift line 2, no prompt
```

## Flow

1. Validates the token account state (`is_pass=4`, button state 1–3); exits if expired or not eligible.
2. Live mode: syncs Beijing time over NTP, waits for the next midnight minus the line's
   timeshift, then sends up to 10 staggered POSTs to the `bl-auth` endpoint.
3. On approval (`apply_result=1` or code `100003`) it re-checks the unlock status and stops.

Both data files are read relative to `unlock.py`, so it can be run from any directory.
