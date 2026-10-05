from datetime import date
from unittest.mock import patch

from constance.test import override_config
from django.test import TestCase
from django.urls import reverse
from freezegun import freeze_time

from ..changelog_banner import (
    CHANGELOG_URL,
    ChangelogRelease,
    banner_end_date,
    federal_holidays,
    get_active_release,
    get_latest_release,
    is_business_day,
    parse_latest_release,
)
from ..context_processors import get_changelog_banner

CHANGELOG_TEXT = """# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

- Something not out yet

## [3.34.0](https://github.com/HHS/simpler-grants-pdf-builder/compare/nofos-v3.33.0...nofos-v3.34.0) (2026-10-05)


### Features

* a thing ([#1](https://github.com/HHS/simpler-grants-pdf-builder/issues/1))

## [3.33.0] - 2026-05-26

### Fixed

- Another thing
"""

RELEASE = ChangelogRelease("3.34.0", date(2026, 10, 5))


class ParseLatestReleaseTests(TestCase):
    def test_returns_newest_dated_release(self):
        self.assertEqual(parse_latest_release(CHANGELOG_TEXT), RELEASE)

    def test_keep_a_changelog_heading_format(self):
        text = "## [3.33.0] - 2026-05-26\n\n### Added\n"
        self.assertEqual(
            parse_latest_release(text), ChangelogRelease("3.33.0", date(2026, 5, 26))
        )

    def test_release_please_heading_format(self):
        text = (
            "## [3.48.0](https://github.com/HHS/simpler-grants-pdf-builder/compare/"
            "nofos-v3.47.1...nofos-v3.48.0) (2026-10-03)\n"
        )
        self.assertEqual(
            parse_latest_release(text), ChangelogRelease("3.48.0", date(2026, 10, 3))
        )

    def test_mixed_formats_pick_newest(self):
        # The real file switched formats at 3.34.0
        text = "## [3.34.0](https://x) (2026-09-03)\n\n## [3.33.0] - 2026-05-26\n"
        self.assertEqual(parse_latest_release(text).version, "3.34.0")

    def test_ignores_unreleased_and_undated_headings(self):
        text = "## [Unreleased]\n\n## [4.0.0]\n\n## [3.0.0] - 2026-01-02\n"
        self.assertEqual(
            parse_latest_release(text), ChangelogRelease("3.0.0", date(2026, 1, 2))
        )

    def test_does_not_rely_on_entry_order(self):
        text = "## [1.0.0] - 2026-01-02\n\n## [1.1.0] - 2026-03-04\n"
        self.assertEqual(parse_latest_release(text).version, "1.1.0")

    def test_skips_invalid_dates(self):
        text = "## [2.0.0] - 2026-13-45\n\n## [1.0.0] - 2026-01-02\n"
        self.assertEqual(parse_latest_release(text).version, "1.0.0")

    def test_no_releases(self):
        self.assertIsNone(parse_latest_release("# Changelog\n"))
        self.assertIsNone(parse_latest_release(""))
        self.assertIsNone(parse_latest_release(None))

    def test_repo_changelog_has_a_parseable_release(self):
        # Guards against the CHANGELOG.md heading format drifting.
        get_latest_release.cache_clear()
        self.addCleanup(get_latest_release.cache_clear)
        self.assertIsNotNone(get_latest_release())


class BusinessDayTests(TestCase):
    def test_federal_holidays_2026(self):
        self.assertEqual(
            sorted(federal_holidays(2026)),
            [
                date(2026, 1, 1),
                date(2026, 1, 19),
                date(2026, 2, 16),
                date(2026, 5, 25),
                date(2026, 6, 19),
                date(2026, 7, 3),  # July 4 is a Saturday
                date(2026, 9, 7),
                date(2026, 10, 12),
                date(2026, 11, 11),
                date(2026, 11, 26),
                date(2026, 12, 25),
            ],
        )

    def test_new_years_on_saturday_is_observed_prior_december(self):
        # Jan 1, 2028 is a Saturday
        self.assertIn(date(2027, 12, 31), federal_holidays(2027))

    def test_weekends_are_not_business_days(self):
        self.assertFalse(is_business_day(date(2026, 10, 3)))  # Saturday
        self.assertFalse(is_business_day(date(2026, 10, 4)))  # Sunday
        self.assertTrue(is_business_day(date(2026, 10, 5)))  # Monday

    def test_end_date_counts_release_day_and_skips_holidays(self):
        # Mon Oct 5 is day 1; Mon Oct 12 (Columbus Day) is skipped
        self.assertEqual(banner_end_date(date(2026, 10, 5), 10), date(2026, 10, 19))

    def test_end_date_for_weekend_release_starts_next_business_day(self):
        # Sat Oct 3: counting starts Mon Oct 5
        self.assertEqual(banner_end_date(date(2026, 10, 3), 10), date(2026, 10, 19))

    def test_end_date_one_business_day(self):
        self.assertEqual(banner_end_date(date(2026, 10, 5), 1), date(2026, 10, 5))


@patch("bloom_nofos.changelog_banner.get_latest_release", return_value=RELEASE)
class GetActiveReleaseTests(TestCase):
    def test_active_on_release_day(self, _):
        self.assertEqual(get_active_release(today=date(2026, 10, 5)), RELEASE)

    def test_active_on_last_business_day(self, _):
        self.assertEqual(get_active_release(today=date(2026, 10, 19)), RELEASE)

    def test_inactive_after_window(self, _):
        self.assertIsNone(get_active_release(today=date(2026, 10, 20)))

    def test_inactive_for_future_dated_entry(self, _):
        self.assertIsNone(get_active_release(today=date(2026, 10, 2)))

    def test_custom_business_days(self, _):
        self.assertEqual(
            get_active_release(today=date(2026, 10, 20), business_days=11), RELEASE
        )
        self.assertIsNone(get_active_release(today=date(2026, 10, 5), business_days=0))

    @freeze_time("2026-10-20 02:00:00")  # still Oct 19 in Eastern time
    def test_today_uses_eastern_time(self, _):
        self.assertEqual(get_active_release(), RELEASE)

    @freeze_time("2026-10-20 05:00:00")  # Oct 20, 1am Eastern
    def test_today_uses_eastern_time_after_midnight(self, _):
        self.assertIsNone(get_active_release())

    def test_newer_entry_restarts_the_window(self, mock_latest):
        # 3.34.0's window would end Oct 19; a 3.35.0 entry on Oct 16 restarts it.
        mock_latest.return_value = ChangelogRelease("3.35.0", date(2026, 10, 16))
        self.assertEqual(get_active_release(today=date(2026, 10, 29)).version, "3.35.0")


@patch("bloom_nofos.changelog_banner.get_latest_release", return_value=RELEASE)
@freeze_time("2026-10-06 12:00:00")
@override_config(CHANGELOG_BANNER_ENABLED=True)  # off by default in tests
class ChangelogBannerContextTests(TestCase):
    def test_banner_context_when_enabled(self, *_):
        self.assertEqual(
            get_changelog_banner(),
            {
                "version": "3.34.0",
                "release_date": date(2026, 10, 5),
                "url": CHANGELOG_URL,
            },
        )

    @override_config(CHANGELOG_BANNER_ENABLED=False)
    def test_toggle_off_hides_banner(self, *_):
        self.assertIsNone(get_changelog_banner())

    @override_config(CHANGELOG_BANNER_BUSINESS_DAYS=1)
    def test_business_days_setting_is_used(self, *_):
        self.assertIsNone(get_changelog_banner())

    def test_banner_renders_on_unauthenticated_login_page(self, *_):
        response = self.client.get(reverse("users:login"))
        self.assertContains(response, "usa-site-alert--info")
        self.assertContains(response, "See what’s new in version 3.34.0")
        self.assertContains(response, f'href="{CHANGELOG_URL}"')
        self.assertContains(response, 'target="_blank"')
        self.assertContains(response, "(opens in a new tab)")

    @override_config(CHANGELOG_BANNER_ENABLED=False)
    def test_banner_not_rendered_when_toggled_off(self, *_):
        response = self.client.get(reverse("users:login"))
        self.assertNotContains(response, "usa-site-alert--info")


@patch("bloom_nofos.changelog_banner.get_latest_release", return_value=RELEASE)
@freeze_time("2026-10-06 12:00:00")
class ChangelogBannerTestDefaultTests(TestCase):
    def test_off_by_default_while_running_tests(self, _):
        # Keeps every other page-rendering test independent of today's date
        self.assertIsNone(get_changelog_banner())
        response = self.client.get(reverse("users:login"))
        self.assertNotContains(response, "changelog-banner")
