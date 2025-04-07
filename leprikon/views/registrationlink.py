from django.shortcuts import get_object_or_404, redirect

from ..models.activities import Activity
from ..models.registrationlink import RegistrationLink
from .activities import ActivityListBaseView, ActivityTypeMixin, RegistrationFormBaseView


class RegistrationLinkMixin(ActivityTypeMixin):
    def dispatch(self, request, registration_link, *args, **kwargs):
        self.registration_link = get_object_or_404(RegistrationLink, slug=registration_link)
        self.activity_type = self.registration_link.activity_type
        self.model = self._models[self.activity_type.model]
        return super(ActivityTypeMixin, self).dispatch(request, *args, **kwargs)

    def get_placeholder(self):
        return super().get_placeholder() + ":" + self.activity_type.slug

    def get_queryset(self):
        return super().get_queryset().filter(id__in=self.registration_link.activity_variants.values("activity_id"))

    def get_template_names(self):
        return [
            "leprikon/{}{}.html".format(self.activity_type.slug, self.template_name_suffix),
            "leprikon/{}{}.html".format(self.activity_type.model, self.template_name_suffix),
            "leprikon/activity{}.html".format(self.template_name_suffix),
        ]


class RegistrationLinkView(RegistrationLinkMixin, ActivityListBaseView):
    pass


class ActivityMixin:
    registration_link: RegistrationLink

    def dispatch(self, request, pk, **kwargs):
        lookup_kwargs = {"activity_type_id": self.registration_link.activity_type_id, "id": int(pk)}
        if not self.request.user.is_staff:
            lookup_kwargs["public"] = True
        self.activity = get_object_or_404(Activity, **lookup_kwargs)
        if not self.registration_link.registration_allowed:
            return redirect(self.activity)
        self.request.school_year = self.activity.school_year
        return super().dispatch(request, **kwargs)


class RegistrationLinkFormView(RegistrationLinkMixin, ActivityMixin, RegistrationFormBaseView):
    def form_valid(self, form):
        response = super().form_valid(form)
        self.object.registration_link = self.registration_link
        self.object.save()
        return response
