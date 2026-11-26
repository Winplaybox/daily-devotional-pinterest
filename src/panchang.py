"""Date localization and approximate Hindu lunar Tithi formatter."""

from datetime import date, datetime, timezone
import math

# Reference new moon: 2000-01-06 18:14 UTC (Julian Day 2451550.26)
_REF_NEW_MOON_JD = 2451550.26
_SYNODIC_MONTH = 29.53058867

_TITHI_NAMES_GU = [
    "એકમ", "બીજ", "ત્રીજ", "ચોથ", "પાંચમ",
    "છઠ", "સાતમ", "આઠમ", "નોમ", "દશમ",
    "અગિયારસ", "બારસ", "તેરસ", "ચૌદશ", "પૂનમ",
]
_TITHI_NAMES_GU_KRISHNA = _TITHI_NAMES_GU[:-1] + ["અમાસ"]

_TITHI_NAMES_HI = [
    "प्रतिपदा", "द्वितीया", "तृतीया", "चतुर्थी", "पंचमी",
    "षष्ठी", "सप्तमी", "अष्टमी", "नवमी", "दशमी",
    "एकादशी", "द्वादशी", "त्रयोदशी", "चतुर्दशी", "पूर्णिमा",
]
_TITHI_NAMES_HI_KRISHNA = _TITHI_NAMES_HI[:-1] + ["अमावस्या"]


def localize_digits(text: str, digits: str) -> str:
    """Replace ASCII digits 0-9 with localized numeral characters."""
    if not digits or digits == "0123456789" or len(digits) != 10:
        return text
    table = str.maketrans("0123456789", digits)
    return text.translate(table)


def format_date(target_date: date, digits: str = "0123456789") -> str:
    """Format date as DD-MM-YYYY with localized digits."""
    return localize_digits(target_date.strftime("%d-%m-%Y"), digits)


def _to_julian_day(d: date) -> float:
    dt = datetime(d.year, d.month, d.day, 6, 0, tzinfo=timezone.utc)
    y, m = dt.year, dt.month
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + (a // 4)
    return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + dt.day + (dt.hour / 24.0) + b - 1524.5


def get_lunar_tithi(target_date: date, lang_code: str = "gu") -> str:
    """Return approximate Hindu lunar Paksha + Tithi label for a date."""
    jd = _to_julian_day(target_date)
    lunar_age = (jd - _REF_NEW_MOON_JD) % _SYNODIC_MONTH
    tithi_index = int(math.floor((lunar_age / _SYNODIC_MONTH) * 30)) % 30  # 0..29

    is_shukla = tithi_index < 15
    day_num = (tithi_index % 15) + 1

    if lang_code == "gu":
        paksha = "સુદ" if is_shukla else "વદ"
        return localize_digits(f"{paksha} {day_num}", "૦૧૨૩૪૫૬૭૮૯")
    if lang_code in ("hi", "mr"):
        paksha = "शुक्ल" if is_shukla else "कृष्ण"
        return localize_digits(f"{paksha} {day_num}", "०१२३४५६७८९")
    paksha = "Shukla" if is_shukla else "Krishna"
    return f"{paksha} Paksha {day_num}"
