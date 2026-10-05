"""
"What's new" site banner, driven by the newest dated entry in CHANGELOG.md.

The banner turns on automatically when a new release heading is published to
CHANGELOG.md (release-please writes these, for example
"## [3.48.0](https://github.com/.../compare/...) (2026-10-03)") and stays on
through the end of the Nth business day, counting the release date as day 1
when it is a business day. Because only the newest entry is used, a newer entry
published inside the window restarts the count.

Business days are weekdays that are not US federal holidays, counted in
Eastern time.

Admins can switch the banner off for everyone with the CHANGELOG_BANNER_ENABLED
setting in Django admin (Constance). See documentation/CHANGELOG_BANNER.md.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from django.conf import settings

CHANGELOG_URL = (
    "https://github.com/HHS/simpler-grants-pdf-builder/blob/main/CHANGELOG.md"
    "#changelog"
)

BANNER_TIMEZONE = ZoneInfo("America/New_York")

# Matches dated release headings in both formats CHANGELOG.md has used:
#   release-please: "## [3.48.0](https://github.com/.../compare/...) (2026-10-03)"
#   Keep a Changelog: "## [3.33.0] - 2026-05-26"
# "## [Unreleased]" and undated headings are ignored on purpose.
RELEASE_HEADING_RE = re.compile(
    r"^##\s+\[(?P<version>[^\]]+)\](?:\([^)]*\))?\s+"
    r"(?:-\s+(?P<date>\d{4}-\d{2}-\d{2})|\((?P<paren_date>\d{4}-\d{2}-\d{2})\))\s*$",
    re.MULTILINE,
)


@dataclass(frozen=True)
class ChangelogRelease:
    version: str
    release_date: date


def get_changelog_path():
    return Path(settings.BASE_DIR).parent / "CHANGELOG.md"


def parse_latest_release(changelog_text):
    """Return the newest dated release in the changelog text, or None."""
    releases = []
    for match in RELEASE_HEADING_RE.finditer(changelog_text or ""):
        try:
            release_date = date.fromisoformat(
                match.group("date") or match.group("paren_date")
            )
        except ValueError:
            continue
        releases.append(ChangelogRelease(match.group("version"), release_date))

    if not releases:
        return None

    # Entries are newest-first by convention, but don't rely on it.
    return max(releases, key=lambda release: release.release_date)


@lru_cache(maxsize=1)
def get_latest_release():
    """
    Read CHANGELOG.md once per process. The file only changes on deploy, so
    caching it for the life of the process is safe.
    """
    try:
        changelog_text = get_changelog_path().read_text(encoding="utf-8")
    except OSError:
        return None
    return parse_latest_release(changelog_text)


def _nth_weekday(year, month, weekday, n):
    """The nth (1-based) weekday of a month. Monday is 0."""
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + 7 * (n - 1))


def _last_weekday(year, month, weekday):
    next_month = date(year + month // 12, month % 12 + 1, 1)
    last = next_month - timedelta(days=1)
    return last - timedelta(days=(last.weekday() - weekday) % 7)


def _observed(day):
    """Federal holidays on a Saturday are observed Friday, Sunday on Monday."""
    if day.weekday() == 5:
        return day - timedelta(days=1)
    if day.weekday() == 6:
        return day + timedelta(days=1)
    return day


@lru_cache(maxsize=16)
def federal_holidays(year):
    """Observed US federal holidays (5 U.S.C. 6103) for a year."""
    MONDAY, THURSDAY = 0, 3
    holidays = {
        _observed(date(year, 1, 1)),  # New Year's Day
        _nth_weekday(year, 1, MONDAY, 3),  # Birthday of Martin Luther King, Jr.
        _nth_weekday(year, 2, MONDAY, 3),  # Washington's Birthday
        _last_weekday(year, 5, MONDAY),  # Memorial Day
        _observed(date(year, 6, 19)),  # Juneteenth
        _observed(date(year, 7, 4)),  # Independence Day
        _nth_weekday(year, 9, MONDAY, 1),  # Labor Day
        _nth_weekday(year, 10, MONDAY, 2),  # Columbus Day
        _observed(date(year, 11, 11)),  # Veterans Day
        _nth_weekday(year, 11, THURSDAY, 4),  # Thanksgiving Day
        _observed(date(year, 12, 25)),  # Christmas Day
    }
    # New Year's Day on a Saturday is observed on Dec 31 of the prior year.
    if date(year + 1, 1, 1).weekday() == 5:
        holidays.add(date(year, 12, 31))
    return frozenset(holidays)


def is_business_day(day):
    return day.weekday() < 5 and day not in federal_holidays(day.year)


def banner_end_date(release_date, business_days):
    """
    The last day the banner shows. The release date is day 1 if it is a
    business day; otherwise counting starts on the next business day.
    """
    day = release_date
    counted = 0
    while True:
        if is_business_day(day):
            counted += 1
            if counted >= business_days:
                return day
        day += timedelta(days=1)


def get_active_release(today=None, business_days=5):
    """
    Return the release to announce if today falls inside its banner window,
    otherwise None. Future-dated entries never show.
    """
    if business_days < 1:
        return None

    release = get_latest_release()
    if release is None:
        return None

    if today is None:
        today = datetime.now(BANNER_TIMEZONE).date()

    if release.release_date > today:
        return None
    if today > banner_end_date(release.release_date, business_days):
        return None
    return release
