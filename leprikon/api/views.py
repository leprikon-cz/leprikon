from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from datetime import datetime
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _

from ..models import Club
from ..views import login_required, leader_required, leader_or_staff_required, staff_required


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

    return JsonResponse({'registrations': list({'value': r.id, 'label': str(r)} for r in club.get_registrations(d))})

