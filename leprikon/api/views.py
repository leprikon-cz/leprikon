from datetime import datetime

from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from ..models.subjects import Subject
from ..views import leader_or_staff_required


@leader_or_staff_required
def registrations(request, subject_id):
    qs = Subject.objects.all()
    if not request.user.is_staff:
        qs = qs.filter(leaders=request.leader)
    subject = get_object_or_404(qs, id=subject_id)

    try:
        d = datetime.fromtimestamp(int(request.GET['date']))
    except:
        d = None

    return JsonResponse({
        'registrations': list({'value': r.id, 'label': str(r)} for r in subject.subject.get_approved_registrations(d)),
    })
