import datetime

from app.features.day_boundary import noon_to_noon_range


class TestNoonToNoonRange:
    def test_basic_date(self):
        start, end = noon_to_noon_range(datetime.date(2025, 1, 15))
        assert start == datetime.datetime(2025, 1, 14, 12, 0)
        assert end == datetime.datetime(2025, 1, 15, 12, 0)

    def test_first_of_month(self):
        start, end = noon_to_noon_range(datetime.date(2025, 3, 1))
        assert start == datetime.datetime(2025, 2, 28, 12, 0)
        assert end == datetime.datetime(2025, 3, 1, 12, 0)

    def test_leap_year(self):
        start, end = noon_to_noon_range(datetime.date(2024, 3, 1))
        assert start == datetime.datetime(2024, 2, 29, 12, 0)
        assert end == datetime.datetime(2024, 3, 1, 12, 0)

    def test_new_year(self):
        start, end = noon_to_noon_range(datetime.date(2025, 1, 1))
        assert start == datetime.datetime(2024, 12, 31, 12, 0)
        assert end == datetime.datetime(2025, 1, 1, 12, 0)

    def test_window_is_24_hours(self):
        start, end = noon_to_noon_range(datetime.date(2025, 6, 15))
        assert (end - start) == datetime.timedelta(hours=24)
