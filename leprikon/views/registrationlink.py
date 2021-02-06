from django.shortcuts import get_object_or_404, redirect

from ..models.registrationlink import RegistrationLink
from ..models.subjects import Subject
from .subjects import SubjectListBaseView, SubjectRegistrationFormBaseView, SubjectTypeMixin


class RegistrationLinkMixin(SubjectTypeMixin):
    def dispatch(self, request, registration_link, *args, **kwargs):
        self.registration_link = get_object_or_404(RegistrationLink, slug=registration_link)
        self.subject_type = self.registration_link.subject_type
        self.model = self._models[self.subject_type.subject_type]
        return super(SubjectTypeMixin, self).dispatch(request, *args, **kwargs)

    def get_placeholder(self):
        return super().get_placeholder() + ":" + self.subject_type.slug

    def get_queryset(self):
        return super().get_queryset().filter(registration_links=self.registration_link)

    def get_template_names(self):
        return [
            "leprikon/{}{}.html".format(self.subject_type.slug, self.template_name_suffix),
            "leprikon/{}{}.html".format(self.subject_type.subject_type, self.template_name_suffix),
            "leprikon/subject{}.html".format(self.template_name_suffix),
        ]


class RegistrationLinkView(RegistrationLinkMixin, SubjectListBaseView):
    pass


class SubjectMixin:
    def dispatch(self, request, pk, **kwargs):
        lookup_kwargs = {"subject_type_id": self.registration_link.subject_type_id, "id": int(pk)}
        if not self.request.user.is_staff:
            lookup_kwargs["public"] = True
        self.subject = get_object_or_404(Subject, **lookup_kwargs)
        if not self.registration_link.registration_allowed:
            return redirect(self.subject)
        self.request.school_year = self.subject.school_year
        return super().dispatch(request, **kwargs)


class RegistrationLinkFormView(RegistrationLinkMixin, SubjectMixin, SubjectRegistrationFormBaseView):
    def form_valid(self, form):
        response = super().form_valid(form)
        self.object.registration_link = self.registration_link
        self.object.save()
        return response
