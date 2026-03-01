from __future__ import annotations

from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncHour
from django.utils import timezone

from voting_system.apps.ballots.models import Ballot
from voting_system.apps.tokens.models import Token, TokenStatus


def election_summary(election):
    total_tokens = Token.objects.filter(election=election).count()
    used_tokens = Token.objects.filter(election=election, status=TokenStatus.USED).count()
    ballots_submitted = Ballot.objects.filter(election=election).count()
    turnout_percentage = (used_tokens / total_tokens * 100) if total_tokens else 0
    return {
        "tokens_generated": total_tokens,
        "tokens_used": used_tokens,
        "turnout_percentage": round(turnout_percentage, 2),
        "ballots_submitted": ballots_submitted,
    }


def election_turnout_timeseries(election, hours: int = 72):
    now = timezone.now()
    start = now - timedelta(hours=hours)
    start = start.replace(minute=0, second=0, microsecond=0)
    end = now.replace(minute=0, second=0, microsecond=0)
    rows = (
        Ballot.objects.filter(election=election, submitted_at__gte=start)
        .annotate(hour=TruncHour("submitted_at"))
        .values("hour")
        .annotate(count=Count("id"))
        .order_by("hour")
    )
    counts = {row["hour"]: row["count"] for row in rows}

    series = []
    cursor = start
    while cursor <= end:
        series.append({"day": cursor.isoformat(), "count": counts.get(cursor, 0)})
        cursor += timedelta(hours=1)
    return series
