"""Compose a full birth chart (ChartRequest -> ChartResponse)."""
from __future__ import annotations

import zoneinfo
from datetime import datetime, timedelta, timezone

import swisseph as swe

from . import __version__
from . import core as C
from . import ephemeris as E
from . import timeutil
from .constants import (DASHA_YEAR_DAYS, DASHA_YEAR_DAYS_DEFAULT, DASHA_YEAR_SAVANA,
                        DASHA_YEAR_SOLAR, GRAHA_ML, GRAHA_SA, GRAHAS,
                        GULIKA_CONVENTION,
                        MANDI_CONVENTION, NAKSHATRAS, NAKSHATRAS_IAST, NAKSHATRAS_ML,
                        NAKSHATRAS_ML_LATIN, RASIS, VARAS, VIMSHOTTARI_ORDER, WEEKDAYS,
                        karana_record, tithi_record, vara_record, yoga_record)
from .geocode import geocode
from .schema import (BirthKarana, BirthNityaYoga, BirthPanchanga, BirthStar, BirthTithi, BirthVara,
                     ChartRequest, ChartResponse, DashaBalance, DashaEndPair, DashaPeriod,
                     DashaYearCompare, Dignity, Graha, Lagna,
                     Meta, Nakshatra, Panchanga, TimeInfo, TransitGraha, Transits, Upagraha,
                     Vimshottari)
from .vargas import VARGAS

COMBUSTION_SOURCE = ("Surya Siddhanta 9.6-9 and 10.1 (Burgess tr., 1860): Moon 12, Mars 17, "
                     "Mercury 14 (12 retrograde), Jupiter 11, Venus 10 (8 retrograde), Saturn 15 degrees; "
                     "applied as ecliptic-longitude separation from the Sun (the text uses kalamsas)")


def jd_to_dt(jd: float) -> datetime:
    y, m, d, h = swe.revjul(jd, swe.GREG_CAL)
    return datetime(y, m, d, tzinfo=timezone.utc) + timedelta(hours=h)


def dms(x: float) -> str:
    total = round(x * 3600)
    d, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{d}°{m:02d}'{s:02d}\""


def nak(lon: float) -> Nakshatra:
    i, p = E.nakshatra_of(lon)
    return Nakshatra(index=i + 1, name=NAKSHATRAS[i], pada=p, lord=VIMSHOTTARI_ORDER[i % 9],
                     name_iast=NAKSHATRAS_IAST[i], name_ml=NAKSHATRAS_ML[i],
                     name_ml_latin=NAKSHATRAS_ML_LATIN[i])


def year_length_convention(days: float, mode: str | None = None) -> str:
    if mode == DASHA_YEAR_SAVANA:
        return (
            "Vimshottari year mode savana_360: the Kerala traditional sāvana year, "
            "12 months × 30 days = 360 days. Daśā and apahāra (bhukti) lengths are the "
            "aṃśa proportion counted in these 360-day years, and the start and end dates "
            "use that length, so a 12×30 year, month and day is a calendar year, month and day. "
            "The default mode is solar_365_25 (365.25 days). A sidereal year of 365.256364 days "
            "is not used."
        )
    which = ("the project default, the mean Julian year" if days == DASHA_YEAR_DAYS_DEFAULT else
             f"a request override; the project default is {DASHA_YEAR_DAYS_DEFAULT:g}, "
             "the mean Julian year")
    return (f"A Vimshottari year is {days:g} days ({which}). It scales mahadasha and bhukti "
            "start and end dates only. Other lengths in use are 365.256364 (sidereal, PyJHora's "
            "own default), 365.2425 (tropical) and 360 (savana). The years/months/days balance "
            "is a 12×30 split of the year-balance and does not use this length.")


def _dasha_periods(v, jd_local) -> list:
    def period(lord, a, b, yrs, bh=None):
        return DashaPeriod(lord=lord, start_utc=jd_to_dt(a), end_utc=jd_to_dt(b),
                           start_local_date=jd_local(a).date(), end_local_date=jd_local(b).date(),
                           years=yrs, bhuktis=bh)

    return [period(md, a, b, yrs, [period(bl, ba, bb, by) for bl, ba, bb, by in bh])
            for md, a, b, yrs, bh in v["mahadashas"]]


def _round_days(days: float) -> float:
    # Six decimals keeps 986.175 and 972 stable. The raw product is a hair off
    # an exact decimal (18×18/120 × 365.25).
    return round(days, 6)


def _selected_year_mode(days: float) -> str:
    if days == DASHA_YEAR_DAYS[DASHA_YEAR_SOLAR]:
        return DASHA_YEAR_SOLAR
    if days == DASHA_YEAR_DAYS[DASHA_YEAR_SAVANA]:
        return DASHA_YEAR_SAVANA
    return "custom"


def _end_pair(solar, savana, jd_local, children) -> DashaEndPair:
    sa, sb = solar[1], solar[2]
    va, vb = savana[1], savana[2]
    return DashaEndPair(
        lord=solar[0],
        end_utc_solar=jd_to_dt(sb),
        end_utc_savana=jd_to_dt(vb),
        end_local_date_solar=jd_local(sb).date(),
        end_local_date_savana=jd_local(vb).date(),
        delta_days=_round_days(vb - sb),
        span_days_solar=_round_days(sb - sa),
        span_days_savana=_round_days(vb - va),
        bhuktis=children,
    )


def dasha_year_compare(solar_v, savana_v, selected: str, jd_local) -> DashaYearCompare:
    """Pair the two named Vimshottari timelines. No ephemeris work."""
    mds = []
    for solar, savana in zip(solar_v["mahadashas"], savana_v["mahadashas"]):
        bh = [_end_pair(a, b, jd_local, None) for a, b in zip(solar[4], savana[4])]
        mds.append(_end_pair(solar, savana, jd_local, bh))
    return DashaYearCompare(selected=selected, mahadashas=mds)


def pos_fields(lon: float) -> dict:
    s = int(lon // 30) % 12
    return dict(longitude=round(lon, 6), longitude_dms=dms(lon), sign_index=s + 1, sign=RASIS[s],
                degree_in_sign=round(lon - (lon // 30) * 30, 6), nakshatra=nak(lon))


def vargas_of(lon: float) -> dict[str, str]:
    return {k: RASIS[f(lon)] for k, f in VARGAS.items()}


def compute_chart(req: ChartRequest, now: datetime | None = None) -> ChartResponse:
    st = req.settings
    warnings: list[str] = []
    place = req.place
    if place.lat is None:
        g = geocode(place.name)
        lat, lon = g["lat"], g["lon"]
        place_out = dict(name=place.name, lat=lat, lon=lon, geocoded=True,
                         geocoder_display_name=g["display_name"])
        warnings.append(f"place geocoded to {g['display_name']} ({lat:.4f}, {lon:.4f}); please confirm")
    else:
        lat, lon = place.lat, place.lon
        place_out = dict(name=place.name, lat=lat, lon=lon, geocoded=False)

    rt = timeutil.resolve(req.date, req.time, req.tz, lat, lon, req.utc_offset_override_hours,
                          req.use_lmt, req.fold)
    warnings += rt.warnings
    zone = zoneinfo.ZoneInfo(rt.tz_name) if rt.offset_source.startswith("iana:") else None
    fixed = timezone(timedelta(seconds=rt.utc_offset_seconds))

    def to_local(dt_utc: datetime) -> datetime:
        return dt_utc.astimezone(zone) if zone else dt_utc.astimezone(fixed)

    def jd_local(jd):
        return to_local(jd_to_dt(jd))

    jd = E.julday_utc(rt.utc)
    jd_midnight = swe.julday(req.date.year, req.date.month, req.date.day, 0.0) - rt.utc_offset_seconds / 86400

    with E.LOCK:
        E.set_ayanamsa(st.ayanamsa)
        ayan = E.ayanamsa_value(jd)
        bodies = C.graha_longitudes(jd, st.node, st.position_type)
        asc = E.ascendant(jd, lat, lon)
        civil_wd = (req.date.weekday() + 1) % 7
        try:
            dn = C.day_night(jd, jd_midnight, civil_wd, lat, lon, st.sunrise_convention)
        except ValueError as e:  # polar day/night: no sunrise-based quantities
            dn = None
            warnings.append(str(e) + "; Gulika/Mandi omitted and the civil weekday is used")
        if dn:
            if st.gulika_point == "prasna_marga_mandi":
                t_gul = C.mandi_time(dn, "prasna_marga_ghatika")
            else:
                t_gul = C.gulika_time(dn, st.gulika_point)
            t_man = C.mandi_time(dn, st.mandi_method)
            asc_gul = E.ascendant(t_gul, lat, lon)
            asc_man = E.ascendant(t_man, lat, lon)
        pan = C.panchanga_elements(jd, st.position_type)
        tr_at = req.transit_at or now or datetime.now(timezone.utc)
        if tr_at.tzinfo is None:
            raise ValueError("transit_at must include a UTC offset")
        jd_tr = E.julday_utc(tr_at.astimezone(timezone.utc))
        tr_bodies = C.graha_longitudes(jd_tr, st.node, st.position_type)

    ephem = "swiss" if all(b.ephemeris == "swiss" for b in bodies.values()) else "moshier"
    if ephem != "swiss":
        warnings.append("Swiss Ephemeris data files did not cover this date; Moshier fallback used")

    lagna_sign = int(asc // 30)

    def house(lon_):
        return (int(lon_ // 30) - lagna_sign) % 12 + 1

    sun = bodies["Sun"].longitude
    grahas = []
    for g in GRAHAS:
        b = bodies[g]
        retro = C.is_retrograde(g, b.speed, st.node)
        comb, orb = C.combustion(g, b.longitude, sun, retro, st.moon_combustion)
        h = house(b.longitude)
        grahas.append(Graha(name=g, **pos_fields(b.longitude), speed_deg_per_day=round(b.speed, 6),
                            retrograde=retro, combust=comb, combustion_orb_deg=orb, house=h,
                            dignity=Dignity(**C.dignity(g, int(b.longitude // 30) % 12, h)),
                            vargas=vargas_of(b.longitude)))

    part_of = "day" if dn and dn.is_day else "night"
    if st.gulika_point == "prasna_marga_mandi":
        method_g = ("Prasna Marga ch. 5 st. 14-16 Mandi ghatika table, scaled to the real "
                    f"{st.sunrise_convention} sunrise and sunset at the birthplace "
                    "(day 26,22,18,14,10,6,2 / night 10,6,2,26,22,18,14 ghatikas, Sunday..Saturday)")
    else:
        method_g = (f"lagna rising at the {st.gulika_point} of Saturn's 1/8 part of the {part_of} "
                    f"(real {st.sunrise_convention} sunrise and sunset at the birthplace; "
                    "weekday-lord segments, night counted from the 5th lord)")
    if st.mandi_method == "prasna_marga_ghatika":
        method_m = ("Prasna Marga ghatika table (day 26,22,18,14,10,6,2 / night 10,6,2,26,22,18,14 "
                    "ghatikas from sunrise/sunset, Sunday..Saturday, scaled to actual day/night length)")
    else:
        method_m = f"lagna rising at the {st.mandi_method.replace('saturn_segment_', '')} of Saturn's part"
    upas = []
    rows = ((("Gulika", t_gul, asc_gul, method_g, GULIKA_CONVENTION[st.gulika_point]),
             ("Mandi", t_man, asc_man, method_m, MANDI_CONVENTION[st.mandi_method])) if dn else ())
    for name, t, a, m, conv in rows:
        label = dict(alias="Mandi", name_ml="മാന്ദി") if name == "Gulika" else {}
        upas.append(Upagraha(name=name, **label, **pos_fields(a), house=house(a),
                             rising_time_utc=jd_to_dt(t), rising_time_local=jd_local(t),
                             method=m, convention=conv))

    houses = []
    for i in range(12):
        s = (lagna_sign + i) % 12
        placed = [u for u in upas if u.sign_index == s + 1]
        houses.append(dict(
            house=i + 1, sign=RASIS[s], sign_index=s + 1,
            grahas=[g.name for g in grahas if g.sign_index == s + 1],
            # Gulika (and Mandi) on the rasi, with the sign and longitude. `grahas` stays the nine.
            upagrahas=[dict(name=u.name, alias=u.alias, name_ml=u.name_ml, longitude=u.longitude,
                            sign=u.sign, sign_index=u.sign_index, degree_in_sign=u.degree_in_sign)
                       for u in placed]))

    def el(d, extra=None):
        out = {k: v for k, v in d.items() if not k.endswith("_jd")}
        out["starts_local"] = jd_local(d["start_jd"]).isoformat()
        out["ends_local"] = jd_local(d["end_jd"]).isoformat()
        return out

    pk = pan["nakshatra"]
    pan_n = el(pk)
    ni = pk["index"] - 1
    pan_n.update(name=NAKSHATRAS[ni], name_iast=NAKSHATRAS_IAST[ni], name_ml=NAKSHATRAS_ML[ni],
                 name_ml_latin=NAKSHATRAS_ML_LATIN[ni], lord=VIMSHOTTARI_ORDER[ni % 9])
    vara_note = None
    vwd = dn.vedic_weekday if dn else civil_wd
    if dn is None:
        vara_note = "no sunrise/sunset at this place and date: civil weekday shown"
    elif not dn.is_day and dn.vedic_weekday != civil_wd:
        vara_note = "birth before sunrise: the Vedic day is the previous civil day"
    th = tithi_record(pan["tithi"]["number"])
    yg = yoga_record(pan["yoga"]["number"])
    kr = karana_record(pan["karana"]["number"])
    vr = vara_record(vwd)
    tithi_out = el(pan["tithi"])
    tithi_out.update(name_iast=th["name_iast"], name_en=th["name_en"], name_ml=th["name_ml"],
                     paksha_iast=th["paksha_iast"], paksha_en=th["paksha_en"], paksha_ml=th["paksha_ml"])
    yoga_out = el(pan["yoga"])
    yoga_out.update(name_iast=yg["name_iast"], name_en=yg["name_en"], name_ml=yg["name_ml"])
    karana_out = el(pan["karana"])
    karana_out.update(name_iast=kr["name_iast"], name_en=kr["name_en"], name_ml=kr["name_ml"])
    panchanga = Panchanga(
        tithi=tithi_out, nakshatra=pan_n, yoga=yoga_out, karana=karana_out,
        vara=dict(index=vwd, name=VARAS[vwd], weekday=WEEKDAYS[vwd], civil_weekday=WEEKDAYS[civil_wd],
                  note=vara_note, name_iast=vr["name_iast"], name_en=vr["name_en"], name_ml=vr["name_ml"]),
        sunrise_local=jd_local(dn.sunrise) if dn else None, sunset_local=jd_local(dn.sunset) if dn else None,
        is_day_birth=dn.is_day if dn else None, sunrise_convention=st.sunrise_convention)

    moon = next(g for g in grahas if g.name == "Moon")
    birth_star = BirthStar(index=moon.nakshatra.index, name_iast=moon.nakshatra.name_iast,
                           name_en=moon.nakshatra.name, name_ml=moon.nakshatra.name_ml,
                           name_ml_latin=moon.nakshatra.name_ml_latin, pada=moon.nakshatra.pada)
    birth_panchanga = BirthPanchanga(
        vara=BirthVara(**vr), nakshatra=birth_star, tithi=BirthTithi(**th),
        nitya_yoga=BirthNityaYoga(**yg), karana=BirthKarana(**kr))

    # The second timeline is arithmetic on the Moon longitude already in hand.
    # It runs only when asked, and the default response omits year_compare.
    moon_lon = bodies["Moon"].longitude
    year_compare = None
    if st.compare_dasha_years:
        solar_v = C.vimshottari(moon_lon, jd, DASHA_YEAR_DAYS[DASHA_YEAR_SOLAR])
        savana_v = C.vimshottari(moon_lon, jd, DASHA_YEAR_DAYS[DASHA_YEAR_SAVANA])
        selected = _selected_year_mode(st.dasha_year_days)
        if selected == DASHA_YEAR_SOLAR:
            v = solar_v
        elif selected == DASHA_YEAR_SAVANA:
            v = savana_v
        else:
            v = C.vimshottari(moon_lon, jd, st.dasha_year_days)
        year_compare = dasha_year_compare(solar_v, savana_v, selected, jd_local)
    else:
        v = C.vimshottari(moon_lon, jd, st.dasha_year_days)
    mds = _dasha_periods(v, jd_local)
    by, bm, bd = C.years_to_ymd_parts(v["balance"])
    vim = Vimshottari(year_days=st.dasha_year_days, birth_nakshatra_lord=v["lord"],
                      balance_at_birth_years=round(v["balance"], 6),
                      balance_at_birth_ymd=C.years_to_ymd(v["balance"]),
                      elapsed_fraction=round(v["frac"], 6), mahadashas=mds,
                      balance_at_birth=DashaBalance(
                          lord=v["lord"], lord_en=GRAHA_SA[v["lord"]], lord_ml=GRAHA_ML[v["lord"]],
                          years=by, months=bm, days=bd),
                      year_length_convention=year_length_convention(st.dasha_year_days, st.dasha_year),
                      ymd_convention=C.YMD_RULE, year_compare=year_compare)

    moon_sign = int(bodies["Moon"].longitude // 30)
    trs = []
    for g in GRAHAS:
        b = tr_bodies[g]
        s = int(b.longitude // 30) % 12
        trs.append(TransitGraha(name=g, longitude=round(b.longitude, 6), sign=RASIS[s], sign_index=s + 1,
                                degree_in_sign=round(b.longitude - s * 30, 6), nakshatra=nak(b.longitude),
                                retrograde=C.is_retrograde(g, b.speed, st.node),
                                house_from_lagna=(s - lagna_sign) % 12 + 1,
                                house_from_moon=(s - moon_sign) % 12 + 1))

    return ChartResponse(
        meta=Meta(engine_version=__version__, settings=st, ayanamsa_deg=round(ayan, 6), ephemeris=ephem,
                  swisseph_version=swe.version, combustion_orbs_source=COMBUSTION_SOURCE, warnings=warnings),
        time=TimeInfo(local_input=rt.local, utc=rt.utc, utc_offset=timeutil.fmt_offset(rt.utc_offset_seconds),
                      utc_offset_hours=rt.utc_offset_seconds / 3600, tz_name=rt.tz_name, tz_abbrev=rt.tz_abbrev,
                      offset_source=rt.offset_source, tzdata_version=timeutil.TZDATA_VERSION,
                      timezone_unverified=rt.timezone_unverified, julian_day_ut=jd),
        place=place_out,
        lagna=Lagna(**pos_fields(asc), vargas=vargas_of(asc)),
        grahas=grahas, upagrahas=upas, houses=houses, panchanga=panchanga,
        birth_star=birth_star, birth_panchanga=birth_panchanga, vimshottari=vim,
        transits=Transits(at_utc=tr_at.astimezone(timezone.utc), grahas=trs))
