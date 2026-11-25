"""Divisional charts (vargas), Parashara methods. Signs are 0=Mesha .. 11=Meena.

Each function takes a sidereal longitude and returns the varga sign index. `s` = rasi index,
`d` = degrees within the rasi (0 <= d < 30). "Odd" signs are Mesha, Mithuna, Simha... (index even).

D2  Hora:       odd sign: 0-15° Sun's hora (Simha), 15-30° Moon's hora (Karka);
                even sign: 0-15° Karka, 15-30° Simha.   (Parashara, BPHS 'Hora' as Sun/Moon horas)
D3  Drekkana:   0-10° the sign itself, 10-20° the 5th from it, 20-30° the 9th.
D7  Saptamsa:   7 parts of 4°17'8.57"; odd sign: count from the sign itself; even sign: count
                from the 7th sign.
D9  Navamsa:    9 parts of 3°20'; movable signs start from the sign itself, fixed signs from the
                9th, dual signs from the 5th (equivalently: fire from Mesha, earth from Makara,
                air from Tula, water from Karka). Equals the continuous rule floor(L / 3°20') mod 12.
D10 Dasamsa:    10 parts of 3°; odd sign: count from the sign itself; even sign: from the 9th.
D12 Dwadasamsa: 12 parts of 2°30', counted from the sign itself.
D30 Trimsamsa:  unequal parts. Odd sign: 0-5 Mars (Mesha), 5-10 Saturn (Kumbha), 10-18 Jupiter
                (Dhanu), 18-25 Mercury (Mithuna), 25-30 Venus (Tula). Even sign: 0-5 Venus
                (Vrishabha), 5-12 Mercury (Kanya), 12-20 Jupiter (Meena), 20-25 Saturn (Makara),
                25-30 Mars (Vrischika). Each part is half-open [start, end).
"""
from __future__ import annotations

EPS = 1e-9


def _split(lon: float):
    s = int(lon // 30) % 12
    d = lon - (lon // 30) * 30
    return s, d


def _odd(s: int) -> bool:
    return s % 2 == 0  # Mesha (0) is the first, odd, sign


def d2(lon):
    s, d = _split(lon)
    first = d < 15
    return 4 if first == _odd(s) else 3   # 4 Simha (Sun), 3 Karka (Moon)


def d3(lon):
    s, d = _split(lon)
    return (s + 4 * int(d // 10)) % 12


def d7(lon):
    s, d = _split(lon)
    part = min(int(d * 7 // 30), 6)
    start = s if _odd(s) else (s + 6) % 12
    return (start + part) % 12


def d9(lon):
    s, d = _split(lon)
    part = min(int(d * 9 // 30), 8)
    start = {0: s, 1: (s + 8) % 12, 2: (s + 4) % 12}[s % 3]  # movable, fixed, dual
    return (start + part) % 12


def d10(lon):
    s, d = _split(lon)
    part = min(int(d // 3), 9)
    start = s if _odd(s) else (s + 8) % 12
    return (start + part) % 12


def d12(lon):
    s, d = _split(lon)
    return (s + min(int(d // 2.5), 11)) % 12


_D30_ODD = [(5, 0), (10, 10), (18, 8), (25, 2), (30, 6)]
_D30_EVEN = [(5, 1), (12, 5), (20, 11), (25, 9), (30, 7)]


def d30(lon):
    s, d = _split(lon)
    for end, sign in (_D30_ODD if _odd(s) else _D30_EVEN):
        if d < end:
            return sign
    return (_D30_ODD if _odd(s) else _D30_EVEN)[-1][1]


VARGAS = {"D2": d2, "D3": d3, "D7": d7, "D9": d9, "D10": d10, "D12": d12, "D30": d30}
