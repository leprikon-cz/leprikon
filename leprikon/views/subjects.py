from typing import List, Optional

from cms.views import details as cms_view_details
from django.core.exceptions import PermissionDenied
from django.db.models import F, Q
from django.forms import Form
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy as reverse
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from ..forms.subjects import (
    CourseRegistrationForm,
    EventRegistrationForm,
    OrderableRegistrationForm,
    SubjectFilterForm,
    SubjectForm,
)
from ..models.courses import Course
from ..models.events import Event
from ..models.orderables import Orderable
from ..models.registrationlink import RegistrationLink
from ..models.subjects import (
    Subject,
    SubjectPayment,
    SubjectReceivedPayment,
    SubjectRegistration,
    SubjectReturnedPayment,
    SubjectType,
    SubjectVariant,
)
from ..utils import reverse_with_back
from .generic import ConfirmUpdateView, CreateView, DetailView, FilteredListView, ListView, UpdateView


class SubjectTypeMixin:
    _models = {
        SubjectType.COURSE: Course,
        SubjectType.EVENT: Event,
        SubjectType.ORDERABLE: Orderable,
    }

    def dispatch(self, request, subject_type, *args, **kwargs):
        self.subject_type = get_object_or_404(SubjectType, slug=subject_type)
        self.model = self._models[self.subject_type.subject_type]
        return super().dispatch(request, *args, **kwargs)

    def get_placeholder(self):
        return super().get_placeholder() + ":" + self.subject_type.slug

    def get_queryset(self):
        return super().get_queryset().filter(subject_type=self.subject_type)

    def get_template_names(self):
        return [
            "leprikon/{}{}.html".format(self.subject_type.slug, self.template_name_suffix),
            "leprikon/{}{}.html".format(self.subject_type.subject_type, self.template_name_suffix),
            "leprikon/subject{}.html".format(self.template_name_suffix),
        ]


class CMSSubjectTypeMixin(SubjectTypeMixin):
    def dispatch(self, request, *args, **kwargs):
        # Get current CMS Page
        cms_page = request.current_page.get_public_object()

        # Check whether it really is a Leprikon subject type application.
        # It might also be one of its sub-pages.
        if cms_page.application_urls != "LeprikonSubjectTypeApp":
            # In such case show regular CMS Page
            return cms_view_details(request, *args, **kwargs)
        return super().dispatch(request, cms_page.application_namespace, **kwargs)


class SubjectListBaseView(FilteredListView):
    form_class = SubjectFilterForm
    preview_template = "leprikon/subject_preview.html"
    paginate_by = 10

    def get_title(self):
        if self.subject_type.subject_type == SubjectType.EVENT:
            if self.request.GET.get("past"):
                return _("Past {subject_type} in school year {school_year}").format(
                    subject_type=self.subject_type.plural,
                    school_year=self.request.school_year,
                )
            return _("Oncoming {subject_type}").format(
                subject_type=self.subject_type.plural,
            )
        return _("{subject_type} in school year {school_year}").format(
            subject_type=self.subject_type.plural,
            school_year=self.request.school_year,
        )

    def get_message_empty(self):
        return _("No {subject_type} matching given search parameters found.").format(
            subject_type=self.subject_type.plural,
        )

    def get_form(self):
        return self.form_class(
            subject_type_type=self.subject_type.subject_type,
            subject_types=[self.subject_type],
            school_year=self.request.school_year,
            is_staff=self.request.user.is_staff,
            data=self.request.GET,
        )


class SubjectListView(CMSSubjectTypeMixin, SubjectListBaseView):
    pass


class SubjectListMineView(SubjectTypeMixin, SubjectListBaseView):
    def get_template_names(self):
        return [
            "leprikon/{}_list_mine.html".format(self.subject_type.slug),
            "leprikon/{}_list_mine.html".format(self.subject_type.subject_type),
            "leprikon/subject_list_mine.html",
        ] + super().get_template_names()

    def get_title(self):
        return _("My {subject_type} in school year {school_year}").format(
            subject_type=self.subject_type.plural,
            school_year=self.request.school_year,
        )

    def get_queryset(self):
        return super().get_queryset().filter(leaders=self.request.leader)


class SubjectDetailView(CMSSubjectTypeMixin, DetailView):
    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(public=True)
        return qs


class SubjectJournalsView(SubjectTypeMixin, DetailView):
    template_name_suffix = "_journals"

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(leaders=self.request.leader)
        return qs

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            add_label=_("Create journal"),
            add_url=reverse_with_back(self.request, "leprikon:journal_create", kwargs={"subject": self.object.id}),
            preview_template="leprikon/journal_preview.html",
            message_empty=_("No journals matching given search parameters found."),
            **kwargs,
        )

    def get_title(self):
        return _("Journals of {subject_type} {subject}").format(
            subject_type=self.subject_type.name_genitiv,
            subject=self.object.display_name,
        )


class SubjectRegistrationsView(SubjectTypeMixin, DetailView):
    template_name_suffix = "_registrations"

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(leaders=self.request.leader)
        return qs


class SubjectUpdateView(SubjectTypeMixin, UpdateView):
    form_class = SubjectForm

    def get_title(self):
        return _("Change {subject_type} {subject}").format(
            subject_type=self.subject_type.name_akuzativ,
            subject=self.object.name,
        )

    def get_message(self):
        return _("The changes in {subject_type} {subject} have been saved.").format(
            subject_type=self.subject_type.name_genitiv,
            subject=self.object.name,
        )

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(leaders=self.request.leader)
        return qs


class SubjectMixin:
    def dispatch(self, request, pk, **kwargs):
        lookup_kwargs = {"subject_type": self.subject_type, "id": int(pk)}
        if not self.request.user.is_staff:
            lookup_kwargs["public"] = True
        self.subject = get_object_or_404(Subject, **lookup_kwargs)
        if not self.subject.registration_allowed:
            return redirect(self.subject)
        self.request.school_year = self.subject.school_year
        return super().dispatch(request, **kwargs)


class SubjectRegistrationFormBaseView(CreateView):
    subject: Subject
    subject_variant: Optional[SubjectVariant]
    registration_link: Optional[RegistrationLink] = None
    available_variants: List[SubjectVariant]

    back_url = reverse("leprikon:registration_list")
    submit_label = _("Submit registration")
    message = _("The registration has been saved. We will inform you about its further processing.")
    template_name_suffix = "_registration_form"
    _form_classes = {
        SubjectType.COURSE: CourseRegistrationForm,
        SubjectType.EVENT: EventRegistrationForm,
        SubjectType.ORDERABLE: OrderableRegistrationForm,
    }

    def dispatch(self, request, **kwargs):
        subject_variant_pk: Optional[int] = kwargs.pop("variant_pk", None)
        if self.registration_link:
            self.available_variants = list(self.registration_link.subject_variants.filter(subject=self.subject))
        else:
            self.available_variants = self.subject.all_available_variants
        try:
            self.subject_variant = (
                subject_variant_pk and [v for v in self.available_variants if v.pk == int(subject_variant_pk)][0]
            )
        except (IndexError, ValueError):
            self.subject_variant = None
        if self.subject_variant is None and len(self.available_variants) == 1:
            self.subject_variant = self.available_variants[0]
        return super().dispatch(request, **kwargs)

    def get_title(self):
        return _("Registration for {subject_type} {subject}").format(
            subject_type=self.subject_type.name_akuzativ,
            subject=self.subject.name,
        )

    def get_form_class(self):
        return self._form_classes[self.subject_type.subject_type] if self.subject_variant else Form

    def get_form_kwargs(self):
        if self.subject_variant:
            kwargs = super().get_form_kwargs()
            kwargs["subject"] = self.subject
            kwargs["subject_variant"] = self.subject_variant
            kwargs["user"] = self.request.user
            return kwargs
        else:
            return {}


class SubjectRegistrationFormView(CMSSubjectTypeMixin, SubjectMixin, SubjectRegistrationFormBaseView):
    pass


class UserRegistrationMixin:
    allow_leader_or_staff = False
    _attrs = {
        SubjectType.COURSE: "courseregistration",
        SubjectType.EVENT: "eventregistration",
        SubjectType.ORDERABLE: "orderableregistration",
    }

    def get_object(self):
        subject_registration = super().get_object()
        if self.request.user == subject_registration.user or (
            self.allow_leader_or_staff
            and (self.request.user.is_staff or self.request.leader in subject_registration.subject.all_leaders)
        ):
            return getattr(
                subject_registration,
                self._attrs[subject_registration.subject_type_type],
            )
        raise PermissionDenied()

    def get_queryset(self):
        return SubjectRegistration.objects.annotate(
            subject_type_type=F("subject__subject_type__subject_type"),
        )

    def get_template_names(self):
        return (
            [self.template_name]
            if self.template_name
            else [
                "leprikon/{}_registration{}.html".format(
                    self.object.subject.subject_type.slug, self.template_name_suffix
                ),
                "leprikon/{}_registration{}.html".format(
                    self.object.subject.subject_type.subject_type, self.template_name_suffix
                ),
                "leprikon/subject_registration{}.html".format(self.template_name_suffix),
            ]
        )


class PDFMixin:
    event = "pdf"

    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="{}"'.format(obj.get_pdf_filename(self.event))
        return obj.write_pdf(self.event, response)


class SubjectRegistrationPdfView(PDFMixin, UserRegistrationMixin, DetailView):
    pass


class SubjectRegistrationPaymentRequestView(PDFMixin, UserRegistrationMixin, DetailView):
    allow_leader_or_staff = True
    event = "payment_request"


class SubjectRegistrationCancelView(UserRegistrationMixin, ConfirmUpdateView):
    template_name_suffix = "_cancel"
    title = _("Registration cancellation request")

    def get_queryset(self):
        return super().get_queryset().filter(canceled=None)

    def get_question(self):
        return _('Are you sure You want to cancel the registration "{}"?').format(self.object)

    def get_message(self):
        return _("The cancellation request for {} has been saved.").format(self.object)

    def confirmed(self):
        if self.object.approved:
            self.object.cancelation_requested = now()
            self.object.cancelation_requested_by = self.request.user
            self.object.save()
        else:
            self.object.refuse(self.request.user)


class SubjectPaymentsListView(ListView):
    model = SubjectPayment
    template_name = "leprikon/payments.html"
    paginate_by = 20

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(Q(target_registration__user=self.request.user) | Q(source_registration__user=self.request.user))
            .order_by("-accounted")
        )

    def get_title(self):
        return _("Payments")


class SubjectReceivedPaymentPdfView(PDFMixin, DetailView):
    model = SubjectReceivedPayment

    def get_queryset(self):
        return super().get_queryset().filter(target_registration__user=self.request.user)


class SubjectReturnedPaymentPdfView(PDFMixin, DetailView):
    model = SubjectReturnedPayment

    def get_queryset(self):
        return super().get_queryset().filter(source_registration__user=self.request.user)
