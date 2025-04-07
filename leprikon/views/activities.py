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

from ..forms.activities import (
    ActivityFilterForm,
    ActivityForm,
    CourseRegistrationForm,
    EventRegistrationForm,
    OrderableRegistrationForm,
)
from ..models.activities import (
    Activity,
    ActivityModel,
    ActivityType,
    ActivityVariant,
    Payment,
    ReceivedPayment,
    Registration,
    ReturnedPayment,
)
from ..models.courses import Course
from ..models.events import Event
from ..models.orderables import Orderable
from ..models.registrationlink import RegistrationLink
from ..utils import reverse_with_back
from .generic import ConfirmUpdateView, CreateView, DetailView, FilteredListView, ListView, UpdateView


class ActivityTypeMixin:
    _models = {
        ActivityModel.COURSE: Course,
        ActivityModel.EVENT: Event,
        ActivityModel.ORDERABLE: Orderable,
    }

    def dispatch(self, request, activity_type, *args, **kwargs):
        self.activity_type = get_object_or_404(ActivityType, slug=activity_type)
        self.model = self._models[self.activity_type.model]
        return super().dispatch(request, *args, **kwargs)

    def get_placeholder(self):
        return super().get_placeholder() + ":" + self.activity_type.slug

    def get_queryset(self):
        return super().get_queryset().filter(activity_type=self.activity_type)

    def get_template_names(self):
        return [
            "leprikon/{}{}.html".format(self.activity_type.slug, self.template_name_suffix),
            "leprikon/{}{}.html".format(self.activity_type.model, self.template_name_suffix),
            "leprikon/activity{}.html".format(self.template_name_suffix),
        ]


class CMSActivityTypeMixin(ActivityTypeMixin):
    def dispatch(self, request, *args, **kwargs):
        # Get current CMS Page
        cms_page = request.current_page.get_public_object()

        # Check whether it really is a Leprikon activity type application.
        # It might also be one of its sub-pages.
        if cms_page.application_urls != "LeprikonActivityTypeApp":
            # In such case show regular CMS Page
            return cms_view_details(request, *args, **kwargs)
        return super().dispatch(request, cms_page.application_namespace, **kwargs)


class ActivityListBaseView(FilteredListView):
    form_class = ActivityFilterForm
    preview_template = "leprikon/activity_preview.html"
    paginate_by = 10

    def get_title(self):
        if self.activity_type.model == ActivityModel.EVENT:
            if self.request.GET.get("past"):
                return _("Past {activity_type} in school year {school_year}").format(
                    activity_type=self.activity_type.plural,
                    school_year=self.request.school_year,
                )
            return _("Oncoming {activity_type}").format(
                activity_type=self.activity_type.plural,
            )
        return _("{activity_type} in school year {school_year}").format(
            activity_type=self.activity_type.plural,
            school_year=self.request.school_year,
        )

    def get_message_empty(self):
        return _("No {activity_type} matching given search parameters found.").format(
            activity_type=self.activity_type.plural,
        )

    def get_form(self):
        return self.form_class(
            activity_type_model=self.activity_type.model,
            activity_types=[self.activity_type],
            school_year=self.request.school_year,
            is_staff=self.request.user.is_staff,
            data=self.request.GET,
        )


class ActivityListView(CMSActivityTypeMixin, ActivityListBaseView):
    pass


class ActivityListMineView(ActivityTypeMixin, ActivityListBaseView):
    def get_template_names(self):
        return [
            "leprikon/{}_list_mine.html".format(self.activity_type.slug),
            "leprikon/{}_list_mine.html".format(self.activity_type.model),
            "leprikon/activity_list_mine.html",
        ] + super().get_template_names()

    def get_title(self):
        return _("My {activity_type} in school year {school_year}").format(
            activity_type=self.activity_type.plural,
            school_year=self.request.school_year,
        )

    def get_queryset(self):
        return super().get_queryset().filter(leaders=self.request.leader)


class ActivityDetailView(CMSActivityTypeMixin, DetailView):
    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(public=True)
        return qs


class ActivityJournalsView(ActivityTypeMixin, DetailView):
    template_name_suffix = "_journals"

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(leaders=self.request.leader)
        return qs

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            add_label=_("Create journal"),
            add_url=reverse_with_back(self.request, "leprikon:journal_create", kwargs={"activity": self.object.id}),
            preview_template="leprikon/journal_preview.html",
            message_empty=_("No journals matching given search parameters found."),
            **kwargs,
        )

    def get_title(self):
        return _("Journals of {activity_type} {activity}").format(
            activity_type=self.activity_type.name_genitiv,
            activity=self.object.display_name,
        )


class ActivityRegistrationsView(ActivityTypeMixin, DetailView):
    template_name_suffix = "_registrations"

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(leaders=self.request.leader)
        return qs


class ActivityUpdateView(ActivityTypeMixin, UpdateView):
    form_class = ActivityForm

    def get_title(self):
        return _("Change {activity_type} {activity}").format(
            activity_type=self.activity_type.name_akuzativ,
            activity=self.object.name,
        )

    def get_message(self):
        return _("The changes in {activity_type} {activity} have been saved.").format(
            activity_type=self.activity_type.name_genitiv,
            activity=self.object.name,
        )

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(leaders=self.request.leader)
        return qs


class ActivityMixin:
    def dispatch(self, request, pk, **kwargs):
        lookup_kwargs = {"activity_type": self.activity_type, "id": int(pk)}
        if not self.request.user.is_staff:
            lookup_kwargs["public"] = True
        self.activity = get_object_or_404(Activity, **lookup_kwargs)
        if not self.activity.registration_allowed:
            return redirect(self.activity)
        self.request.school_year = self.activity.school_year
        return super().dispatch(request, **kwargs)


class RegistrationFormBaseView(CreateView):
    activity: Activity
    activity_variant: Optional[ActivityVariant]
    registration_link: Optional[RegistrationLink] = None
    available_variants: List[ActivityVariant]

    back_url = reverse("leprikon:registration_list")
    submit_label = _("Submit registration")
    message = _("The registration has been saved. We will inform you about its further processing.")
    template_name_suffix = "_registration_form"
    _form_classes = {
        ActivityModel.COURSE: CourseRegistrationForm,
        ActivityModel.EVENT: EventRegistrationForm,
        ActivityModel.ORDERABLE: OrderableRegistrationForm,
    }

    def dispatch(self, request, **kwargs):
        activity_variant_pk: Optional[int] = kwargs.pop("variant_pk", None)
        if self.registration_link:
            self.available_variants = list(self.registration_link.activity_variants.filter(activity=self.activity))
        else:
            self.available_variants = self.activity.all_available_variants
        try:
            self.activity_variant = (
                activity_variant_pk and [v for v in self.available_variants if v.pk == int(activity_variant_pk)][0]
            )
        except (IndexError, ValueError):
            self.activity_variant = None
        if self.activity_variant is None and len(self.available_variants) == 1:
            self.activity_variant = self.available_variants[0]
        return super().dispatch(request, **kwargs)

    def get_title(self):
        return _("Registration for {activity_type} {activity}").format(
            activity_type=self.activity_type.name_akuzativ,
            activity=self.activity.name,
        )

    def get_form_class(self):
        return self._form_classes[self.activity_type.model] if self.activity_variant else Form

    def get_form_kwargs(self):
        if self.activity_variant:
            kwargs = super().get_form_kwargs()
            kwargs["activity"] = self.activity
            kwargs["activity_variant"] = self.activity_variant
            kwargs["user"] = self.request.user
            return kwargs
        else:
            return {}


class RegistrationFormView(CMSActivityTypeMixin, ActivityMixin, RegistrationFormBaseView):
    pass


class UserRegistrationMixin:
    allow_leader_or_staff = False
    _attrs = {
        ActivityModel.COURSE: "courseregistration",
        ActivityModel.EVENT: "eventregistration",
        ActivityModel.ORDERABLE: "orderableregistration",
    }

    def get_object(self):
        registration = super().get_object()
        if self.request.user == registration.user or (
            self.allow_leader_or_staff
            and (self.request.user.is_staff or self.request.leader in registration.activity.all_leaders)
        ):
            return getattr(
                registration,
                self._attrs[registration.activity_type_model],
            )
        raise PermissionDenied()

    def get_queryset(self):
        return Registration.objects.annotate(
            activity_type_model=F("activity__activity_type__model"),
        )

    def get_template_names(self):
        return (
            [self.template_name]
            if self.template_name
            else [
                "leprikon/{}_registration{}.html".format(
                    self.object.activity.activity_type.slug, self.template_name_suffix
                ),
                "leprikon/{}_registration{}.html".format(
                    self.object.activity.activity_type.model, self.template_name_suffix
                ),
                "leprikon/registration{}.html".format(self.template_name_suffix),
            ]
        )


class PDFMixin:
    event = "pdf"

    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="{}"'.format(obj.get_pdf_filename(self.event))
        return obj.write_pdf(self.event, response)


class RegistrationPdfView(PDFMixin, UserRegistrationMixin, DetailView):
    pass


class RegistrationPaymentRequestView(PDFMixin, UserRegistrationMixin, DetailView):
    allow_leader_or_staff = True
    event = "payment_request"


class RegistrationCancelView(UserRegistrationMixin, ConfirmUpdateView):
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


class PaymentsListView(ListView):
    model = Payment
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


class ReceivedPaymentPdfView(PDFMixin, DetailView):
    model = ReceivedPayment

    def get_queryset(self):
        return super().get_queryset().filter(target_registration__user=self.request.user)


class ReturnedPaymentPdfView(PDFMixin, DetailView):
    model = ReturnedPayment

    def get_queryset(self):
        return super().get_queryset().filter(source_registration__user=self.request.user)
