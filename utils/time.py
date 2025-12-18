import calendar
from datetime import date, timedelta

from fastapi import HTTPException

from analytics.models import TimeWindow


def resolve_time(tw: TimeWindow):
    if tw.mode == "rolling":
        days = int(tw.days or 90)
        end = date.today()
        start = end - timedelta(days=days)
        return start.isoformat(), end.isoformat()
    if not tw.start or not tw.end:
        raise HTTPException(
            400, "No modo range, informe time.start e time.end (YYYY-MM-DD)."
        )
    return tw.start, tw.end


def month_end(year: int, month: int) -> date:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, last_day)


def shift_range(end: date, window_days: int):
    start = end - timedelta(days=window_days)
    return start, end
