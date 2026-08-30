from datetime import date, datetime

_ACCEPTED_FORMATS = ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y")


def parse_date(raw: str) -> date:
    # used for reading the several date shapes the site and the cli both produce
    cleaned = raw.strip()
    for pattern in _ACCEPTED_FORMATS:
        try:
            return datetime.strptime(cleaned, pattern).date()
        except ValueError:
            continue
    raise ValueError(f"unrecognised date format: {raw!r}")


def format_site_date(value: date) -> str:
    # used for writing dates back in the dd/mm/yyyy shape the search endpoint expects
    return value.strftime("%d/%m/%Y")
