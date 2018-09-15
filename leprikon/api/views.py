from datetime import datetime

from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from ..models.courses import Course
from ..views import leader_or_staff_required


@leader_or_staff_required
def course_registrations(request, course_id):
    qs = Course.objects.all()
    if not request.user.is_staff:
        qs = qs.filter(leaders=request.leader)
    course = get_object_or_404(qs, id=course_id)

    try:
        d = datetime.fromtimestamp(int(request.GET['date']))
    except:
        d = None

    return JsonResponse({
        'registrations': list({'value': r.id, 'label': str(r)} for r in course.get_approved_registrations(d)),
    })
