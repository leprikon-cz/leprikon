from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from ..forms.subjects import RegistrationsFilterForm
from ..models.subjects import SubjectRegistration
from .generic import FilteredListView


class RegistrationsListView(FilteredListView):
    form_class = RegistrationsFilterForm
    message_empty = _("You don't have any registrations yet.")
    paginate_by = 10
    preview_template = "leprikon/registration_preview_object.html"
    title = _("My registrations")

    def get_queryset(self):
        qs = SubjectRegistration.objects.filter(
            user=self.request.user,
        ).order_by("-created")
        if not self.form.is_valid():
            return qs
        if self.form.cleaned_data.get("subject_types"):
            qs = qs.filter(subject__subject_type__in=self.form.cleaned_data["subject_types"])
        if self.form.cleaned_data.get("q"):
            for word in self.form.cleaned_data["q"].split():
                qs = qs.filter(Q(subject__name__icontains=word) | Q(subject__description__icontains=word))
        qs = qs.distinct()
        if self.form.cleaned_data.get("not_paid"):
            qs = [reg for reg in qs if reg.payment_status.amount_due]
        return qs
