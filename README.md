# ADL KMD KCSAP FTP Decoder

An [ADL FTP](https://github.com/wmo-raf/adl-ftp-plugin) decoder plugin for the Kenya Meteorological Department (KMD)
KCSAP automatic weather station network.

## Description

This repository contains a decoder for the generic [ADL FTP plugin](https://github.com/wmo-raf/adl-ftp-plugin). It
registers the **KCSAP / KMD AWS** decoder (`kcsap`), which reads the per-minute CSV files the KCSAP loggers deliver
over FTP and turns them into ADL observation records.

[ADL](https://github.com/wmo-raf/adl) is a web based tool that automates periodic observation data collection from
different Automatic Weather Station (AWS) networks and pushes it to receiving systems.

**Requires** `adl-ftp-plugin` >= 0.10.0 to be installed in the ADL instance (for the *Populate Variable Mappings from
Decoder* action; decoding itself works with any version).

## File format

One file per station per minute, named `KMD_<stationID>_<YYYYMMDDHHMM>.csv`, e.g. `KMD_001_202408241414.csv`. Each
file has exactly two lines:

```
KMD,001,202408241414
KMD,001,202408241414, 1,13.39, 18.4, 62.0, 0.0,  80.6, 826.4,/////,//////,   0,////,////,////,////,////,////,/////,/////,/////,/////,/////,/////, 2.47, 3.88,114.0,14:13:03,120.6,100.1,137.3
```

- Line 1 is a short preview; line 2 is the 32-field record. Files that do not have exactly two lines are skipped.
- The timestamp (field 3, `YYYYMMDDHHMM`) is **UTC**. Records are emitted with an aware UTC `observation_time`; ADL
  localises it to the station link's timezone.
- Any field made of slashes (`////`, `/////` ...) is the feed's missing-value marker and decodes to `None`.
- Occasionally two records are glued into one line, joined by a literal `?KMD`; the decoder splits them.
- Field 29 (`HH:MM:SS`, time of the minute's peak gust) is discarded: gust speed and direction are stored as period
  statistics at the record's minute timestamp, like every other field.

### Variables

All 157 KCSAP stations share the same layout, so the field map is fixed in the decoder (`decoders/kcsap.py`,
`VARIABLES`). Index is 0-based within the 32-field record.

| Index | File variable name        | File unit | ADL parameter (auto-created) | ADL unit |
|------:|--------------------------|-----------|------------------------------|----------|
| 5     | `air_temperature_2m`     | °C        | Air Temperature 2m           | °C       |
| 6     | `relative_humidity_2m`   | %         | Relative Humidity 2m         | %        |
| 7     | `precipitation_1m`       | mm        | Precipitation 1m             | mm       |
| 8     | `total_radiation_1m`     | W/m^2     | Total Radiation 1m           | W/m^2    |
| 9     | `air_pressure_2m`        | hPa       | Air Pressure 2m              | hPa      |
| 11    | `evaporation_1m`         | mm        | Evaporation 1m               | mm       |
| 12    | `leaf_wetness_2m`        | 1         | Leaf Wetness 2m              | 1        |
| 13–18 | `soil_temperature_<d>m` (d = 0.05, 0.1, 0.2, 0.5, 1, 1.2) | °C | Soil Temperature &lt;d&gt;m | °C |
| 19–24 | `soil_moisture_<d>m` (d = 0.05, 0.1, 0.2, 0.5, 1, 1.2)    | %  | Soil Moisture &lt;d&gt;m    | %  |
| 25    | `wind_speed_2m`          | knot      | Wind Speed 2m                | m/s      |
| 26    | `wind_gust_speed_2m`     | knot      | Wind Gust Speed 2m           | m/s      |
| 27    | `wind_gust_direction_2m` | degree    | Wind Gust Direction 2m       | degree   |
| 28    | *(gust time — discarded)* |          |                              |          |
| 29    | `wind_direction_avg_2m`  | degree    | Wind Direction Avg 2m        | degree   |
| 30    | `wind_direction_min_2m`  | degree    | Wind Direction Min 2m        | degree   |
| 31    | `wind_direction_max_2m`  | degree    | Wind Direction Max 2m        | degree   |

Wind speeds arrive in **knots**; ADL converts them to m/s through the variable mapping's file unit. Wind directions are
declared with the *circular* aggregation method; precipitation with the *precipitation* unit-conversion context.

## Setting up KMD in ADL

1. **Network connection** — add a *Network FTP/SFTP* connection with the KMD FTP credentials and choose the decoder
   **KCSAP / KMD AWS**.
2. **Variable mappings** — in the *Network Connections* list, open the connection's *…* menu and click
   **Populate Variable Mappings from Decoder**. Review the 25 pre-filled rows (existing Units / Data Parameters are
   pre-selected where the names match; otherwise they are created on submit) and submit. Re-running the action only
   shows variables that are still unmapped.
3. **Station links** — one per station. Files are one-per-minute with the timestamp in the name, so *Direct Fetch* is
   the natural listing strategy:
   - Remote Path: the directory holding the files
   - Listing Strategy: *Direct Fetch*
   - Direct Fetch Prefix: `KMD_<stationID>_` (e.g. `KMD_001_`)
   - Direct Fetch Datetime Format: `YYYYMMDDHHMM`
   - Direct Fetch Interval (minutes): `1`
   - Direct Fetch File Extension: `.csv`
   - Direct Fetch Datetime Timezone: `UTC`

   *Filter by Date* with file pattern `KMD_001_*.csv` and filename date format `YYYYMMDDHHMM` also works if the
   directory is small enough to list.
4. Use the connection's **Test Decoder Configuration** action with a sample file to confirm the decode before the first
   collection.

## Development

Tests live in `plugins/adl_kmd_kcsap_ftp_decoder/src/adl_kmd_kcsap_ftp_decoder/tests/` and use the two real sample
files in `tests/fixtures/`. Run them inside the dev container:

```bash
docker compose exec adl adl test adl_kmd_kcsap_ftp_decoder
```

## Getting started

### Prerequisites

- Docker and Docker Compose installed on your machine.
- Git installed on your machine.

### Install and build the ADL Core Image

The ADL KMD KCSAP FTP Decoder is a module intended to be installed in an [ADL](https://github.com/wmo-raf/adl)
instance. This means that you need to first get the core ADL system and build it on your local development environment.

You can follow the instructions on the [ADL core repository](https://github.com/wmo-raf/adl) to install and build the
ADL core image

### Install ADL KMD KCSAP FTP Decoder

The `dev.Dockerfile` file uses the `adl` image as a base image. The `ADL KMD KCSAP FTP Decoder` is
installed during the build process. Using docker mounted volumes, the plugin is editable such that any changes made to
the code trigger Django to reload the development server, allowing you to see the changes as you develop

1. Clone the plugin repository:

```bash
git clone https://github.com/wmo-raf/adl-kmd-kcsap-ftp-decoder.git
cd adl-kmd-kcsap-ftp-decoder
```

2. Create a `.env` file using the provided `.env.sample` file:

```bash
cp .env.sample .env
```

3. Edit the `.env` file to set the required environment variables

```bash
nano .env
```

You can use the default values provided in the `.env.sample` file, but be sure to set the following correctly:

- `PLUGIN_BUILD_UID`: The UID of the user that will run the plugin inside the container
- `PLUGIN_BUILD_GID`: The GID of the user that will run the plugin inside the container

You can find the UID and GID of your user by running the following command:

```bash
id -u
id -g
```

4. Build the plugin image:

```bash
docker compose build
```

If you are getting errors like
`failed to solve: adl:latest: failed to resolve source metadata for docker.io/library/adl:latest: pull access denied`,
you might need to disable `DOCKER_BUILDKIT` when building the image.

You can do this by running the following

```bash
DOCKER_BUILDKIT=0  docker compose build
```

5. Start the plugin:

```bash
docker compose up
```

If everything is set up correctly, you should see the plugin starting up and listening for incoming requests. You can
access the plugin at `http://localhost:8000`. The port number can be changed using the `PORT` environment variable in
the `.env`. The default port is `8000`.

6. Create superuser

```bash
docker compose exec adl adl createsuperuser
```

The `adl`command is shorthand for `python manage.py` command. You can use it to run any Django management command
inside the container.


