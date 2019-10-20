from datetime import date, datetime

import pytz
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.timezone import localdate

from ..models.subjects import Subject
from ..views import leader_or_staff_required


@leader_or_staff_required
def participants(request, subject_id):
    qs = Subject.objects.all()
    if not request.user.is_staff:
        qs = qs.filter(leaders=request.leader)
    subject = get_object_or_404(qs, id=subject_id)

    try:
        d = localdate(datetime.utcfromtimestamp(int(request.GET['date'])).replace(tzinfo=pytz.utc))
    except (KeyError, ValueError):
        d = date.today()

    return JsonResponse({
        'participants': list(
            {'value': p.id, 'label': str(p)}
            for p in subject.get_valid_participants(d)
        ),
    })
