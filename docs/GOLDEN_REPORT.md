# Golden test report

Charts: 60 (general: 10, lagna_boundary: 10, nakshatra_boundary: 10, pre1955_india: 16, southern: 17, tithi_boundary: 4).

Reference: PyJHora 4.8.7, run 2026-10-21T04:32:16+00:00. Config: LAHIRI; mean nodes; apparent positions; Hindu sunrise; Vimshottari year 365.25 d (patched); D2 method 2 (traditional Parasara), D3/D7/D9/D10/D12/D30 method 1; elevation 0.
PyJHora also uses the Swiss Ephemeris, so this table checks conventions, not the ephemeris.

### Gated comparisons (M1 exit criterion b)

| field | compared | pass | fail | max deviation | first failures |
|---|---:|---:|---:|---|---|
| graha_longitude | 540 | 540 | 0 | 0.001796 arcsec |  |
| graha_sign | 540 | 540 | 0 |  |  |
| lagna_longitude | 60 | 60 | 0 | 0.002519 arcsec |  |
| lagna_sign | 60 | 60 | 0 |  |  |
| lagna_nakshatra_pada | 60 | 60 | 0 |  |  |
| moon_nakshatra | 60 | 60 | 0 |  |  |
| moon_pada | 60 | 60 | 0 |  |  |
| tithi | 60 | 60 | 0 |  |  |
| yoga_at_birth | 60 | 60 | 0 |  |  |
| karana_at_birth | 60 | 60 | 0 |  |  |
| vara | 60 | 60 | 0 |  |  |
| retrograde_set | 60 | 60 | 0 |  |  |
| varga_D2 | 600 | 600 | 0 |  |  |
| varga_D3 | 600 | 600 | 0 |  |  |
| varga_D7 | 600 | 600 | 0 |  |  |
| varga_D9 | 600 | 600 | 0 |  |  |
| varga_D10 | 600 | 600 | 0 |  |  |
| varga_D12 | 600 | 600 | 0 |  |  |
| varga_D30 | 600 | 600 | 0 |  |  |
| dasha_sequence | 60 | 60 | 0 |  |  |
| dasha_start_dates(<=1d) | 60 | 60 | 0 | 3.861e-06 days |  |
| birth_dasha_lord | 60 | 60 | 0 |  |  |
| sunrise_seconds(<=60s) | 40 | 40 | 0 | 4.986e-07 s |  |
| gulika_start_day_birth | 26 | 26 | 0 | 0.1569 arcmin |  |

### Informational comparisons (known convention differences / reference bugs)

| field | compared | pass | fail | max deviation | first failures |
|---|---:|---:|---:|---|---|
| karana_vs_pyjhora_karana_fn | 60 | 60 | 0 |  |  |
| yoga_vs_pyjhora_yogam_fn(sunrise) | 60 | 60 | 0 |  |  |
| combustion_vs_pyjhora(orb indexing differs) | 60 | 42 | 18 |  | A02: ['Mars', 'Mercury', 'Moon', 'Venus'] vs ['Jupiter', 'Mars', 'Mercury', 'Moon', 'Venus']; A10: ['Saturn', 'Venus'] vs ['Mercury', 'Saturn', 'Venus']; A11: ['Jupiter'] vs ['Jupiter', 'Mercury', 'Venus'] |
| gulika_start_night_birth | 34 | 0 | 34 | 1.079e+04 arcmin | A01: 10569.72'; A03: 10609.75'; A05: 10769.40' |
| defaults_true_positions_Sun | 60 | 60 | 0 | 20.84 arcsec |  |
| defaults_true_positions_Moon | 60 | 60 | 0 | 0.7571 arcsec |  |
| defaults_true_positions_Mars | 60 | 60 | 0 | 38.06 arcsec |  |
| defaults_true_positions_Mercury | 60 | 59 | 1 | 60.09 arcsec | A03: 60.1" |
| defaults_true_positions_Jupiter | 60 | 60 | 0 | 29.87 arcsec |  |
| defaults_true_positions_Venus | 60 | 60 | 0 | 44.83 arcsec |  |
| defaults_true_positions_Saturn | 60 | 60 | 0 | 27.25 arcsec |  |
| defaults_true_positions_Rahu | 60 | 60 | 0 | 0.01567 arcsec |  |
| defaults_true_positions_Ketu | 60 | 60 | 0 | 0.01567 arcsec |  |

### NASA/JPL Horizons (independent ephemeris service)

91 tropical apparent longitudes (Sun..Saturn, 13 charts, 1901-2026): max deviation 0.425 arcsec (pass < 1 arcsec).

### prokerala.com published daily panchanga

13 pages compared; unreachable: PK04, PK13. Element names mismatched: 0. Deviations are ours minus theirs, minutes (their times are printed to the minute). drikpanchang page DP01 values below; its other 13 pages were removed after a reCAPTCHA wall.

| quantity | n | min | max |
|---|---:|---:|---:|
| tithi start | 26 | -0.01 | +0.94 |
| tithi end | 26 | -0.01 | +1.07 |
| nakshatra start | 25 | -0.53 | +1.47 |
| nakshatra end | 25 | -0.42 | +1.47 |
| karana start | 40 | -0.01 | +0.94 |
| karana end | 40 | +0.02 | +0.99 |
| yoga start | 26 | -0.85 | +1.78 |
| yoga end | 26 | -0.67 | +1.91 |
| sunrise[apparent_upper_limb] | 13 | -6.58 | -2.43 |
| sunset[apparent_upper_limb] | 13 | +3.79 | +6.39 |
| gulika_kalam_start[apparent_upper_limb] | 13 | -3.93 | +3.08 |
| sunrise[hindu] | 13 | -0.40 | +0.93 |
| sunset[hindu] | 13 | +0.22 | +1.36 |
| gulika_kalam_start[hindu] | 13 | -0.06 | +1.05 |

### drikpanchang.com (1 page; later requests got a reCAPTCHA wall)

| quantity | result |
|---|---|
| tz_offset | +05:30 vs +05:30 |
| ayanamsa_arcsec | -15.95 |
| tithi_end_min | +0.94 |
| nakshatra_end_min | +0.34 |
| yoga_end_min | +0.03 |
| karana_end_min | +0.94 |
| sunrise_min[apparent_upper_limb] | -0.28 |
| sunset_min[apparent_upper_limb] | -0.25 |
| gulika_kalam_start_min[apparent_upper_limb] | -0.27 |
| sunrise_min[hindu] | +3.12 |
| sunset_min[hindu] | -3.66 |
| gulika_kalam_start_min[hindu] | -0.27 |
