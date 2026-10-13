# hyperos-auto-apply-script

Sends Xiaomi HyperOS bootloader-unlock apply requests the instant the daily
counts reset (00:00 Beijing time), synchronized with NTP.

## Usage

```bash
cd script
python unlock.py --test       # fire the burst immediately
python unlock.py              # wait for the reset, then burst
```
