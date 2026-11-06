# Data behind the Satellite Physics page

Every number on the Satellite Physics page ([satellites.html](../../satellites.html)) comes from the files in this folder.

| File | What it is |
|---|---|
| `raw/celestrak-active.csv` | CelesTrak's untouched "Active Satellites" catalog in CSV form (see Source). Not edited by hand. Kept out of the repo; download it as described below and check its SHA-256. |
| `build_summary.py` | Reads the raw CSV, works out each satellite's period, altitude and speed from its mean motion, groups the catalog by orbit band and constellation, thins the low-orbit crowd for the scatter, runs the NRLMSIS 2.1 atmosphere model at three solar levels, works out the radiation budget in orbit, runs 13 checks, and writes `summary.json`. Exits with an error if any check fails. |
| `summary.json` | What the page charts: orbit bands, an altitude histogram, the constellation summaries, 2,821 drawn satellites, the physics curve, the atmosphere profile (0 to 1,200 km, three solar levels), the energy budget at four altitudes, equilibrium temperatures, and the check results. |

Run: download the CSV (see Source), save it as `raw/celestrak-active.csv`, then `python build_summary.py` (needs numpy and pymsis). The script stops if the file's fingerprint doesn't match. CelesTrak refreshes the catalog every few hours, so a later download will differ; update the fingerprint and the expected row count only after reviewing the new file.

## Source

**CelesTrak current GP element sets**, Active Satellites group, CSV format: [celestrak.org/NORAD/elements/](https://celestrak.org/NORAD/elements/) (download link `gp.php?GROUP=active&FORMAT=csv`). Accessed November 6, 2026. CelesTrak asks for at most one download per catalog update (about every two hours).

- 16,872 rows, 17 columns. One row per active satellite with its latest orbital elements (epochs from October 9 to November 8, 2026).
- Fields follow the CCSDS Orbit Data Messages standard (502.0-B-3): MEAN_MOTION is revolutions per day, ECCENTRICITY and INCLINATION describe the orbit's shape and tilt.
- SHA-256 of the raw file: `fc9ce8c41dcc0ebf02ee26d81e5bbf5363c341ea12a0a16a238dacf74a436aff`

**Atmosphere model**: NRLMSIS 2.1 (Emmert et al. 2022, doi:10.1029/2022JA030896), run through [pymsis](https://swxtrec.github.io/pymsis/) 0.13.0 at the equator, local noon on the access date, quiet geomagnetic conditions (Ap 4), and F10.7 of 70, 150 and 250 solar flux units for quiet, moderate and active sun.

**Constants**: Earth's gravitational parameter 398,600.4418 km³/s² and equatorial radius 6,378.137 km (standard values); speed of light 299,792.458 km/s; total solar irradiance 1,360 W/m², albedo 29% and 240 W/m² absorbed on average (NASA Earth Observatory, Climate and Earth's Energy Budget); standard sea-level air density 1.225 kg/m³ (U.S. Standard Atmosphere, 1976).

## How the physics is done

- Period = 1440 / mean motion (minutes). Semi-major axis from Kepler's third law: a = (μ (T / 2π)²)^(1/3). Mean altitude = a minus Earth's equatorial radius; perigee and apogee from the eccentricity. Speed = √(μ / a).
- Signal floor = four legs of altitude (up, down, and back) at the speed of light. The "edge of view" figure uses the slant range at 25° elevation.
- Footprint = the share of Earth's surface where the satellite is at least 25° above the horizon, from the central angle acos(R cos e / r) − e.
- Air heating on the front face = ½ ρ v³ (free-molecular flow, full accommodation). The resting air's own heat flux = n v̄ / 4 × 2kT. Both are upper bounds.
- Earth's glow and reflected sunlight at altitude are scaled by the view factor (R / r)².
- Equilibrium temperatures assume equal absorptivity and emissivity (a gray plate).

## Decisions

| Date | Decision |
|---|---|
| 2026-11-06 | Dataset: CelesTrak's Active Satellites group, the public, daily-refreshed catalog of every working satellite. Debris and dead satellites are left out on purpose. |
| 2026-11-06 | Altitude is measured from Earth's equatorial radius (6,378.137 km), the convention that puts the geostationary belt at the textbook 35,786 km. |
| 2026-11-06 | Orbit bands: elliptical (eccentricity above 0.25), low (below 2,000 km), geostationary (period within 10 minutes of a sidereal day), medium (below 35,000 km), high (the rest). |
| 2026-11-06 | Constellations are grouped by name prefix (Starlink, OneWeb, Kuiper, Qianfan, Guowang as HULIANWANG, Iridium, Globalstar, GPS as NAVSTAR, BeiDou, Galileo as GSAT). The geostationary belt is grouped by orbit. The space station is a landmark of its own. |
| 2026-11-06 | Scatter: every 8th low-orbit satellite (by catalog number) plus everything higher in full, so the chart stays light and the sparse upper orbits stay complete. |
| 2026-11-06 | Charts: altitude histogram (log-log), altitude against period / speed / signal floor with the physics curve, an altitude slider, three atmosphere panels, and an energy-budget bar chart. |
| 2026-11-06 | Signal delay is shown as the speed-of-light floor for four legs, labeled as a floor, not a measured ping. |
| 2026-11-06 | Antenna minimum elevation assumed at 25° for the footprint and edge-of-view figures. |
| 2026-11-06 | Atmosphere: three fixed F10.7 levels (70, 150, 250) rather than the live index, so the page is reproducible. Conditions: equator, local noon, Ap 4. |
| 2026-11-06 | Solar irradiance 1,360 W/m² and albedo 29%, matching the NASA page cited, not the more precise literature values. |
| 2026-11-06 | The station's exterior temperature swing is not quoted: the NASA article giving it survives only as reprints. The page uses equilibrium temperatures worked out from the radiation budget instead. |
| 2026-11-06 | The 100 km standard-atmosphere density is not used as a check: the NTRS PDF could not be opened to confirm it. Only the sea-level value is checked. |

## Known limitations

- Active satellites only. Rocket bodies, debris and dead satellites are tracked in other groups.
- Mean altitude hides the swing of elliptical orbits; 45 satellites with eccentricity above 0.25 are labeled elliptical and drawn at their mean.
- The atmosphere model gives typical values for one place and time. Real density at a given altitude varies by a factor of several with latitude, local time and geomagnetic storms.
- The heating figures assume every molecule gives up all its energy; real surfaces absorb less.
- Constellation matching by name misses satellites with non-standard catalog names and counts test satellites with the same prefix.
