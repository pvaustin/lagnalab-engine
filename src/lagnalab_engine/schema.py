"""Pydantic request/response schema for the chart engine (JSON contract)."""
from __future__ import annotations

from datetime import date as Date, datetime, time as Time
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_serializer, model_validator

from .constants import (DASHA_YEAR_DAYS, DASHA_YEAR_DAYS_DEFAULT, DASHA_YEAR_SAVANA,
                        DASHA_YEAR_SOLAR)

Ayanamsa = Literal["lahiri", "raman", "kp", "true_chitra"]


class Settings(BaseModel):
    ayanamsa: Ayanamsa = "lahiri"
    node: Literal["mean", "true"] = "mean"
    position_type: Literal["apparent", "true_geometric"] = Field(
        "apparent", description="apparent = Swiss Ephemeris default (light-time, aberration, "
        "deflection, nutation); true_geometric = FLG_TRUEPOS (PyJHora's default)")
    sunrise_convention: Literal["hindu", "apparent_upper_limb"] = Field(
        "hindu", description="hindu = disc centre, no refraction; apparent_upper_limb = civil sunrise")
    gulika_point: Literal["prasna_marga_mandi", "start", "middle", "end"] = Field(
        "prasna_marga_mandi",
        description="How Gulika is placed. prasna_marga_mandi (default): Prasna Marga ch. 5 "
        "st. 14-16 Mandi ghatika table; the lagna at that ghatika, labelled Gulika with alias Mandi. "
        "start: vedicastro.com, ascendant at the beginning of Saturn's eighth-part. "
        "end: Uttara Kalamrita (astrojyoti.com uttarakalamritam1-2, sloka 8), the end of that part. "
        "middle: the midpoint. Day is sunrise to sunset and night is sunset to the next sunrise "
        "at the birthplace (sunrise_convention). For start/middle/end, night parts start from the "
        "5th lord counted from the weekday lord.")
    mandi_method: Literal["prasna_marga_ghatika", "saturn_segment_start",
                          "saturn_segment_middle", "saturn_segment_end"] = "prasna_marga_ghatika"
    dasha_year_days: float = Field(
        DASHA_YEAR_DAYS_DEFAULT, gt=300, lt=400,
        description="Calendar length of one Vimshottari year, in days. Default 365.25 "
        "(mean Julian year). Scales mahadasha and bhukti dates only; the years/months/days "
        "balance is a 12×30 split of the year-balance and does not use this length. "
        "Ignored when dasha_year is set.")
    dasha_year: Optional[Literal["solar_365_25", "savana_360"]] = Field(
        None,
        description="Named Vimshottari year. solar_365_25 (default) is 365.25 days, "
        "the length used by ClickAstro, Astro-Vision and Kerala Jyotisham. "
        "savana_360 is the Kerala traditional sāvana year: 12 months × 30 days, "
        "with aṃśa-proportional daśā and apahāra lengths. When set, this chooses "
        "the length and wins over dasha_year_days. Sidereal 365.256364 is not a mode. "
        "Omitted from the response unless the value is savana_360, so a default "
        "chart matches the previous JSON.")
    compare_dasha_years: bool = Field(
        False,
        description="When true, the same response adds vimshottari.year_compare: "
        "each mahadasha and bhukti end under both solar_365_25 and savana_360. "
        "vimshottari.mahadashas stay on the selected length. Omitted from the "
        "response when false, so a default chart matches the previous JSON.")
    moon_combustion: bool = Field(True, description="apply the 12° orb to the Moon")

    @model_validator(mode="after")
    def _apply_dasha_year(self):
        if self.dasha_year is not None:
            self.dasha_year_days = DASHA_YEAR_DAYS[self.dasha_year]
        return self

    @model_serializer(mode="wrap")
    def _echo_dasha_year(self, handler):
        data = handler(self)
        # Keep a default chart byte-identical. The 365.25 mode is already visible
        # as dasha_year_days and vimshottari.year_days. Name the mode only when
        # the caller selected the 360-day year.
        if data.get("dasha_year") != DASHA_YEAR_SAVANA:
            data.pop("dasha_year", None)
        # Same rule as dasha_year: a default chart must not grow a new key.
        if data.get("compare_dasha_years") is not True:
            data.pop("compare_dasha_years", None)
        return data


class Place(BaseModel):
    name: Optional[str] = Field(None, description="geocoded if lat/lon are not given")
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lon: Optional[float] = Field(None, ge=-180, le=180)


class ChartRequest(BaseModel):
    date: Date
    time: Time = Field(..., description="local civil time as recorded")
    place: Place
    tz: Optional[str] = Field(None, description="IANA zone, e.g. Asia/Kolkata; inferred from lat/lon if omitted")
    utc_offset_override_hours: Optional[float] = Field(None, ge=-14, le=14)
    use_lmt: bool = Field(False, description="treat the time as local mean time of the birthplace")
    fold: Literal[0, 1] = Field(0, description="which reading of an ambiguous (repeated) local time")
    transit_at: Optional[datetime] = Field(None, description="gochara moment (aware); default now (UTC)")
    settings: Settings = Settings()

    @model_validator(mode="after")
    def _place(self):
        if (self.place.lat is None) != (self.place.lon is None):
            raise ValueError("give both lat and lon, or neither")
        if self.place.lat is None and not self.place.name:
            raise ValueError("place needs a name or lat/lon")
        return self


class Nakshatra(BaseModel):
    index: int = Field(..., description="1..27, 1 = Ashwini")
    name: str = Field(..., description="English name, e.g. Jyeshtha")
    pada: int
    lord: str
    name_iast: str = Field(..., description="IAST, e.g. Jyeṣṭhā")
    name_ml: str = Field(..., description="Kerala Malayalam name, e.g. തൃക്കേട്ട")
    name_ml_latin: str = Field(..., description="Kerala name in Latin script, e.g. Thriketta")


class BirthStar(BaseModel):
    """The Moon's nakshatra at birth."""
    index: int = Field(..., description="1..27, 1 = Ashwini")
    name_iast: str
    name_en: str
    name_ml: str
    name_ml_latin: str
    pada: int = Field(..., ge=1, le=4)


class DashaBalance(BaseModel):
    """Vimshottari balance at birth, as a lord and truncated years/months/days."""
    lord: str = Field(..., description="engine graha key, e.g. Mercury; same as birth_nakshatra_lord")
    lord_en: str = Field(..., description="Sanskrit name in Latin script, e.g. Budha")
    lord_ml: str = Field(..., description="Malayalam name, e.g. ബുധൻ")
    years: int
    months: int
    days: int


class Position(BaseModel):
    longitude: float = Field(..., description="sidereal degrees 0..360")
    longitude_dms: str
    sign_index: int = Field(..., description="1..12, 1 = Mesha")
    sign: str
    degree_in_sign: float
    nakshatra: Nakshatra


class Dignity(BaseModel):
    exalted: bool
    debilitated: bool
    sign_relation: Optional[Literal["own", "friend", "neutral", "enemy"]] = Field(
        None, description="naisargika relation of the graha to the sign lord; null for Rahu/Ketu")
    dig_bala: bool


class Graha(Position):
    name: str
    speed_deg_per_day: float
    retrograde: bool
    combust: Optional[bool] = Field(None, description="null for Sun, Rahu, Ketu")
    combustion_orb_deg: Optional[float] = None
    house: int = Field(..., description="whole-sign house from lagna, 1..12")
    dignity: Dignity
    vargas: dict[str, str]


class Lagna(Position):
    vargas: dict[str, str]


class Upagraha(Position):
    name: str
    alias: Optional[str] = Field(None, description="Gulika's other name: Mandi")
    name_ml: Optional[str] = Field(None, description="Malayalam name; മാന്ദി on Gulika")
    house: int
    rising_time_utc: datetime
    rising_time_local: datetime
    method: str
    convention: str = Field("", description="which rule produced this point; see docs/engine/METHODS.md")


class Panchanga(BaseModel):
    tithi: dict
    nakshatra: dict
    yoga: dict
    karana: dict
    vara: dict
    sunrise_local: Optional[datetime] = Field(None, description="null where the Sun does not rise/set")
    sunset_local: Optional[datetime] = None
    is_day_birth: Optional[bool] = None
    sunrise_convention: str


class BirthVara(BaseModel):
    """Weekday of the Hindu day, which runs from local sunrise to the next sunrise."""
    index: int = Field(..., ge=0, le=6, description="0 = Sunday")
    name_iast: str
    name_en: str
    name_ml: str


class BirthTithi(BaseModel):
    number: int = Field(..., ge=1, le=30)
    name_iast: str
    name_en: str
    name_ml: str
    paksha: Literal["shukla", "krishna"]
    paksha_iast: str
    paksha_en: str
    paksha_ml: str


class BirthNityaYoga(BaseModel):
    number: int = Field(..., ge=1, le=27)
    name_iast: str
    name_en: str
    name_ml: str


class BirthKarana(BaseModel):
    """Half-tithi. number is 1..60; the name is one of the 11 karanas."""
    number: int = Field(..., ge=1, le=60)
    name_iast: str
    name_en: str
    name_ml: str


class BirthPanchanga(BaseModel):
    """The five limbs at the birth instant. nakshatra is the Moon's birth_star."""
    vara: BirthVara
    nakshatra: BirthStar
    tithi: BirthTithi
    nitya_yoga: BirthNityaYoga
    karana: BirthKarana


class DashaPeriod(BaseModel):
    lord: str
    start_utc: datetime
    end_utc: datetime
    start_local_date: Date
    end_local_date: Date
    years: float
    bhuktis: Optional[list["DashaPeriod"]] = None


class DashaEndPair(BaseModel):
    """One period's end under both named daśā years.

    delta_days is the sāvana end minus the saura end, in days. Negative means
    the 360-day year ends earlier. span_days_* is this period's own length
    (end minus start), which is not the same number once earlier periods have
    already shifted the end date.
    """
    lord: str
    end_utc_solar: datetime
    end_utc_savana: datetime
    end_local_date_solar: Date
    end_local_date_savana: Date
    delta_days: float
    span_days_solar: float
    span_days_savana: float
    bhuktis: Optional[list["DashaEndPair"]] = None

    @model_serializer(mode="wrap")
    def _omit_empty_bhuktis(self, handler):
        data = handler(self)
        if not data.get("bhuktis"):
            data.pop("bhuktis", None)
        return data


class DashaYearCompare(BaseModel):
    """Both named year lengths. Present only when compare_dasha_years is set."""
    selected: Literal["solar_365_25", "savana_360", "custom"]
    solar_year_days: float = DASHA_YEAR_DAYS[DASHA_YEAR_SOLAR]
    savana_year_days: float = DASHA_YEAR_DAYS[DASHA_YEAR_SAVANA]
    mahadashas: list[DashaEndPair]


class Vimshottari(BaseModel):
    year_days: float
    birth_nakshatra_lord: str
    balance_at_birth_years: float
    balance_at_birth_ymd: str
    elapsed_fraction: float
    mahadashas: list[DashaPeriod]
    balance_at_birth: DashaBalance
    year_length_convention: str
    ymd_convention: str
    year_compare: Optional[DashaYearCompare] = None

    @model_serializer(mode="wrap")
    def _omit_year_compare(self, handler):
        data = handler(self)
        if data.get("year_compare") is None:
            data.pop("year_compare", None)
        return data


class TransitGraha(BaseModel):
    name: str
    longitude: float
    sign: str
    sign_index: int
    degree_in_sign: float
    nakshatra: Nakshatra
    retrograde: bool
    house_from_lagna: int
    house_from_moon: int


class Transits(BaseModel):
    at_utc: datetime
    grahas: list[TransitGraha]


class TimeInfo(BaseModel):
    local_input: datetime
    utc: datetime
    utc_offset: str
    utc_offset_hours: float
    tz_name: Optional[str]
    tz_abbrev: Optional[str]
    offset_source: str
    tzdata_version: str
    timezone_unverified: bool
    julian_day_ut: float


class Meta(BaseModel):
    engine_version: str
    basis: str = "Drik (Swiss Ephemeris), sidereal, whole-sign houses"
    settings: Settings
    ayanamsa_deg: float
    ephemeris: str
    swisseph_version: str
    combustion_orbs_source: str
    warnings: list[str]


class ChartResponse(BaseModel):
    meta: Meta
    time: TimeInfo
    place: dict
    lagna: Lagna
    grahas: list[Graha]
    upagrahas: list[Upagraha]
    houses: list[dict]
    panchanga: Panchanga
    birth_star: BirthStar
    birth_panchanga: BirthPanchanga
    vimshottari: Vimshottari
    transits: Optional[Transits] = None
