"""Protect refreshes against replacing real activity with incomplete data."""
import unittest
from datetime import date, timedelta
from profile_art import ContributionParser, summarize

def calendar(count="No", missing_tip=False):
    start = date(2025, 1, 1)
    return "".join(
        f'<td id="d{i}" data-date="{start+timedelta(days=i)}" data-level="0"></td>'
        + ("" if missing_tip and i == 0 else f'<tool-tip for="d{i}">{count} contributions on a date.</tool-tip>')
        for i in range(365))

class CalendarTests(unittest.TestCase):
    def parse(self, markup):
        parser = ContributionParser()
        parser.feed(markup)
        return parser.days()

    def test_tooltip_counts_and_sorted_days(self):
        days = self.parse(calendar("1,234"))
        self.assertEqual(len(days), 365)
        self.assertEqual(days[0]["count"], 1234)
        self.assertEqual(days[-1]["date"], "2025-12-31")

    def test_unknown_markup_fails_instead_of_zeroing_activity(self):
        with self.assertRaises(ValueError):
            self.parse(calendar(missing_tip=True))
        with self.assertRaises(ValueError):
            self.parse("<html>Rate limited</html>")

    def test_missing_calendar_day_fails(self):
        with self.assertRaises(ValueError):
            self.parse(calendar().replace('data-date="2025-01-02"', 'data-date="2025-01-03"'))

    def test_streak_does_not_end_before_today_is_over(self):
        stats = summarize([{"count": n} for n in [1, 1, 1, 0, 4, 2, 0]])
        self.assertEqual(stats, {"total": 9, "active_days": 5, "longest_streak": 3, "current_streak": 2})

if __name__ == "__main__":
    unittest.main()
