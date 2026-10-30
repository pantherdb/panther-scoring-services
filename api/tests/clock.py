from datetime import UTC, datetime, timedelta


class Clock:
    """A clock that only moves when a test moves it.

    Patch `panther_api.jobs.store.utcnow` with it, where every job timestamp comes from.
    """

    def __init__(self) -> None:
        self.now = datetime(2026, 10, 29, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, delta: timedelta) -> None:
        self.now += delta
