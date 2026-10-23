from datetime import datetime, timedelta, timezone


class FakeClock:
    def __init__(self):
        self.current = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def now(self):
        return self.current

    def advance(self, minutes: int):
        self.current += timedelta(minutes=minutes)
