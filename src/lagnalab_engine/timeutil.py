"""Local civil time -> UTC using the IANA tz database (historical offsets).

We pin zoneinfo to the `tzdata` PyPI package (not the OS copy) so results are reproducible and the
database version can be reported.
"""
from __future__ import annotations

import zoneinfo
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone

import tzdata

zoneinfo.reset_tzpath(to=[])  # use the tzdata package only
TZDATA_VERSION = tzdata.IANA_VERSION

# Zones covering pre-1947 British India / princely states.
SUBCONTINENT_ZONES = {"Asia/Kolkata", "Asia/Calcutta", "Asia/Karachi", "Asia/Dhaka", "Asia/Dacca",
                      "Asia/Kathmandu", "Asia/Katmandu", "Asia/Colombo", "Asia/Thimphu", "Asia/Yangon",
                      "Asia/Rangoon"}
INDIA_TZ_CUTOFF = date(1955, 1, 1)


@dataclass
class ResolvedTime:
    local: datetime                 # naive local civil time as entered
    utc: datetime                   # aware UTC
    utc_offset_seconds: int
    tz_name: str | None
    tz_abbrev: str | None
    offset_source: str              # "iana:<zone>" | "override" | "lmt"
    warnings: list[str] = field(default_factory=list)
    timezone_unverified: bool = False


def tz_from_latlon(lat: float, lon: float) -> str | None:
    try:
        from timezonefinder import TimezoneFinder
    except ImportError:  # pragma: no cover
        return None
    return TimezoneFinder().timezone_at(lng=lon, lat=lat)


def _in_british_india_box(lat: float | None, lon: float | None) -> bool:
    if lat is None or lon is None:
        return False
    return 5.0 <= lat <= 37.5 and 60.0 <= lon <= 98.0


def fmt_offset(seconds: int) -> str:
    sign = "+" if seconds >= 0 else "-"
    s = abs(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{sign}{h:02d}:{m:02d}" + (f":{sec:02d}" if sec else "")


def resolve(d: date, t: time, tz_name: str | None = None, lat: float | None = None,
            lon: float | None = None, utc_offset_override_hours: float | None = None,
            use_lmt: bool = False, fold: int = 0) -> ResolvedTime:
    local = datetime.combine(d, t)
    warnings: list[str] = []

    if use_lmt:
        if lon is None:
            raise ValueError("use_lmt requires a longitude")
        off = round(lon * 240)  # 4 minutes of time per degree
        res = ResolvedTime(local, (local - timedelta(seconds=off)).replace(tzinfo=timezone.utc), off,
                           tz_name, "LMT", "lmt", warnings)
    elif utc_offset_override_hours is not None:
        off = round(utc_offset_override_hours * 3600)
        res = ResolvedTime(local, (local - timedelta(seconds=off)).replace(tzinfo=timezone.utc), off,
                           tz_name, None, "override", warnings)
    else:
        if tz_name is None:
            if lat is None or lon is None:
                raise ValueError("need tz_name, or lat/lon to look it up, or a utc offset override")
            tz_name = tz_from_latlon(lat, lon)
            if tz_name is None:
                raise ValueError("could not determine time zone from coordinates")
            warnings.append(f"time zone inferred from coordinates: {tz_name}")
        try:
            z = zoneinfo.ZoneInfo(tz_name)
        except (zoneinfo.ZoneInfoNotFoundError, ValueError) as e:
            raise ValueError(f"unknown IANA time zone {tz_name!r}") from e
        a = local.replace(tzinfo=z, fold=fold)
        other = local.replace(tzinfo=z, fold=1 - fold)
        if a.utcoffset() != other.utcoffset():
            back = a.astimezone(timezone.utc).astimezone(z).replace(tzinfo=None)
            if back != local:
                warnings.append(
                    f"local time {local.isoformat()} does not exist in {tz_name} (clock change gap); "
                    f"interpreted with offset {fmt_offset(int(a.utcoffset().total_seconds()))}")
            else:
                warnings.append(
                    f"local time {local.isoformat()} is ambiguous in {tz_name} (clocks set back); "
                    f"using fold={fold} offset {fmt_offset(int(a.utcoffset().total_seconds()))}, "
                    f"the other reading is {fmt_offset(int(other.utcoffset().total_seconds()))}")
        off = int(a.utcoffset().total_seconds())
        res = ResolvedTime(local, a.astimezone(timezone.utc), off, tz_name, a.tzname(),
                           f"iana:{tz_name}", warnings)

    if d < INDIA_TZ_CUTOFF and (res.tz_name in SUBCONTINENT_ZONES or _in_british_india_box(lat, lon)):
        res.timezone_unverified = True
        res.warnings.append(
            "timezone unverified: births in the Indian subcontinent before 1955 may have been recorded in "
            "a local or city time rather than the IANA offset used here. Check which clock the birth "
            "time was read from: railway/Madras time (+05:21:10, to 1906), IST (+05:30), Calcutta "
            "government time (+05:53:20 or +05:54, used locally until about 1948), Bombay Time "
            "(about +04:51, used locally until about 1955; unverified), war time (+06:30, "
            "1941-10 to 1942-05-15 and 1942-09 to 1945-10-15 per tzdata, whose source it calls dubious), "
            "or local mean time. Confirm the UTC offset, or resubmit with utc_offset_override_hours.")
    return res
