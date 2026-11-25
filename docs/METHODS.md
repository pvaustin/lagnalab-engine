# Methods, conventions and sources

Everything here is configurable unless marked fixed. "Unverified" means not yet checked against
a primary text or by the Kerala astrologer.

## Time and place
- Local civil time -> UTC with the IANA tz database via `zoneinfo`, pinned to the `tzdata` package
  (version reported as `time.tzdata_version`). The offset used is always returned for the user to confirm.
- DST gaps and repeated times produce warnings; `fold` selects the reading.
- **Pre-1955 Indian subcontinent** (zone in Asia/Kolkata, Karachi, Dhaka, Colombo, ... or coordinates
  inside 5-37.5N, 60-98E): `timezone_unverified = true` plus a warning listing the clocks that were
  in use. tzdata's Asia/Kolkata uses railway time: LMT to 1854, +5:53:20 to 1870, Madras time
  +5:21:10 to 1906, IST after, and +6:30 war time 1941-10..1942-05-15 and 1942-09..1945-10-15; its own
  comments call the war-time source "dubious" and note Calcutta government time of +5:53:20 or +5:54
  (docs/sources/tzdb_asia_india_excerpt.txt). Bombay Time (~+4:51, to ~1955) is from general knowledge,
  unverified. Users can resubmit with `utc_offset_override_hours` or `use_lmt`.
- Place names are geocoded with Nominatim (cached). The geocoded name and coordinates are echoed back
  with a "please confirm" warning.

## Ephemeris and basis
- Swiss Ephemeris 2.10.03 (pyswisseph), data files 1800-2400; geocentric; **apparent** positions by
  default (light-time, aberration, deflection, nutation; Swiss default). `position_type=true_geometric`
  adds FLG_TRUEPOS, PyJHora's default. The difference reached 60" (Mercury) on our golden set.
- Sidereal via `swe.set_sid_mode`: lahiri = SIDM_LAHIRI (default), raman = SIDM_RAMAN,
  kp = SIDM_KRISHNAMURTI, true_chitra = SIDM_TRUE_CITRA. The ayanamsa at birth is returned.
- Lagna: sidereal ascendant from `swe.houses_ex` (whole-sign houses from the lagna sign).
- Rahu: mean node by default (`node=true` for the true node); Ketu = Rahu + 180.
- Retrograde = negative longitudinal speed; mean nodes are always retrograde; Sun/Moon never.
- Nakshatra = floor(L / 13°20'); pada = quarter of 3°20'. Every position carries the English
  name (`name`), IAST (`name_iast`), Kerala Malayalam (`name_ml`) and the Latin Kerala spelling
  (`name_ml_latin`). Jyeshtha = Jyeṣṭhā = തൃക്കേട്ട / Thriketta. The Moon's star is also the
  top-level `birth_star`: index, IAST, English, Malayalam, Latin Kerala name, and pada.

## Sunrise
- Default `hindu`: centre of the disc on the horizon, no refraction (`swe.BIT_HINDU_RISING`).
  Matches PyJHora and prokerala.com (within the minute they print).
- `apparent_upper_limb`: upper limb with standard refraction. Matches drikpanchang.com's printed
  sunrise. The two differ by about 3-6 minutes (more at high latitude).
- Which one Kerala practice uses for Gulika/Mandi and the Vedic day is an **open question**.

## Panchanga at birth
Returned as `panchanga` (with start and end times) and as `birth_panchanga` (the five limbs at
the birth instant, each with IAST, English and Kerala Malayalam names).
- Tithi = floor((Moon − Sun) / 12°) + 1 (1–30). 1–15 are śukla, 16–30 kṛṣṇa. 15 = Pūrṇimā,
  30 = Amāvāsyā. `birth_panchanga.tithi.paksha` is `shukla` or `krishna`. The older
  `panchanga.tithi.paksha` stays `Shukla` / `Krishna`.
- Nakshatra is the Moon's birth star. `birth_panchanga.nakshatra` is the same object as
  `birth_star` (index, IAST, English, Kerala Malayalam, Latin Kerala name, pada). It is not
  computed a second time.
- Nitya yoga = floor((Moon + Sun) / 13°20') + 1, numbered 1–27 from Viṣkambha.
- Karana is the half-tithi, number 1–60 = floor(elongation / 6°) + 1, mapped onto 11 names:
  1 Kiṃstughna, 2–57 the seven movable karanas in turn (Bava … Viṣṭi), 58 Śakuni,
  59 Catuṣpāda, 60 Nāga.
- Vara: the Hindu day runs from local sunrise to the next local sunrise (`sunrise_convention`,
  default disc centre). A birth before that morning's sunrise belongs to the previous weekday.
  Index 0 = Sunday. Polar day or night: the civil weekday, with a warning.
- Each element's start and end time (Newton iteration on the angle) is on `panchanga`.

## Vargas (Parashara), signs only
Formulas are in the `lagnalab_engine/vargas.py` docstring: D2 Sun/Moon horas (odd sign: Simha then
Karka; even: Karka then Simha), D3 (1st/5th/9th), D7 (odd from itself, even from the 7th),
D9 (movable from itself, fixed from 9th, dual from 5th), D10 (odd from itself, even from 9th),
D12 (from itself), D30 (unequal Mars/Saturn/Jupiter/Mercury/Venus parts, reversed for even signs).
Parts are half-open [start, end). These match PyJHora's "traditional Parasara" methods (D2 method 2,
others method 1) on all 4,200 golden varga placements. Other variants (parivritti, Somanatha, Kerala
practices) are not implemented; the varga set is still to be confirmed with the astrologer.

## Dignity (basic)
- Exaltation signs (deep degree): Sun Mesha 10, Moon Vrishabha 3, Mars Makara 28, Mercury Kanya 15,
  Jupiter Karka 5, Venus Meena 27, Saturn Tula 20; debilitation the opposite sign. Flags are by sign.
- `sign_relation`: naisargika relation of the graha to the sign lord (own/friend/neutral/enemy), with
  the standard Parashara table in `constants.NAISARGIKA`. Both `exalted` and `sign_relation` are given
  (e.g. Mercury in Kanya is exalted and own). No relation for Rahu/Ketu. Moolatrikona is not
  implemented. Source of the tables: standard BPHS values from general knowledge; **not yet checked
  against a text in our corpus** (BJ ch. 1-2 would be the citable source).
- Dig bala flag: Jupiter/Mercury in house 1, Moon/Venus in 4, Saturn in 7, Sun/Mars in 10 (whole-sign
  houses; classical dig bala is graded from bhava cusps - open question).

## Combustion
Orbs (degrees of longitude from the Sun): Moon 12, Mars 17, Mercury 14 (12 when retrograde),
Jupiter 11, Venus 10 (8 when retrograde), Saturn 15. Source: Surya Siddhanta 9.6-9 and 10.1
(Burgess tr. 1860, public domain; checked on siva.sh/surya-siddhanta). The text gives kalamsas
(time-degrees), not ecliptic degrees; using them as longitude orbs is the usual modern
simplification. Moon combustion can be switched off (`moon_combustion`).

## Gulika and Mandi (Kerala method)
Day = sunrise to sunset, night = sunset to next sunrise, each split into 8 equal parts.
Day parts are ruled by the seven weekday lords in weekday order starting from the lord of the day;
night parts start from the lord of the 5th weekday counted from the day (Sunday night starts with
Jupiter). The 8th part has no lord. A pre-sunrise birth belongs to the previous day's night.
- **Gulika** (project decision) is the lagna at the Prasna Marga Mandi ghatika, the same
  point the engine already computes for Mandi. `gulika_point`:
  - `prasna_marga_mandi` (default): day ghatikas 26, 22, 18, 14, 10, 6, 2 and night ghatikas
    10, 6, 2, 26, 22, 18, 14 (Sunday..Saturday), scaled to the real sunrise-to-sunset day or
    sunset-to-next-sunrise night (30 ghatikas = the whole day or night). Source: Prasna Marga
    ch. 5 st. 14-16. The upagraha is named Gulika, with `alias` Mandi and `name_ml` മാന്ദി.
    `upagrahas[].convention` cites Prasna Marga.
  - `start`: beginning of Saturn's eighth-part. vedicastro.com, and the BPHS *gulikārambhakāle*
    reading. Night parts start from the 5th lord from the weekday lord. The PyJHora golden
    check compares this instant (`gulika_point=start`); it is not the default.
  - `end`: end of Saturn's part. Uttara Kalamrita, astrojyoti.com uttarakalamritam1-2 sloka 8.
  - `middle`: midpoint of Saturn's part.
  Day and night lengths are the real sunrise and sunset at the birthplace
  (`sunrise_convention`; default is disc-centre, no refraction). Gulika is an upagraha, not one
  of the nine `grahas`. It is listed on the rasi house it occupies (`houses[].upagrahas`) with
  its sign and longitude. `houses[].grahas` stays the nine grahas.
- **Mandi** (default `prasna_marga_ghatika`) is that same ghatika table, kept as its own upagraha:
  26, 22, 18, 14, 10, 6, 2 ghatikas after sunrise (day, Sunday..Saturday) or 10, 6, 2, 26, 22, 18,
  14 ghatikas after sunset (night). With both defaults, Gulika and Mandi are the same longitude.
- Source: Prasna Marga ch. 5 st. 14-16 as explained in B.V. Raman's notes (cited, not reproduced here), and the same ghatika table under
  "Gulikodaya kala" in his notes to ch. 2 st. 16-20.
- **Still open:**
  1. Raman's notes on the eighth-part put Gulika at the **end** of Saturn's part (his Friday
     example gives 7.5 ghatikas, the end of the 2nd part). That remains selectable as `end`.
     PyJHora uses the start for "gulika" and the middle for "maandi".
  2. Phaladeepika's rule was not checked: no Phaladeepika text is in our corpus yet.
  3. Which sunrise (Hindu vs apparent) the tradition uses shifts Gulika by up to ~1-2 degrees.
  4. The chart still returns a separate Mandi upagraha beside Gulika. Dropping it is not decided.

## Vimshottari
Lord sequence Ketu, Venus, Sun, Moon, Mars, Rahu, Jupiter, Saturn, Mercury (7, 20, 6, 10, 7, 18, 16,
19, 17 years) starting from Ashwini. Balance at birth = (1 - fraction of the Moon's nakshatra
traversed) x years of its lord. Bhukti = MD years x AD years / 120, starting with the MD lord.
**Year length = 365.25 days** by default. `settings.dasha_year` chooses a named mode:
`solar_365_25` (default, mean Julian year; the length ClickAstro, Astro-Vision and Kerala
Jyotisham use) or `savana_360` (Kerala traditional sāvana year, 12 months × 30 days, aṃśa
proportion). The named mode wins over `dasha_year_days`. Omitting `dasha_year` leaves
`dasha_year_days` in force, still 365.25 unless that float is set. A sidereal year of
365.256364 days is not a mode. The length scales mahadasha and bhukti start and end dates.
365.25 is the length the golden set compares. A default response (no `dasha_year`, or
`solar_365_25`) does not add a `dasha_year` key, so that JSON stays as it was.
`savana_360` is echoed on `meta.settings.dasha_year` and in `year_length_convention`.
`settings.compare_dasha_years` defaults to false and is omitted from the response when false.
Set it true to add `vimshottari.year_compare` in that same response: each mahadasha and
bhukti end under both `solar_365_25` and `savana_360`. `delta_days` is the sāvana end
minus the saura end, in days. `span_days_solar` and `span_days_savana` are that period's
own length (a full Śukra mahādaśā is 7,305 and 7,200 days). The dates already on
`vimshottari.mahadashas` stay the selected length. A client that does not send the flag
still gets the previous JSON. The extra timeline is the same arithmetic on the Moon
longitude already computed; it does not call the ephemeris again.
The lord is the engine key (`birth_nakshatra_lord`, e.g. Mercury) and, on `balance_at_birth`, the
Sanskrit name in Latin script plus Malayalam (Budha / ബുധൻ; Surya, Chandra, Kuja, Guru, Shukra,
Shani, Rahu, Ketu for the others).
**Years, months, days** (`balance_at_birth.years/months/days`) split that year-balance as 12 months
of 30 days. Leftover days are truncated toward zero, not rounded. A balance of 16.588 years
therefore prints as 16 years, 7 months, 1 day, which is the figure Kerala software shows. Rounding
the day would print 2. This split does not use `dasha_year_days`. Under `savana_360` the
same 12×30 units are calendar days, because the year is 360 days; under `solar_365_25` they
are the printed balance and the calendar span is the year-balance times 365.25. The older string
`balance_at_birth_ymd` keeps one decimal day (`16y 7m 1.7d`) so the truncated fraction stays visible.
Same-lord apahāra at 360 days: Rahu–Rahu 2y 8m 12d (972 d), Saturn–Saturn 3y 0m 3d (1083 d),
Venus–Venus 3y 4m 0d (1200 d), Sun–Sun 3m 18d (108 d), Moon–Moon 10m (300 d).

## Transits (gochara)
Sidereal positions at `transit_at`, with house from the natal lagna and from the natal Moon sign.

## Disagreements with PyJHora 4.8.7 (the golden reference)
Gated fields agree on all 60 charts once PyJHora is set to our conventions (see GOLDEN_REPORT.md).
What had to be configured, and what still differs:
1. **Defaults differ**: PyJHora defaults to TRUE_PUSHYA ayanamsa, true nodes, true-geometric
   positions (FLG_TRUEPOS) and a 365.256364-day dasha year. We default to Lahiri, mean node,
   apparent positions, 365.25 days. Mean vs true node differed by up to 1.64 deg on the golden set; true vs apparent
   positions by up to 60" (Mercury), i.e. at the 1' tolerance edge.
   *Recommendation*: keep apparent positions (they match JPL Horizons to < 0.5" and are what almanacs
   print). Mean vs true node and the dasha year length are tradition choices for the astrologer.
2. **Night-time Gulika/Maandi bug in PyJHora**: for births after sunset or before sunrise,
   `drik.upagraha_longitude` divides the *day* length (not the night) into 8 and counts from a
   sunrise, so night Gulika lands at a daytime moment. All 34 night births disagree (by up to ~180 deg);
   all 26 day births agree within 0.16'. Our night rule follows Raman's notes (night parts from sunset,
   lords from the 5th weekday lord).
3. **Combustion**: PyJHora's `planets_in_combustion` reads its orb list with an off-by-one index (Mars
   gets 12, Mercury 17, Jupiter 14, Saturn 11 ...) and does not wrap at 0/360 deg. 18 of 60 charts
   differ. We use the Surya Siddhanta orbs above.
4. **Naisargika/sign-strength table**: PyJHora's `house_strengths_of_planets` marks Sun in Karka as
   neutral, Jupiter in Kanya as friend, and Venus in Dhanu as friend; the standard Parashara table
   (and PyJHora's own `compound_planet_relations`) gives friend, enemy and neutral. We keep the standard table.
5. PyJHora names: its `gulika_longitude` uses the start of Saturn's part and `maandi_longitude` the
   middle (its own comment says the opposite). Our Gulika default, and our Mandi default, are the
   Prasna Marga ghatika table. The golden check of PyJHora's begin-of-part longitude requests
   `gulika_point=start`.

## Other independent checks
- NASA/JPL Horizons: tropical apparent longitudes of Sun..Saturn for 13 charts (1901-2026) agree
  to < 0.5".
- prokerala.com: 13 daily pages (Kerala, Kolkata 1943 war time, Kochi 1901/1944, Sydney, Johannesburg,
  London, Chicago, Buenos Aires): every tithi/nakshatra/karana/yoga name matches; tithi and karana
  times fall 0-1 min after theirs (they truncate to the minute); nakshatra/yoga within -0.9..+1.9 min;
  their sunrise matches our `hindu` convention. Two pages (Chennai geoname) returned 404.
- drikpanchang.com: one page (Kochi, 2026-10-20) fetched before a reCAPTCHA wall; all four
  end-times within 1 min, sunrise matches our `apparent_upper_limb` convention. Its printed
  "Lahiri Ayanamsha" (24.238202 deg) is 16" larger than Swiss SIDM_LAHIRI; no Swiss variant
  (LAHIRI_1940, VP285, ICRC) reproduces it exactly. Effect: ~0.5 min on Moon-based end times.

## Open questions for the Kerala astrologer
1. Gulika's instant is decided (project decision): the default is `prasna_marga_mandi`, the Prasna Marga
   ghatika table, labelled Gulika with alias Mandi. `start`, `middle` and `end` stay selectable.
   Whether the separate Mandi upagraha should be dropped is still open.
2. Sunrise for the Vedic day and Gulika: disc centre without refraction, or visible upper limb?
3. Mean or true Rahu/Ketu.
4. Ayanamsa: Lahiri (which Lahiri - Swiss SIDM_LAHIRI vs the value drikpanchang prints), or another.
5. Dasha year: decided (project decision). Default stays 365.25 (`solar_365_25`). `savana_360`
   (12×30) is selectable. Sidereal 365.256364 is not offered. Chidra (the third level)
   uses the same aṃśa formula and is not in the chart response.
6. Varga set and methods (D2 Parashara vs Kerala usage; D30 for both sexes?), and whether a bhava
   (Sripati) chart is needed (plan §8.8).
7. Combustion orbs: Surya Siddhanta kalamsas as longitude orbs? Moon included?
8. Dig bala by whole-sign house or graded by bhava cusp; moolatrikona wanted?
9. Rahu/Ketu dignity (exaltation/own sign) - which tradition, if any.

## Unverified
- Dignity and friendship tables: standard values, not yet checked against BJ/BPHS text in our corpus.
- Bombay Time (~+4:51) and the dates city times ended; the 1941-45 war-time dates rest on tzdata's
  admittedly weak source. No independent historical-time source was checked beyond the tzdata comments.
- Phaladeepika's Gulika/Mandi rule (text not in corpus).
- Chapter/stanza numbers for Prasna Marga are from Raman's English edition OCR; not checked against
  the 1926 Sanskrit edition.
- Swiss Ephemeris data files cover 1800-2400 only; earlier dates use Moshier (flagged in warnings).
