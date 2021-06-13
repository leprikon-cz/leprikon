from django import forms
from django.conf.urls import url as urls_url
from django.contrib import admin, messages
from django.contrib.admin.templatetags.admin_list import _boolean_icon
from django.contrib.admin.utils import unquote
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.core.exceptions import ValidationError
from django.db.models import BooleanField, Func
from django.db.models.expressions import Random
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.formats import date_format
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.timezone import localtime
from django.utils.translation import ugettext_lazy as _

from ..forms.subjects import (
    RegistrationAdminForm,
    RegistrationGroupAdminForm,
    RegistrationParticipantAdminForm,
    SubjectAdminForm,
)
from ..models.subjects import (
    CHAT_GROUP_TYPE_LABELS,
    DEFAULT_TEXTS,
    Subject,
    SubjectAttachment,
    SubjectGroup,
    SubjectReceivedPayment,
    SubjectRegistration,
    SubjectRegistrationBillingInfo,
    SubjectRegistrationGroup,
    SubjectRegistrationGroupMember,
    SubjectRegistrationParticipant,
    SubjectReturnedPayment,
    SubjectType,
    SubjectTypeAttachment,
    SubjectVariant,
)
from ..models.utils import lazy_help_text_with_default, lazy_help_text_with_html_default
from ..utils import amount_color, currency
from .bulkupdate import BulkUpdateMixin
from .export import AdminExportMixin
from .filters import (
    ApprovedListFilter,
    CanceledListFilter,
    IsNullFieldListFilter,
    LeaderListFilter,
    SchoolYearListFilter,
    SubjectGroupListFilter,
    SubjectListFilter,
    SubjectTypeListFilter,
)
from .messages import SendMessageAdminMixin
from .sendmail import SendMailAdminMixin
from .transaction import TransactionAdminMixin, TransactionBaseAdmin, TransactionTypeListFilter
from .utils import datetime_with_by


class IsNull(Func):
    _output_field = BooleanField()
    arity = 1
    template = "%(expressions)s IS NULL"


class SubjectTypeAttachmentInlineAdmin(admin.TabularInline):
    model = SubjectTypeAttachment
    extra = 0


@admin.register(SubjectType)
class SubjectTypeAdmin(BulkUpdateMixin, admin.ModelAdmin):
    bulk_update_exclude = (
        "subject_type",
        "slug",
        "order",
        "name",
        "plural",
        "name_genitiv",
        "name_akuzativ",
    )
    list_display = ("plural", "order")
    list_editable = ("order",)
    exclude = ("order",)
    filter_horizontal = ("questions", "registration_agreements")
    prepopulated_fields = {"slug": ("plural",)}
    inlines = (SubjectTypeAttachmentInlineAdmin,)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        # limit choices of registration agreements
        registration_agreements_choices = form.base_fields["registration_agreements"].widget.widget.choices
        registration_agreements_choices.queryset = registration_agreements_choices.queryset.exclude(
            id__in=request.leprikon_site.registration_agreements.values("id")
        )
        form.base_fields["registration_agreements"].choices = registration_agreements_choices

        return form


@admin.register(SubjectGroup)
class SubjectGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "color", "order")
    list_editable = ("color", "order")
    filter_horizontal = ("subject_types",)


class SubjectAttachmentInlineAdmin(admin.TabularInline):
    model = SubjectAttachment
    extra = 0


class SubjectVariantInlineAdmin(admin.TabularInline):
    model = SubjectVariant
    extra = 0


class SubjectBaseAdmin(AdminExportMixin, BulkUpdateMixin, SendMessageAdminMixin, admin.ModelAdmin):
    registration_model = None
    list_editable = ("public", "note")
    list_filter = (
        ("school_year", SchoolYearListFilter),
        "department",
        ("subject_type", SubjectTypeListFilter),
        ("groups", SubjectGroupListFilter),
        ("leaders", LeaderListFilter),
        "place",
    )
    inlines = (
        SubjectVariantInlineAdmin,
        SubjectAttachmentInlineAdmin,
    )
    filter_horizontal = ("age_groups", "target_groups", "groups", "leaders", "questions", "registration_agreements")
    actions = ("set_registration_dates",)
    search_fields = ("name", "description")
    save_as = True

    @property
    def media(self):
        m = super().media
        m.add_js(["leprikon/js/Popup.js"])
        return m

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        if not object_id and request.method == "POST" and len(request.POST) == 4:
            return HttpResponseRedirect(
                "{}?subject_type={}&registration_type={}".format(
                    request.path,
                    request.POST.get("subject_type", ""),
                    request.POST.get("registration_type", ""),
                )
            )
        else:
            return super().changeform_view(request, object_id, form_url, extra_context)

    def get_exclude(self, request, obj=None):
        if request.registration_type == Subject.PARTICIPANTS:
            exclude = ["target_groups", "min_group_members_count", "max_group_members_count"]
        elif request.registration_type == Subject.GROUPS:
            exclude = ["age_groups", "min_participants_count", "max_participants_count"]
        else:
            exclude = []
        if obj and obj.registrations.exists():
            exclude.append("registration_type")
        return exclude

    def get_form(self, request, obj, **kwargs):
        # set school year
        if obj:
            request.school_year = obj.school_year

        # get subject type
        try:
            # first try request.POST (user may want to change subject type)
            request.subject_type = SubjectType.objects.get(id=int(request.POST.get("subject_type")))
        except (SubjectType.DoesNotExist, TypeError, ValueError):
            if obj:
                # use subject type from object
                request.subject_type = obj.subject_type
            else:
                # try to get subject type from request.GET
                try:
                    request.subject_type = SubjectType.objects.get(
                        id=int(request.GET.get("subject_type")),
                    )
                except (SubjectType.DoesNotExist, TypeError, ValueError):
                    request.subject_type = None

        # get registration type
        request.registration_type = request.POST.get("registration_type")
        if request.registration_type not in Subject.REGISTRATION_TYPES:
            if obj:
                # use registration type from object
                request.registration_type = obj.registration_type
            else:
                # try to get registration type from request.GET
                request.registration_type = request.GET.get("registration_type")
                if request.registration_type not in Subject.REGISTRATION_TYPES:
                    request.registration_type = None

        if request.subject_type and request.registration_type:
            kwargs["form"] = type(
                SubjectAdminForm.__name__,
                (SubjectAdminForm,),
                {
                    "school_year": request.school_year,
                    "subject_type": request.subject_type,
                    "registration_type": request.registration_type,
                },
            )
        else:
            kwargs["fields"] = ["subject_type", "registration_type"]
            request.hide_inlines = True

        form = super().get_form(request, obj, **kwargs)

        if request.subject_type and request.registration_type:
            for field_name in [
                "text_registration_received",
                "text_registration_approved",
                "text_registration_refused",
                "text_registration_payment_request",
                "text_registration_refund_offer",
                "text_registration_canceled",
                "text_discount_granted",
                "text_payment_received",
                "text_payment_returned",
            ]:
                form.base_fields[field_name].help_text = lazy_help_text_with_html_default(
                    form.base_fields[field_name].help_text,
                    getattr(request.subject_type, field_name) or DEFAULT_TEXTS[field_name],
                )
            form.base_fields["chat_group_type"].help_text = lazy_help_text_with_default(
                form.base_fields["chat_group_type"].help_text,
                CHAT_GROUP_TYPE_LABELS[request.subject_type.chat_group_type],
            )

        return form

    def get_inline_instances(self, request, obj=None):
        return [] if hasattr(request, "hide_inlines") else super().get_inline_instances(request, obj)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        formfield = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == "subject_type":
            limit_choices_to = {"subject_type__exact": self.subject_type_type}
            formfield.limit_choices_to = limit_choices_to
        return formfield

    def save_form(self, request, form, change):
        obj = super().save_form(request, form, change)
        obj.school_year = request.school_year
        return obj

    def get_journal_link(self, obj):
        return "<br/>".join(
            (
                format_html(
                    '<a href="{url}" title="{title}" target="_blank">{journal}</a>',
                    url=reverse("admin:leprikon_subject_journal", args=[obj.id]),
                    title=_("printable journal"),
                    journal=_("journal"),
                ),
                format_html(
                    '<a href="{url}" title="{title}" target="_blank">{participants}</a>',
                    url=reverse("admin:leprikon_subject_journal_pdf", args=[obj.id]),
                    title=_("printable list of participants"),
                    participants=_("participants"),
                ),
            )
        )

    get_journal_link.short_description = _("journal")
    get_journal_link.allow_tags = True

    def get_message_recipients(self, request, queryset):
        return get_user_model().objects.filter(leprikon_subjectregistrations__subject__in=queryset).distinct()

    def get_registrations_link(self, obj):
        icon = False
        approved_registrations_count = obj.approved_registrations.count()
        unapproved_registrations_count = obj.unapproved_registrations.count()

        if approved_registrations_count == 0:
            title = _("There are no approved registrations for this {}.").format(obj.subject_type.name_akuzativ)
        elif obj.min_registrations_count is not None and approved_registrations_count < obj.min_registrations_count:
            title = _("The number of approved registrations is lower than {}.").format(obj.min_registrations_count)
        elif obj.max_registrations_count is not None and approved_registrations_count > obj.max_registrations_count:
            title = _("The number of approved registrations is greater than {}.").format(obj.max_registrations_count)
        else:
            icon = True
            title = ""
        return format_html(
            '<a href="{url}" title="{title}">{icon} {approved}{unapproved}</a>',
            url=reverse(
                "admin:{}_{}_changelist".format(
                    self.registration_model._meta.app_label,
                    self.registration_model._meta.model_name,
                )
            )
            + "?subject__id__exact={}".format(obj.id),
            title=title,
            icon=_boolean_icon(icon),
            approved=approved_registrations_count,
            unapproved=" + {}".format(unapproved_registrations_count) if unapproved_registrations_count else "",
        ) + format_html(
            '<a class="popup-link" href="{url}" style="background-position: 0 0" title="{title}">'
            '<img src="{icon}" alt="+"/></a>',
            url=reverse(
                "admin:{}_{}_add".format(
                    self.registration_model._meta.app_label,
                    self.registration_model._meta.model_name,
                )
            )
            + "?subject={}".format(obj.id),
            title=_("add registration"),
            icon=static("admin/img/icon-addlink.svg"),
        )

    get_registrations_link.short_description = _("registrations")
    get_registrations_link.allow_tags = True

    def registration_allowed_icon(self, obj):
        return _boolean_icon(obj.registration_allowed)

    registration_allowed_icon.short_description = _("registration allowed")

    def get_approved_registrations_count(self, obj):
        return obj.registrations.filter(canceled=None).exclude(approved=None).count()

    get_approved_registrations_count.short_description = _("approved registrations count")
    get_approved_registrations_count.admin_order_field = "approved registrations_count"

    def get_unapproved_registrations_count(self, obj):
        return obj.registrations.filter(canceled=None, approved=None).count()

    get_unapproved_registrations_count.short_description = _("unapproved registrations count")
    get_unapproved_registrations_count.admin_order_field = "unapproved registrations_count"

    def icon(self, obj):
        try:
            return '<img src="{}" alt="{}"/>'.format(obj.photo.icons["48"], obj.photo.label)
        except (AttributeError, KeyError):
            return ""

    icon.allow_tags = True
    icon.short_description = _("photo")


class ChangeformRedirectMixin:
    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        if object_id:
            obj = self.get_object(request, unquote(object_id))
            if obj:
                return HttpResponseRedirect(obj.get_edit_url())
        return super().changeform_view(request, object_id, form_url, extra_context)


@admin.register(Subject)
class SubjectAdmin(AdminExportMixin, SendMessageAdminMixin, ChangeformRedirectMixin, admin.ModelAdmin):
    """Hidden admin used for raw id fields"""

    list_display = (
        "id",
        "code",
        "name",
        "subject_type",
        "get_groups_list",
        "get_leaders_list",
        "icon",
    )
    list_filter = (
        ("school_year", SchoolYearListFilter),
        "department",
        "subject_type__subject_type",
        ("subject_type", SubjectTypeListFilter),
        "registration_type",
        ("groups", SubjectGroupListFilter),
        ("leaders", LeaderListFilter),
    )
    search_fields = ("name", "description")

    def get_model_perms(self, request):
        return {}

    def has_add_permission(self, request):
        return False

    def icon(self, obj):
        try:
            return '<img src="{}" alt="{}"/>'.format(obj.photo.icons["48"], obj.photo.label)
        except (AttributeError, KeyError):
            return ""

    icon.allow_tags = True
    icon.short_description = _("photo")

    def get_urls(self):
        return [
            urls_url(
                r"(?P<subject_id>\d+)/journal/$",
                self.admin_site.admin_view(self.journal),
                name="leprikon_subject_journal",
            ),
            urls_url(
                r"(?P<subject_id>\d+)/journal-pdf/$",
                self.admin_site.admin_view(self.journal_pdf),
                name="leprikon_subject_journal_pdf",
            ),
        ] + super().get_urls()

    def journal(self, request, subject_id):
        return render(
            request,
            "leprikon/subject_journal.html",
            {
                "subject": get_object_or_404(Subject, id=subject_id),
                "admin": True,
            },
        )

    def journal_pdf(self, request, subject_id):
        obj = self.get_object(request, subject_id)

        # create PDF response object
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="{}"'.format(obj.get_pdf_filename("journal_pdf"))

        # write PDF to response
        return obj.write_pdf("journal_pdf", response)


class SubjectRegistrationParticipantInlineAdmin(admin.StackedInline):
    model = SubjectRegistrationParticipant
    extra = 0

    def get_min_num(self, request, obj=None, **kwargs):
        return request.subject.min_participants_count

    def get_max_num(self, request, obj=None, **kwargs):
        return request.subject.max_participants_count

    def get_formset(self, request, obj, **kwargs):
        questions = obj.all_questions if obj else request.subject.all_questions
        fields = dict(("q_" + q.name, q.get_field()) for q in questions)
        fields["subject"] = request.subject
        fields["obj"] = obj
        kwargs["form"] = type(RegistrationParticipantAdminForm.__name__, (RegistrationParticipantAdminForm,), fields)
        return super().get_formset(request, obj, **kwargs)


class SubjectRegistrationGroupInlineAdmin(admin.StackedInline):
    model = SubjectRegistrationGroup
    extra = 1
    min_num = 1
    max_num = 1

    def get_formset(self, request, obj, **kwargs):
        questions = obj.all_questions if obj else request.subject.all_questions
        fields = dict(("q_" + q.name, q.get_field()) for q in questions)
        fields["subject"] = request.subject
        fields["obj"] = obj
        kwargs["form"] = type(RegistrationGroupAdminForm.__name__, (RegistrationGroupAdminForm,), fields)
        return super().get_formset(request, obj, **kwargs)


class SubjectRegistrationGroupMemberInlineAdmin(admin.StackedInline):
    model = SubjectRegistrationGroupMember
    extra = 0

    def get_min_num(self, request, obj=None, **kwargs):
        return request.subject.min_group_members_count

    def get_max_num(self, request, obj=None, **kwargs):
        return request.subject.max_group_members_count


class RegistrationBillingInfoInlineAdmin(admin.TabularInline):
    model = SubjectRegistrationBillingInfo
    max_num = 1
    extra = 0


class SubjectRegistrationBaseAdmin(AdminExportMixin, SendMailAdminMixin, SendMessageAdminMixin, admin.ModelAdmin):
    actions = ("approve", "refuse", "request_payment", "offer_refund", "generate_refund_request", "cancel")
    form = RegistrationAdminForm
    inlines = (RegistrationBillingInfoInlineAdmin,)
    list_editable = ("note",)
    list_export = (
        "id",
        "variable_symbol",
        "slug",
        "user",
        "subject",
        "subject_variant",
        "price",
        "note",
        "created",
        "created_by",
        "payment_requested",
        "payment_requested_by",
        "refund_offered",
        "refund_offered_by",
        "approved",
        "approved_by",
        "cancelation_requested",
        "cancelation_requested_by",
        "canceled",
        "canceled_by",
        "agreement_options_list",
        "group_members_list",
        "participants__gender",
        "participants__first_name",
        "participants__last_name",
        "participants__birth_num",
        "participants__birth_date",
        "participants__gender",
        "participants__age_group",
        "participants__street",
        "participants__city",
        "participants__postal_code",
        "participants__citizenship",
        "participants__phone",
        "participants__email",
        "participants__school",
        "participants__school_other",
        "participants__school_class",
        "participants__health",
        "participants__answers",
        "participants__has_parent1",
        "participants__parent1_first_name",
        "participants__parent1_last_name",
        "participants__parent1_street",
        "participants__parent1_city",
        "participants__parent1_postal_code",
        "participants__parent1_phone",
        "participants__parent1_email",
        "participants__has_parent2",
        "participants__parent2_first_name",
        "participants__parent2_last_name",
        "participants__parent2_street",
        "participants__parent2_city",
        "participants__parent2_postal_code",
        "participants__parent2_phone",
        "participants__parent2_email",
        "group__name",
        "group__first_name",
        "group__last_name",
        "group__street",
        "group__city",
        "group__postal_code",
        "group__phone",
        "group__email",
        "group__school__name",
        "group__school_other",
        "group__school_class",
        "billing_info__name",
        "billing_info__street",
        "billing_info__city",
        "billing_info__postal_code",
        "billing_info__company_num",
        "billing_info__vat_number",
        "billing_info__contact_person",
        "billing_info__phone",
        "billing_info__email",
        "billing_info__employee",
    )
    list_filter = (
        ("subject__school_year", SchoolYearListFilter),
        "subject__department",
        ("subject__subject_type", SubjectTypeListFilter),
        "subject__registration_type",
        ApprovedListFilter,
        CanceledListFilter,
        "registration_link",
        ("billing_info", IsNullFieldListFilter),
        "subject__groups",
        ("subject", SubjectListFilter),
        ("subject__leaders", LeaderListFilter),
        "subject__place",
    )
    search_fields = (
        "variable_symbol",
        "participants__birth_num",
        "participants__first_name",
        "participants__last_name",
        "participants__parent1_first_name",
        "participants__parent1_last_name",
        "participants__parent2_first_name",
        "participants__parent2_last_name",
        "group_members__first_name",
        "group_members__last_name",
    )
    ordering = ("-created",)
    raw_id_fields = (
        "subject",
        "user",
    )

    @property
    def media(self):
        m = super().media
        m.add_js(["leprikon/js/Popup.js"])
        m.add_css({"all": ["leprikon/css/registrations.changelist.css"]})
        return m

    def has_delete_permission(self, request, obj=None):
        if obj and obj.approved is None and obj.payments.count() == 0 and obj.returned_payments.count() == 0:
            return super().has_delete_permission(request, obj)
        else:
            return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        if "delete_selected" in actions:
            del actions["delete_selected"]
        return actions

    def get_changelist(self, request, **kwargs):
        class ChangeList(super().get_changelist(request, **kwargs)):
            def get_ordering(self, request, queryset):
                # Show registrations with cancelation request on the top
                # if not showing canceled ones.
                ordering = super().get_ordering(request, queryset)
                return (
                    ordering
                    if request.GET.get("canceled") == "yes"
                    else [
                        IsNull("cancelation_requested"),
                        *ordering,
                    ]
                )

        return ChangeList

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                "discounts",
                "payments",
                "returned_payments",
            )
            .select_related(
                "subject",
                "user",
            )
            .annotate(random_number=Random())
        )

    def approve(self, request, queryset):
        for registration in queryset.all():
            try:
                registration.approve(request.user)
            except ValidationError as e:
                self.message_user(request, e.message, messages.ERROR)
            else:
                self.message_user(
                    request,
                    _("The registration {r} has been approved and the user has been notified.").format(r=registration),
                )

    approve.short_description = _("Approve selected registrations")

    def refuse(self, request, queryset):
        for registration in queryset.all():
            try:
                registration.refuse(request.user)
            except ValidationError as e:
                self.message_user(request, e.message, messages.ERROR)
            else:
                self.message_user(
                    request,
                    _("The registration {r} has been refused and the user has been notified.").format(r=registration),
                )

    refuse.short_description = _("Refuse selected registrations")

    def request_payment(self, request, queryset):
        for registration in queryset.all():
            registration.request_payment(request.user)
        self.message_user(request, _("Payment was requested for selected registrations."))

    request_payment.short_description = _("Request payment for selected registrations")

    def offer_refund(self, request, queryset):
        for registration in queryset.all():
            registration.offer_refund(request.user)
        self.message_user(request, _("Refund was offered for selected registrations."))

    offer_refund.short_description = _("Offer refund for selected registrations")

    def generate_refund_request(self, request, queryset):
        for registration in queryset.filter(refund_request__bank_account=None):
            registration.generate_refund_request(request.user)
        self.message_user(request, _("Refund requests were generated for selected registrations."))

    generate_refund_request.short_description = _("Generate refund requests for selected registrations")

    def cancel(self, request, queryset):
        for registration in queryset.all():
            try:
                registration.cancel(request.user)
            except ValidationError as e:
                self.message_user(request, e.message, messages.ERROR)
            else:
                self.message_user(
                    request,
                    _("The registration {r} has been canceled and the user has been notified.").format(r=registration),
                )

    cancel.short_description = _("Cancel selected registrations")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        formfield = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == "subject":
            limit_choices_to = {"subject_type__subject_type__exact": self.model.subject_type}
            formfield.limit_choices_to = limit_choices_to
            formfield.widget.rel.limit_choices_to = limit_choices_to
        return formfield

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        if not object_id and request.method == "POST" and "user" not in request.POST:
            return HttpResponseRedirect("{}?subject={}".format(request.path, request.POST.get("subject", "")))
        else:
            return super().changeform_view(request, object_id, form_url, extra_context)

    def get_exclude(self, request, obj=None):
        return [] if not request.subject or request.subject.variants.exists() else ["subject_variant"]

    def get_form(self, request, obj, **kwargs):
        try:
            # first try request.POST (user may want to change the subject)
            request.subject = Subject.objects.get(id=int(request.POST.get("subject")))
        except (Subject.DoesNotExist, TypeError, ValueError):
            if obj:
                # use subject from object
                request.subject = obj.subject
            else:
                # try to get subject from request.GET
                try:
                    request.subject = Subject.objects.get(id=int(request.GET.get("subject")))
                except (Subject.DoesNotExist, TypeError, ValueError):
                    request.subject = None

        if request.subject:
            kwargs["form"] = type(
                self.form.__name__,
                (self.form,),
                {"subject": request.subject},
            )
        else:
            kwargs["form"] = forms.ModelForm
            kwargs["fields"] = ["subject"]
        return super().get_form(request, obj, **kwargs)

    def get_inline_instances(self, request, obj=None):
        if request.subject:
            if request.subject.registration_type_participants:
                inlines = (SubjectRegistrationParticipantInlineAdmin,)
            elif request.subject.registration_type_groups:
                inlines = (SubjectRegistrationGroupInlineAdmin, SubjectRegistrationGroupMemberInlineAdmin)
            return [inline(self.model, self.admin_site) for inline in inlines] + super().get_inline_instances(
                request, obj
            )
        else:
            return []

    def save_model(self, request, obj, form, change):
        if not change:
            # set price
            obj.price = obj.subject_variant.get_price() if obj.subject_variant else obj.subject.price
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        if not change:
            form.instance.questions.set(form.instance.subject.all_questions)
            form.instance.agreements.set(form.instance.subject.all_registration_agreements)
            form.instance.generate_variable_symbol_and_slug()
            form.instance.send_mail()

    def get_css(self, obj):
        classes = []
        if obj.cancelation_requested and not obj.canceled:
            classes.append("reg-cancel-request")
        if obj.approved:
            classes.append("reg-approved")
        else:
            classes.append("reg-new")
            if obj.subject.full:
                classes.append("reg-full")
        if obj.canceled:
            classes.append("reg-canceled")
        else:
            classes.append("reg-active")
        return " ".join(classes)

    legend = (
        ("reg-cancel-request", _("cancelation requested")),
        ("reg-new", _("new registration")),
        ("reg-new reg-full", _("new registration, capacity full")),
        ("reg-approved", _("approved registration")),
    )

    def subject_name(self, obj):
        return obj.subject.name

    subject_name.short_description = _("subject")

    def _datetime_with_by(self, obj, attr):
        d = getattr(obj, attr)
        if d:
            d_formated = date_format(localtime(d), "SHORT_DATETIME_FORMAT")
            by = getattr(obj, attr + "_by")
            return mark_safe(f'<span title="{by}">{d_formated}</span>') if by else d_formated
        return "-"

    created_with_by = datetime_with_by("created", _("time of registration"))

    approved_with_by = datetime_with_by("approved", _("time of approval"))

    payment_requested_with_by = datetime_with_by("payment_requested", _("payment request time"))

    refund_offered_with_by = datetime_with_by("refund_offered", _("refund offer time"))

    cancelation_requested_with_by = datetime_with_by("cancelation_requested", _("time of cancellation request"))

    canceled_with_by = datetime_with_by("canceled", _("time of cancellation"))

    def get_message_recipients(self, request, queryset):
        return get_user_model().objects.filter(leprikon_registrations__in=queryset).distinct()

    def random_number(self, obj):
        return int(obj.random_number * 1000000000000)

    random_number.admin_order_field = "random_number"
    random_number.short_description = _("random number")

    def returned_payments(self, obj):
        return format_html(
            '<a href="{href}"><b>{amount}</b></a>',
            href=reverse("admin:leprikon_subjectreturnedpayment_changelist") + f"?source_registration={obj.id}",
            amount=currency(sum(r.amount for r in obj.all_returned_payments)),
        ) + format_html(
            '<a class="popup-link" href="{href}" style="background-position: 0 0" title="{title}">'
            '<img src="{icon}" alt="+"/></a>',
            href=reverse("admin:leprikon_subjectreturnedpayment_add") + f"?source_registration={obj.id}",
            title=_("add returned payment"),
            icon=static("admin/img/icon-addlink.svg"),
        )

    returned_payments.allow_tags = True
    returned_payments.short_description = _("returned payments")


@admin.register(SubjectRegistration)
class SubjectRegistrationAdmin(AdminExportMixin, SendMessageAdminMixin, ChangeformRedirectMixin, admin.ModelAdmin):
    """Hidden admin used for raw id fields"""

    list_display = (
        "id",
        "variable_symbol",
        "subject",
        "participants_list_html",
        "group",
        "created",
        "canceled",
    )
    list_filter = (
        ("subject__school_year", SchoolYearListFilter),
        "subject__department",
        ("subject__subject_type", SubjectTypeListFilter),
        ApprovedListFilter,
        CanceledListFilter,
        ("subject", SubjectListFilter),
        ("subject__leaders", LeaderListFilter),
    )
    ordering = ("-created",)
    search_fields = (
        "variable_symbol",
        "participants__birth_num",
        "participants__first_name",
        "participants__last_name",
        "participants__parent1_first_name",
        "participants__parent1_last_name",
        "participants__parent2_first_name",
        "participants__parent2_last_name",
        "group_members__first_name",
        "group_members__last_name",
    )

    def get_model_perms(self, request):
        return {}

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        return {}


class SubjectDiscountBaseAdmin(TransactionAdminMixin, AdminExportMixin, admin.ModelAdmin):
    list_filter = (
        ("registration__subject__school_year", SchoolYearListFilter),
        "registration__subject__department",
        ("registration__subject__subject_type", SubjectTypeListFilter),
        ("registration__subject", SubjectListFilter),
        ("registration__subject__leaders", LeaderListFilter),
    )
    search_fields = (
        "registration__variable_symbol",
        "registration__subject__name",
        "registration__participants__first_name",
        "registration__participants__last_name",
        "registration__participants__birth_num",
    )
    raw_id_fields = ("registration",)
    closed_fields = ("accounted", "registration", "amount")

    def subject(self, obj):
        return obj.registration.subject

    subject.short_description = _("subject")

    list_export = (
        "id",
        "accounted",
        "accounted_by",
        "transaction_type_label",
        "amount",
        "organization",
        "donor__username",
        "donor",
        "last_updated",
        "last_updated_by",
        "mail_sent",
        "note",
    )


class SubjectPaymentAdminMixin:
    list_display = (
        "id",
        "accounted_with_by",
        "download_tag",
        "transaction_type",
        "amount_html",
        "registration",
        "last_updated_with_by",
        "mail_sent",
        "note",
    )
    list_export = (
        "id",
        "accounted",
        "accounted_by",
        "transaction_type_label",
        "amount",
        "registration",
        "variable_symbol",
        "last_updated",
        "last_updated_by",
        "note",
    )

    def variable_symbol(self, obj):
        return obj.registration.variable_symbol

    variable_symbol.short_description = _("variable symbol")


@admin.register(SubjectReceivedPayment)
class SubjectReceivedPaymentAdmin(SubjectPaymentAdminMixin, TransactionBaseAdmin):
    exclude = ("donor", "organization")
    list_filter = (
        ("target_registration__subject__school_year", SchoolYearListFilter),
        ("transaction_type", TransactionTypeListFilter),
        "target_registration__subject__department",
        ("target_registration__subject__subject_type", SubjectTypeListFilter),
        ("target_registration__subject", SubjectListFilter),
        ("target_registration__subject__leaders", LeaderListFilter),
    )
    search_fields = (
        "target_registration__subject__name",
        "target_registration__participants__first_name",
        "target_registration__participants__last_name",
        "target_registration__participants__birth_num",
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["target_registration"].required = True
        return form


@admin.register(SubjectReturnedPayment)
class SubjectReturnedPaymentAdmin(SubjectPaymentAdminMixin, TransactionBaseAdmin):
    exclude = ("pays_payment",)
    list_filter = (
        ("source_registration__subject__school_year", SchoolYearListFilter),
        ("transaction_type", TransactionTypeListFilter),
        "source_registration__subject__department",
        ("source_registration__subject__subject_type", SubjectTypeListFilter),
        ("source_registration__subject", SubjectListFilter),
        ("source_registration__subject__leaders", LeaderListFilter),
    )
    search_fields = (
        "source_registration__subject__name",
        "source_registration__participants__first_name",
        "source_registration__participants__last_name",
        "source_registration__participants__birth_num",
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["source_registration"].required = True
        return form

    def amount_html(self, obj):
        return format_html(
            '<b style="color: {color}">{amount}</b>',
            color=amount_color(-obj.amount),
            amount=currency(obj.amount),
        )

    amount_html.short_description = _("amount")
    amount_html.admin_order_field = "amount"
    amount_html.allow_tags = True
