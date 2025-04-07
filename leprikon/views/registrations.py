from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from ..forms.activities import RegistrationsFilterForm
from ..models.activities import Registration
from .generic import FilteredListView


class RegistrationsListView(FilteredListView):
    form_class = RegistrationsFilterForm
    message_empty = _("You don't have any registrations yet.")
    paginate_by = 10
    preview_template = "leprikon/registration_preview_object.html"
    title = _("My registrations")

    def get_queryset(self):
        qs = Registration.objects.filter(
            user=self.request.user,
        ).order_by("-created")
        if not self.form.is_valid():
            return qs
        if self.form.cleaned_data.get("activity_types"):
            qs = qs.filter(activity__activity_type__in=self.form.cleaned_data["activity_types"])
        if self.form.cleaned_data.get("q"):
            for word in self.form.cleaned_data["q"].split():
                qs = qs.filter(Q(activity__name__icontains=word) | Q(activity__description__icontains=word))
        qs = qs.distinct()
        if self.form.cleaned_data.get("not_paid"):
            qs = [reg for reg in qs if reg.payment_status.amount_due]
        return qs
