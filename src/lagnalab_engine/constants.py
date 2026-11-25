"""Static tables. Indices are 0-based throughout the code; names are for output only."""

RASIS = ["Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
         "Tula", "Vrischika", "Dhanu", "Makara", "Kumbha", "Meena"]
RASIS_EN = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
            "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

NAKSHATRAS = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
              "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
              "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
              "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
              "Dhanishtha", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada",
              "Revati"]

# IAST, parallel to NAKSHATRAS. English names stay in NAKSHATRAS.
NAKSHATRAS_IAST = [
    "Aśvinī", "Bharaṇī", "Kṛttikā", "Rohiṇī", "Mṛgaśīrṣa", "Ārdrā",
    "Punarvasu", "Puṣya", "Āśleṣā", "Maghā", "Pūrva Phalgunī",
    "Uttara Phalgunī", "Hastā", "Citrā", "Svātī", "Viśākhā", "Anurādhā",
    "Jyeṣṭhā", "Mūla", "Pūrvāṣāḍhā", "Uttarāṣāḍhā", "Śravaṇa",
    "Dhaniṣṭhā", "Śatabhiṣā", "Pūrva Bhādrapadā", "Uttara Bhādrapadā",
    "Revatī",
]

# Kerala Malayalam names and the Latin spelling used on Kerala charts
# (Jyeshtha = തൃക്കേട്ട / Thriketta). Common panchangam forms.
NAKSHATRAS_ML = [
    "അശ്വതി", "ഭരണി", "കാർത്തിക", "രോഹിണി", "മകയിരം", "തിരുവാതിര",
    "പുണർതം", "പൂയം", "ആയില്യം", "മകം", "പൂരം",
    "ഉത്രം", "അത്തം", "ചിത്തിര", "ചോതി", "വിശാഖം", "അനിഴം",
    "തൃക്കേട്ട", "മൂലം", "പൂരാടം", "ഉത്രാടം", "തിരുവോണം",
    "അവിട്ടം", "ചതയം", "പൂരുരുട്ടാതി", "ഉത്രട്ടാതി",
    "രേവതി",
]
NAKSHATRAS_ML_LATIN = [
    "Ashwathi", "Bharani", "Karthika", "Rohini", "Makayiram", "Thiruvathira",
    "Punartham", "Pooyam", "Ayilyam", "Makam", "Pooram",
    "Uthram", "Atham", "Chithira", "Chothi", "Vishakham", "Anizham",
    "Thriketta", "Moolam", "Pooradam", "Uthradam", "Thiruvonam",
    "Avittam", "Chathayam", "Pooruruttathi", "Uthrattathi",
    "Revathi",
]

NAK_SPAN = 360.0 / 27.0      # 13°20'
PADA_SPAN = NAK_SPAN / 4.0   # 3°20'

# Graha keys in output order.
GRAHAS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
SEVEN = GRAHAS[:7]

# Sanskrit name in Latin script, as Kerala charts print a dasha lord
# (Mercury is Budha, not the English planet name), and the Malayalam nominative.
GRAHA_SA = {
    "Sun": "Surya", "Moon": "Chandra", "Mars": "Kuja", "Mercury": "Budha",
    "Jupiter": "Guru", "Venus": "Shukra", "Saturn": "Shani", "Rahu": "Rahu", "Ketu": "Ketu",
}
GRAHA_ML = {
    "Sun": "സൂര്യൻ", "Moon": "ചന്ദ്രൻ", "Mars": "ചൊവ്വ", "Mercury": "ബുധൻ",
    "Jupiter": "വ്യാഴം", "Venus": "ശുക്രൻ", "Saturn": "ശനി", "Rahu": "രാഹു", "Ketu": "കേതു",
}

# Mean Julian year. Scales dasha calendar dates only; see core.YMD_RULE.
DASHA_YEAR_DAYS_DEFAULT = 365.25

# Named Vimshottari year modes. solar_365_25 is the default (industry 365.25-day
# year). savana_360 is the Kerala traditional year: 12 months × 30 days.
# Sidereal 365.256364 is intentionally not a mode.
DASHA_YEAR_SOLAR = "solar_365_25"
DASHA_YEAR_SAVANA = "savana_360"
DASHA_YEAR_DAYS = {
    DASHA_YEAR_SOLAR: DASHA_YEAR_DAYS_DEFAULT,
    DASHA_YEAR_SAVANA: 360.0,
}

# Weekday 0=Sunday .. 6=Saturday; lord of each weekday.
WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
WEEKDAY_LORD = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
VARAS = ["Ravivara", "Somavara", "Mangalavara", "Budhavara", "Guruvara", "Shukravara", "Shanivara"]

# Sign lords (Mesha..Meena).
SIGN_LORD = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
             "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"]

# Exaltation sign and deep-exaltation degree (debilitation = opposite sign, same degree).
EXALTATION = {"Sun": (0, 10), "Moon": (1, 3), "Mars": (9, 28), "Mercury": (5, 15),
              "Jupiter": (3, 5), "Venus": (11, 27), "Saturn": (6, 20)}

# Naisargika (natural) relationships: friends / neutral / enemies.
NAISARGIKA = {
    "Sun":     {"friends": ["Moon", "Mars", "Jupiter"], "neutral": ["Mercury"], "enemies": ["Venus", "Saturn"]},
    "Moon":    {"friends": ["Sun", "Mercury"], "neutral": ["Mars", "Jupiter", "Venus", "Saturn"], "enemies": []},
    "Mars":    {"friends": ["Sun", "Moon", "Jupiter"], "neutral": ["Venus", "Saturn"], "enemies": ["Mercury"]},
    "Mercury": {"friends": ["Sun", "Venus"], "neutral": ["Mars", "Jupiter", "Saturn"], "enemies": ["Moon"]},
    "Jupiter": {"friends": ["Sun", "Moon", "Mars"], "neutral": ["Saturn"], "enemies": ["Mercury", "Venus"]},
    "Venus":   {"friends": ["Mercury", "Saturn"], "neutral": ["Mars", "Jupiter"], "enemies": ["Sun", "Moon"]},
    "Saturn":  {"friends": ["Mercury", "Venus"], "neutral": ["Jupiter"], "enemies": ["Sun", "Moon", "Mars"]},
}

# Dig bala: whole-sign house (1-based) in which the graha has full directional strength.
DIG_BALA_HOUSE = {"Jupiter": 1, "Mercury": 1, "Moon": 4, "Venus": 4,
                  "Saturn": 7, "Sun": 10, "Mars": 10}

# Combustion orbs in degrees of longitude from the Sun.
# Source: Surya Siddhanta 9.6-9 (Jupiter 11, Saturn 15, Mars 17, Venus 10 / 8 when retrograde,
# Mercury 14 / 12 when retrograde) and 10.1 (Moon 12), Burgess tr. 1860 (public domain).
# Caveat: the text's figures are kalamsas (time-degrees of oblique ascension); applying them
# as ecliptic-longitude orbs is the common modern simplification, used here.
COMBUSTION_ORB = {"Moon": (12, 12), "Mars": (17, 17), "Mercury": (14, 12),
                  "Jupiter": (11, 11), "Venus": (10, 8), "Saturn": (15, 15)}  # (direct, retrograde)

TITHIS = ["Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami", "Shashthi", "Saptami",
          "Ashtami", "Navami", "Dashami", "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi"]

YOGAS = ["Vishkambha", "Priti", "Ayushman", "Saubhagya", "Shobhana", "Atiganda", "Sukarma",
         "Dhriti", "Shula", "Ganda", "Vriddhi", "Dhruva", "Vyaghata", "Harshana", "Vajra",
         "Siddhi", "Vyatipata", "Variyana", "Parigha", "Shiva", "Siddha", "Sadhya", "Shubha",
         "Shukla", "Brahma", "Indra", "Vaidhriti"]

MOVABLE_KARANAS = ["Bava", "Balava", "Kaulava", "Taitila", "Gara", "Vanija", "Vishti"]

# Vimshottari: lord order from Ashwini, and years.
VIMSHOTTARI_ORDER = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
VIMSHOTTARI_YEARS = {"Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7,
                     "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17}

# Mandi rising times (ghatikas, for a 30-ghatika day/night), Sunday..Saturday.
# Source: Prasna Marga ch.5 st.14-16 as explained in B.V. Raman's notes (and the gulikodaya table
# in his notes to ch.2 st.16-20); scaled proportionally to the actual day/night length.
MANDI_GHATIKA_DAY = [26, 22, 18, 14, 10, 6, 2]
MANDI_GHATIKA_NIGHT = [10, 6, 2, 26, 22, 18, 14]

# Gulika. Default is the Prasna Marga Mandi ghatika table (same point as Mandi).
# start/middle/end are the Saturn-eighth alternatives. Day is sunrise→sunset and
# night is sunset→next sunrise, both the real times at the birthplace. For the
# eighth-part alternatives, night parts start from the 5th lord counted from the
# weekday lord, and the 8th part has no lord. The PyJHora golden check compares `start`.
GULIKA_CONVENTION = {
    "prasna_marga_mandi": (
        "Prasna Marga ch. 5 st. 14-16: Gulika is the lagna rising at the Mandi ghatika "
        "(day 26, 22, 18, 14, 10, 6, 2 and night 10, 6, 2, 26, 22, 18, 14 ghatikas, "
        "Sunday to Saturday), scaled to the real sunrise-to-sunset day or sunset-to-next-sunrise "
        "night at the birthplace. Default. Labelled Gulika, alias Mandi."
    ),
    "start": (
        "vedicastro.com: ascendant at the START of Saturn's eighth-part of the day or night. "
        "Day parts run from the weekday lord; night parts run from the 5th lord counted from "
        "the weekday lord. Sunrise and sunset are the real times at the birthplace. "
        "Selectable alternative; also the BPHS gulikarambhakale reading. "
        "The PyJHora golden check compares this instant."
    ),
    "end": (
        "Uttara Kalamrita (astrojyoti.com uttarakalamritam1-2, sloka 8): ascendant at the END "
        "of Saturn's eighth-part. Same day/night split, same night count from the 5th lord, "
        "same real sunrise and sunset at the birthplace."
    ),
    "middle": (
        "ascendant at the MIDDLE of Saturn's eighth-part. Same day/night split and the same "
        "real sunrise and sunset. Not the Prasna Marga ghatika table "
        "(gulika_point prasna_marga_mandi)."
    ),
}
MANDI_CONVENTION = {
    "prasna_marga_ghatika": (
        "Prasna Marga ghatika table (day 26, 22, 18, 14, 10, 6, 2 and night 10, 6, 2, 26, 22, "
        "18, 14 ghatikas, Sunday..Saturday), scaled to the real sunrise-sunset day or "
        "sunset-sunrise night at the birthplace."
    ),
    "saturn_segment_start": GULIKA_CONVENTION["start"] + " Applied here as Mandi.",
    "saturn_segment_middle": GULIKA_CONVENTION["middle"] + " Applied here as Mandi.",
    "saturn_segment_end": GULIKA_CONVENTION["end"] + " Applied here as Mandi.",
}


def karana_name(k: int) -> str:
    """k = 0..59 index of the half-tithi from the start of Shukla Pratipada."""
    if k == 0:
        return "Kimstughna"
    if k == 57:
        return "Shakuni"
    if k == 58:
        return "Chatushpada"
    if k == 59:
        return "Naga"
    return MOVABLE_KARANAS[(k - 1) % 7]


# Tithi names for the 14 lunar days, then Purnima and Amavasya.
# English matches the strings already returned on panchanga.tithi.name.
TITHI_EN = TITHIS + ["Purnima", "Amavasya"]
TITHI_IAST = [
    "Pratipadā", "Dvitīyā", "Tṛtīyā", "Caturthī", "Pañcamī", "Ṣaṣṭhī", "Saptamī",
    "Aṣṭamī", "Navamī", "Daśamī", "Ekādaśī", "Dvādaśī", "Trayodaśī", "Caturdaśī",
    "Pūrṇimā", "Amāvāsyā",
]
TITHI_ML = [
    "പ്രതിപദ", "ദ്വിതീയ", "തൃതീയ", "ചതുർത്ഥി", "പഞ്ചമി", "ഷഷ്ഠി", "സപ്തമി",
    "അഷ്ടമി", "നവമി", "ദശമി", "ഏകാദശി", "ദ്വാദശി", "ത്രയോദശി", "ചതുർദശി",
    "പൗർണമി", "അമാവാസി",
]
PAKSHA_EN = {"shukla": "Shukla", "krishna": "Krishna"}
PAKSHA_IAST = {"shukla": "Śukla", "krishna": "Kṛṣṇa"}
PAKSHA_ML = {"shukla": "ശുക്ലപക്ഷം", "krishna": "കൃഷ്ണപക്ഷം"}

# Nitya yoga, parallel to YOGAS (English). 1 = Vishkambha.
YOGA_IAST = [
    "Viṣkambha", "Prīti", "Āyuṣmān", "Saubhāgya", "Śobhana", "Atigaṇḍa", "Sukarman",
    "Dhṛti", "Śūla", "Gaṇḍa", "Vṛddhi", "Dhruva", "Vyāghāta", "Harṣaṇa", "Vajra",
    "Siddhi", "Vyatīpāta", "Varīyān", "Parigha", "Śiva", "Siddha", "Sādhya", "Śubha",
    "Śukla", "Brahman", "Indra", "Vaidhṛti",
]
YOGA_ML = [
    "വിഷ്കംഭം", "പ്രീതി", "ആയുഷ്മാൻ", "സൗഭാഗ്യം", "ശോഭനം", "അതിഗണ്ഡം", "സുകർമ്മം",
    "ധൃതി", "ശൂലം", "ഗണ്ഡം", "വൃദ്ധി", "ധ്രുവം", "വ്യാഘാതം", "ഹർഷണം", "വജ്രം",
    "സിദ്ധി", "വ്യതീപാതം", "വരീയാൻ", "പരിഘം", "ശിവം", "സിദ്ധം", "സാധ്യം", "ശുഭം",
    "ശുക്ലം", "ബ്രഹ്മം", "ഇന്ദ്രം", "വൈധൃതി",
]

# The 11 karana names. Numbers 1..60 map onto these; see karana_record.
KARANA_EN = ["Kimstughna", "Bava", "Balava", "Kaulava", "Taitila", "Gara", "Vanija",
             "Vishti", "Shakuni", "Chatushpada", "Naga"]
KARANA_IAST = ["Kiṃstughna", "Bava", "Bālava", "Kaulava", "Taitila", "Gara", "Vaṇija",
               "Viṣṭi", "Śakuni", "Catuṣpāda", "Nāga"]
KARANA_ML = ["കിംസ്തുഘ്നം", "ബവം", "ബാലവം", "കൗലവം", "തൈതിലം", "ഗരം", "വണിജം",
             "വിഷ്ടി", "ശകുനി", "ചതുഷ്പാദം", "നാഗം"]

# Vara. Index 0 = Sunday, the Hindu day that begins at local sunrise.
VARA_IAST = ["Ravivāra", "Somavāra", "Maṅgalavāra", "Budhavāra", "Guruvāra", "Śukravāra", "Śanivāra"]
VARA_ML = ["ഞായറാഴ്ച", "തിങ്കളാഴ്ച", "ചൊവ്വാഴ്ച", "ബുധനാഴ്ച", "വ്യാഴാഴ്ച", "വെള്ളിയാഴ്ച", "ശനിയാഴ്ച"]


def tithi_record(number: int) -> dict:
    """Tithi 1..30. paksha is 'shukla' or 'krishna'."""
    i = number - 1
    if i == 14:
        idx = 14
    elif i == 29:
        idx = 15
    else:
        idx = i % 15
    paksha = "shukla" if i < 15 else "krishna"
    return dict(number=number, paksha=paksha, name_en=TITHI_EN[idx], name_iast=TITHI_IAST[idx],
                name_ml=TITHI_ML[idx], paksha_en=PAKSHA_EN[paksha], paksha_iast=PAKSHA_IAST[paksha],
                paksha_ml=PAKSHA_ML[paksha])


def yoga_record(number: int) -> dict:
    """Nitya yoga 1..27."""
    i = number - 1
    return dict(number=number, name_en=YOGAS[i], name_iast=YOGA_IAST[i], name_ml=YOGA_ML[i])


def karana_record(number: int) -> dict:
    """Karana 1..60, mapped onto the 11 names."""
    name = karana_name(number - 1)
    i = KARANA_EN.index(name)
    return dict(number=number, name_en=name, name_iast=KARANA_IAST[i], name_ml=KARANA_ML[i])


def vara_record(index: int) -> dict:
    """Weekday 0..6, Sunday .. Saturday, for the Hindu day from local sunrise."""
    return dict(index=index, name_en=WEEKDAYS[index], name_iast=VARA_IAST[index], name_ml=VARA_ML[index])


if not (len(NAKSHATRAS) == len(NAKSHATRAS_IAST) == len(NAKSHATRAS_ML) == len(NAKSHATRAS_ML_LATIN) == 27):
    raise RuntimeError("nakshatra name tables must all have length 27")
if not (len(YOGAS) == len(YOGA_IAST) == len(YOGA_ML) == 27):
    raise RuntimeError("nitya yoga name tables must all have length 27")
if not (len(TITHI_EN) == len(TITHI_IAST) == len(TITHI_ML) == 16):
    raise RuntimeError("tithi name tables must have length 16")
if not (len(KARANA_EN) == len(KARANA_IAST) == len(KARANA_ML) == 11):
    raise RuntimeError("karana name tables must have length 11")
if not (len(VARA_IAST) == len(VARA_ML) == len(WEEKDAYS) == 7):
    raise RuntimeError("vara name tables must have length 7")
if set(GRAHA_SA) != set(GRAHAS) or set(GRAHA_ML) != set(GRAHAS):
    raise RuntimeError("graha Sanskrit/Malayalam tables must cover GRAHAS")
