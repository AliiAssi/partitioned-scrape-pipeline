import re

_WHITESPACE = re.compile(r"[ \t\r\f\v]+")
_BLANK_LINES = re.compile(r"\n{3,}")


def collapse_whitespace(value: str) -> str:
    # used for tidying the ragged whitespace that comes out of html table cells
    return _WHITESPACE.sub(" ", value).strip()


def collapse_blank_lines(value: str) -> str:
    # used for keeping paragraph breaks while dropping the runs of empty lines
    return _BLANK_LINES.sub("\n\n", value)


def slugify_identifier(identifier: str) -> str:
    # used for turning "IR - SC - 00001785" into something safe for an object key
    return re.sub(r"[^a-z0-9]+", "-", identifier.lower()).strip("-")
