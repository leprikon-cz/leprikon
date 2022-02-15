from datetime import date, datetime

import pytz
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.timezone import localdate

from ..models.journals import Journal
from ..views import leader_or_staff_required


@leader_or_staff_required
def participants(request, journal_id):
    qs = Journal.objects.all()
    if not request.user.is_staff:
        qs = qs.filter(leaders=request.leader)
    journal = get_object_or_404(qs, id=journal_id)

    try:
        d = localdate(datetime.utcfromtimestamp(int(request.GET["date"])).replace(tzinfo=pytz.utc))
    except (KeyError, ValueError):
        d = date.today()

    return JsonResponse(
        {
            "participants": list({"value": p.id, "label": str(p)} for p in journal.get_valid_participants(d)),
        }
    )
