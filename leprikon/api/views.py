from __future__ import unicode_literals

from datetime import datetime

from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from ..models.clubs import Club
from ..views import leader_or_staff_required


@leader_or_staff_required
def club_registrations(request, club_id):
    qs = Club.objects.all()
    if not request.user.is_staff:
        qs = qs.filter(leaders=request.leader)
    club = get_object_or_404(qs, id=club_id)

    try:
        d = datetime.fromtimestamp(int(request.GET['date']))
    except:
        d = None

    return JsonResponse({'registrations': list({'value': r.id, 'label': str(r)} for r in club.get_active_registrations(d))})

