"""
KMD/KCSAP sample files for the documentation capture harness.

The core mock FTP server (adl/docs/screenshots/capture/mock-ftp/server.py)
runs this after writing its own TOA5 samples, with SAMPLE_ROOT, SAMPLE_TZ and
SAMPLE_HOURS in the environment. It writes one file per station per minute in
the real KCSAP shape, so a seeded Direct Fetch station link runs a genuine
collection cycle before capture:

    /data/KMD001/KMD_001_<YYYYMMDDHHMM>.csv

Two lines per file — a preview line, then the 32-field record — matching
plugins/adl_kmd_kcsap_ftp_decoder/src/adl_kmd_kcsap_ftp_decoder/tests/fixtures/.
Timestamps are UTC at minute resolution, as the decoder expects. Fields the
KCSAP feed does not populate are written as its slash marker so the guide's
"missing values" behaviour is exercised rather than described.

Nothing here is real data: values are a smooth diurnal cycle plus noise.
"""

import math
import os
import random
from datetime import datetime, timedelta, timezone

ROOT = os.environ.get("SAMPLE_ROOT", "/srv/ftp")
# Direct Fetch builds one filename per minute from the collection start date,
# so a long window costs a request per minute. Two hours is enough to fill the
# data layer and the file list while keeping the cycle quick.
MINUTES = int(os.environ.get("KCSAP_SAMPLE_MINUTES", "120"))
STATION = "001"
N_FIELDS = 32
MISSING = "/////"


def record(moment, seq):
    """One 32-field KCSAP record, 0-based indices as in the decoder."""
    rng = random.Random(f"kcsap-{moment:%Y%m%d%H%M}")
    hour = moment.hour + moment.minute / 60
    diurnal = math.sin((hour - 9) / 24 * 2 * math.pi)  # peaks mid-afternoon

    fields = [MISSING] * N_FIELDS
    fields[0] = "KMD"
    fields[1] = STATION
    fields[2] = f"{moment:%Y%m%d%H%M}"
    fields[3] = f"{seq:2d}"
    fields[4] = f"{12.5 + rng.uniform(-0.2, 0.2):.2f}"          # logger battery
    fields[5] = f"{21 + 6 * diurnal + rng.uniform(-0.4, 0.4):.1f}"   # air temp degC
    fields[6] = f"{70 - 25 * diurnal + rng.uniform(-2, 2):.1f}"      # RH percent
    fields[7] = f"{(rng.choice([0, 0, 0, 0, 0.2, 0.4]) if 14 <= hour <= 17 else 0):.1f}"  # rain mm
    solar = max(0.0, 850 * math.sin((hour - 6) / 12 * math.pi)) if 6 <= hour <= 18 else 0.0
    fields[8] = f"{solar:.1f}"                                        # total radiation
    fields[9] = f"{826 + 2 * math.sin(hour / 12 * math.pi) + rng.uniform(-0.3, 0.3):.1f}"  # pressure hPa
    fields[12] = "   0"                                               # leaf wetness
    # Soil sensors are not fitted at this demo station: left as the feed's
    # slash marker, which is what most KCSAP stations actually send.
    wind_kt = max(0.0, 4.5 + 3 * diurnal + rng.uniform(-1.2, 1.2))
    fields[25] = f"{wind_kt:.2f}"                                     # wind speed knots
    fields[26] = f"{wind_kt + rng.uniform(0.5, 2.0):.2f}"             # gust knots
    fields[27] = f"{(90 + 40 * diurnal + rng.uniform(-15, 15)) % 360:.1f}"  # gust direction
    fields[28] = f"{moment:%H:%M:%S}"                                 # time of peak gust
    avg_dir = (90 + 40 * diurnal + rng.uniform(-10, 10)) % 360
    fields[29] = f"{avg_dir:.1f}"
    fields[30] = f"{(avg_dir - rng.uniform(5, 20)) % 360:.1f}"
    fields[31] = f"{(avg_dir + rng.uniform(5, 20)) % 360:.1f}"
    return ",".join(fields)


def main():
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    directory = os.path.join(ROOT, "data", "KMD001")
    os.makedirs(directory, exist_ok=True)

    for i in range(MINUTES + 1):
        moment = now - timedelta(minutes=MINUTES - i)
        stamp = f"{moment:%Y%m%d%H%M}"
        lines = [f"KMD,{STATION},{stamp}", record(moment, i)]
        path = os.path.join(directory, f"KMD_{STATION}_{stamp}.csv")
        with open(path, "w", newline="") as f:
            f.write("\n".join(lines) + "\n")

    print(f"[mock-ftp] generated {MINUTES + 1} KCSAP minute files up to "
          f"{now:%Y-%m-%d %H:%M} UTC", flush=True)


if __name__ == "__main__":
    main()
