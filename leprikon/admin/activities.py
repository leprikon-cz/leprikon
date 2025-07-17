from typing import Any, List, Optional

from adminsortable2.admin import SortableAdminMixin, SortableInlineAdminMixin
from django import forms
from django.contrib import admin, messages
from django.contrib.admin.templatetags.admin_list import _boolean_icon
from django.contrib.admin.utils import unquote
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import BooleanField, F, Func
from django.db.models.functions import Coalesce, Random
from django.http import HttpRequest, HttpResponseRedirect
from django.template.response import SimpleTemplateResponse
from django.templatetags.static import static
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from ..forms.activities import (
    ActivityAdminForm,
    ActivityVariantForm,
    RegistrationAdminForm,
    RegistrationGroupAdminForm,
    RegistrationParticipantAdminForm,
)
from ..models.activities import (
    DEFAULT_TEXTS,
    Activity,
    ActivityAttachment,
    ActivityGroup,
    ActivityModel,
    ActivityTime,
    ActivityType,
    ActivityTypeAttachment,
    ActivityTypePrintSetups,
    ActivityTypeTexts,
    ActivityVariant,
    ReceivedPayment,
    Registration,
    RegistrationBillingInfo,
    RegistrationGroup,
    RegistrationGroupMember,
    RegistrationParticipant,
    ReturnedPayment,
)
from ..models.utils import lazy_help_text_with_html_default
from ..utils import amount_color, attributes, currency
from .bulkupdate import BulkUpdateMixin
from .export import AdminExportMixin
from .filters import (
    ActivityGroupListFilter,
    ActivityListFilter,
    ActivityTypeListFilter,
    ApprovedListFilter,
    CanceledListFilter,
    IsNullFieldListFilter,
    LeaderListFilter,
    SchoolYearListFilter,
)
from .messages import SendMessageAdminMixin
from .sendmail import SendMailAdminMixin
from .settings import ChildModelAdmin, ParentAdminMixin
from .transaction import TransactionAdminMixin, TransactionBaseAdmin, TransactionTypeListFilter
from .utils import datetime_with_by


class IsNull(Func):
    _output_field = BooleanField()
    arity = 1
    template = "%(expressions)s IS NULL"


class ActivityTypeAttachmentInlineAdmin(SortableInlineAdminMixin, admin.TabularInline):
    model = ActivityTypeAttachment
    extra = 0


ACTIVITY_TYPE_TEXT_FIELDS = [f.name for f in ActivityTypeTexts._meta.fields if f.name.startswith("text_")]
ACTIVITY_TYPE_PRINT_SETUP_FIELDS = [
    f.name for f in ActivityTypePrintSetups._meta.fields if f.name.endswith("_print_setup")
]


@admin.register(ActivityType)
class ActivityTypeAdmin(ParentAdminMixin, BulkUpdateMixin, SortableAdminMixin, admin.ModelAdmin):
    child_models = [ActivityTypeTexts, ActivityTypePrintSetups]
    bulk_update_exclude = (
        "model",
        "page",
        "slug",
        "order",
        "name",
        "plural",
        "name_genitiv",
        "name_akuzativ",
    )
    list_display = ("display_name",)
    filter_horizontal = ("questions", "registration_agreements")
    exclude = ACTIVITY_TYPE_TEXT_FIELDS + ACTIVITY_TYPE_PRINT_SETUP_FIELDS
    prepopulated_fields = {"slug": ("plural",)}
    inlines = (ActivityTypeAttachmentInlineAdmin,)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        # limit choices of registration agreements
        registration_agreements_choices = form.base_fields["registration_agreements"].widget.widget.choices
        registration_agreements_choices.queryset = registration_agreements_choices.queryset.exclude(
            id__in=request.leprikon_site.registration_agreements.values("id")
        )
        form.base_fields["registration_agreements"].choices = registration_agreements_choices

        return form

    @admin.display(description=_("activity type"))
    def display_name(self, obj: ActivityType) -> str:
        return obj.plural


@admin.register(ActivityTypeTexts)
class ActivityTypeTextsAdmin(ChildModelAdmin):
    parent_model = ActivityType
    fields = ACTIVITY_TYPE_TEXT_FIELDS


@admin.register(ActivityTypePrintSetups)
class ActivityTypePrintSetupsAdmin(ChildModelAdmin):
    parent_model = ActivityType
    fields = ACTIVITY_TYPE_PRINT_SETUP_FIELDS


@admin.register(ActivityGroup)
class ActivityGroupAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ("name", "color")
    list_editable = ("color",)
    filter_horizontal = ("activity_types",)


class ActivityAttachmentInlineAdmin(SortableInlineAdminMixin, admin.TabularInline):
    model = ActivityAttachment
    extra = 0


class ActivityTimeInlineAdmin(admin.TabularInline):
    model = ActivityTime
    extra = 0


class ActivityBaseAdmin(AdminExportMixin, BulkUpdateMixin, SendMessageAdminMixin, admin.ModelAdmin):
    registration_model = None
    actions = (
        SendMessageAdminMixin.actions + BulkUpdateMixin.actions + AdminExportMixin.actions + ("set_registration_dates",)
    )
    list_editable = ("note",)
    list_filter = (
        ("school_year", SchoolYearListFilter),
        "department",
        ("activity_type", ActivityTypeListFilter),
        ("groups", ActivityGroupListFilter),
        ("leaders", LeaderListFilter),
        "place",
    )
    inlines = (
        ActivityTimeInlineAdmin,
        ActivityAttachmentInlineAdmin,
    )
    filter_horizontal = ("age_groups", "target_groups", "groups", "leaders", "questions", "registration_agreements")
    search_fields = ("name", "description")
    save_as = True

    class Media:
        js = ["leprikon/js/Popup.js"]

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        if not object_id and request.method == "POST" and len(request.POST) == 4:
            return HttpResponseRedirect(
                "{}?activity_type={}&registration_type={}".format(
                    request.path,
                    request.POST.get("activity_type", ""),
                    request.POST.get("registration_type", ""),
                )
            )
        else:
            return super().changeform_view(request, object_id, form_url, extra_context)

    def get_exclude(self, request, obj=None):
        if request.registration_type == Activity.PARTICIPANTS:
            exclude = ["target_groups"]
        elif request.registration_type == Activity.GROUPS:
            exclude = ["age_groups"]
        else:
            exclude = []
        if obj and obj.registrations.exists():
            exclude.append("registration_type")
        return exclude

    def get_fieldsets(self, request, obj: Activity = None):
        available_fields = self.get_fields(request, obj)
        used_fields = []
        fieldsets = []
        for label, all_fields in [
            (
                None,
                [
                    "activity_type",
                    "registration_type",
                    "name",
                    "description",
                    # course specific
                    "school_year_division",
                    "allow_period_selection",
                    # event specific
                    "start_date",
                    "end_date",
                    "start_time",
                    "end_time",
                    "due_from",
                    "due_date",
                    # orderable specific
                    "duration",
                    "due_from_days",
                    "due_date_days",
                    "min_due_date_days",
                    "age_groups",
                    "target_groups",
                    "reg_from",
                    "reg_to",
                    "public",
                ],
            ),
            (
                _("advanced settings"),
                [
                    "code",
                    "department",
                    "groups",
                    "place",
                    "leaders",
                    "photo",
                    "page",
                    "min_registrations_count",
                    "max_registrations_count",
                    "note",
                    "questions",
                    "registration_agreements",
                    "reg_print_setup",
                    "decision_print_setup",
                    "pr_print_setup",
                    "bill_print_setup",
                    "organization",
                ],
            ),
            (
                _("texts"),
                [
                    "text_registration_received",
                    "text_registration_approved",
                    "text_registration_refused",
                    "text_registration_payment_request",
                    "text_registration_refund_offer",
                    "text_registration_canceled",
                    "text_discount_granted",
                    "text_payment_received",
                    "text_payment_returned",
                ],
            ),
        ]:
            fields = [f for f in all_fields if f in available_fields]
            if fields:
                fieldsets.append((label, {"fields": fields}))
                used_fields += fields
        unused_fields = [f for f in available_fields if f not in used_fields]
        if unused_fields:
            fieldsets.append((None, {"fields": unused_fields}))
        return fieldsets

    def get_form(self, request, obj, **kwargs):
        # set school year
        if obj:
            request.school_year = obj.school_year

        # get activity type
        try:
            # first try request.POST (user may want to change activity type)
            request.activity_type = ActivityType.objects.get(id=int(request.POST.get("activity_type")))
        except (ActivityType.DoesNotExist, TypeError, ValueError):
            if obj:
                # use activity type from object
                request.activity_type = obj.activity_type
            else:
                # try to get activity type from request.GET
                try:
                    request.activity_type = ActivityType.objects.get(
                        id=int(request.GET.get("activity_type")),
                    )
                except (ActivityType.DoesNotExist, TypeError, ValueError):
                    request.activity_type = None

        # get registration type
        request.registration_type = request.POST.get("registration_type")
        if request.registration_type not in Activity.REGISTRATION_TYPES:
            if obj:
                # use registration type from object
                request.registration_type = obj.registration_type
            else:
                # try to get registration type from request.GET
                request.registration_type = request.GET.get("registration_type")
                if request.registration_type not in Activity.REGISTRATION_TYPES:
                    request.registration_type = None

        if request.activity_type and request.registration_type:
            kwargs["form"] = type(
                ActivityAdminForm.__name__,
                (ActivityAdminForm,),
                {
                    "school_year": request.school_year,
                    "activity_type": request.activity_type,
                    "registration_type": request.registration_type,
                },
            )
        else:
            kwargs["fields"] = ["activity_type", "registration_type"]
            request.hide_inlines = True

        form = super().get_form(request, obj, **kwargs)

        if request.activity_type and request.registration_type:
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
                    getattr(request.activity_type, field_name) or DEFAULT_TEXTS[field_name],
                )

        return form

    def get_inline_instances(self, request, obj=None):
        return [] if hasattr(request, "hide_inlines") else super().get_inline_instances(request, obj)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        formfield = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == "activity_type":
            limit_choices_to = {"model__exact": self.activity_type_model}
            formfield.limit_choices_to = limit_choices_to
        return formfield

    def save_form(self, request, form, change):
        obj = super().save_form(request, form, change)
        obj.school_year = request.school_year
        return obj

    @attributes(short_description=_("journals"))
    def journals_link(self, obj):
        return mark_safe(
            format_html(
                '<a href="{url}">{journals}</a>',
                url=reverse("admin:leprikon_journal_changelist")
                + f"?activity__activity_type__id__exact={obj.activity_type_id}&activity__id__exact={obj.id}",
                journals=_("journals"),
            )
            + format_html(
                '<a href="{url}" style="background-position: 0 0" title="{title}">' '<img src="{icon}" alt="+"/></a>',
                url=reverse("admin:leprikon_journal_add") + "?activity={}".format(obj.id),
                title=_("add journal"),
                icon=static("admin/img/icon-addlink.svg"),
            )
        )

    def get_message_recipients(self, request, queryset):
        return (
            get_user_model()
            .objects.filter(
                leprikon_registrations__canceled=None,
                leprikon_registrations__activity__in=queryset,
            )
            .distinct()
        )

    @attributes(short_description=_("registering"))
    def get_registering_link(self, obj):
        return mark_safe(
            format_html(
                '<a href="{url}">{activity_variants}</a>',
                url=reverse("admin:leprikon_activityvariant_changelist") + f"?activity__exact={obj.id}",
                activity_variants=_("price and registering variants"),
            )
            + format_html(
                '<a href="{url}" style="background-position: 0 0" title="{title}">' '<img src="{icon}" alt="+"/></a>',
                url=reverse("admin:leprikon_activityvariant_add") + "?activity={}".format(obj.id),
                title=_("add price and registering variant"),
                icon=static("admin/img/icon-addlink.svg"),
            )
        )

    @attributes(short_description=_("registrations"))
    def get_registrations_link(self, obj):
        icon = False
        approved_registrations_count = obj.approved_registrations.count()
        unapproved_registrations_count = obj.unapproved_registrations.count()

        if approved_registrations_count == 0:
            title = _("There are no approved registrations for this {}.").format(obj.activity_type.name_akuzativ)
        elif obj.min_registrations_count is not None and approved_registrations_count < obj.min_registrations_count:
            title = _("The number of approved registrations is lower than {}.").format(obj.min_registrations_count)
        elif obj.max_registrations_count is not None and approved_registrations_count > obj.max_registrations_count:
            title = _("The number of approved registrations is greater than {}.").format(obj.max_registrations_count)
        else:
            icon = True
            title = ""
        return mark_safe(
            format_html(
                '<a href="{url}" title="{title}">{icon} {approved}{unapproved}</a>',
                url=reverse(
                    "admin:{}_{}_changelist".format(
                        self.registration_model._meta.app_label,
                        self.registration_model._meta.model_name,
                    )
                )
                + "?activity__id__exact={}".format(obj.id),
                title=title,
                icon=_boolean_icon(icon),
                approved=approved_registrations_count,
                unapproved=" + {}".format(unapproved_registrations_count) if unapproved_registrations_count else "",
            )
            + format_html(
                '<a class="popup-link" href="{url}" style="background-position: 0 0" title="{title}">'
                '<img src="{icon}" alt="+"/></a>',
                url=reverse(
                    "admin:{}_{}_add".format(
                        self.registration_model._meta.app_label,
                        self.registration_model._meta.model_name,
                    )
                ),
                title=_("add registration"),
                icon=static("admin/img/icon-addlink.svg"),
            )
        )

    @attributes(short_description=_("approved registrations count"))
    def get_approved_registrations_count(self, obj):
        return obj.registrations.filter(canceled=None).exclude(approved=None).count()

    @attributes(short_description=_("unapproved registrations count"))
    def get_unapproved_registrations_count(self, obj):
        return obj.registrations.filter(canceled=None, approved=None).count()

    @attributes(short_description=_("photo"))
    def icon(self, obj):
        try:
            return mark_safe('<img src="{}" alt="{}"/>'.format(obj.photo.icons["48"], obj.photo.label))
        except (AttributeError, KeyError):
            return ""


class ChangeformRedirectMixin:
    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        if object_id:
            obj = self.get_object(request, unquote(object_id))
            if obj:
                return HttpResponseRedirect(obj.get_edit_url())
        return super().changeform_view(request, object_id, form_url, extra_context)


@admin.register(Activity)
class ActivityAdmin(AdminExportMixin, SendMessageAdminMixin, ChangeformRedirectMixin, admin.ModelAdmin):
    """Hidden admin used for raw id fields"""

    actions = SendMessageAdminMixin.actions + AdminExportMixin.actions
    list_display = (
        "id",
        "code",
        "name",
        "activity_type",
        "get_groups_list",
        "get_leaders_list",
        "icon",
    )
    list_filter = (
        ("school_year", SchoolYearListFilter),
        "department",
        "activity_type__model",
        ("activity_type", ActivityTypeListFilter),
        "registration_type",
        ("groups", ActivityGroupListFilter),
        ("leaders", LeaderListFilter),
    )
    search_fields = ("name", "description")

    def get_model_perms(self, request):
        return {}

    def has_add_permission(self, request, obj=None):
        return False

    @attributes(short_description=_("photo"))
    def icon(self, obj):
        try:
            return mark_safe('<img src="{}" alt="{}"/>'.format(obj.photo.icons["48"], obj.photo.label))
        except (AttributeError, KeyError):
            return ""


@admin.register(ActivityVariant)
class ActivityVariantAdmin(AdminExportMixin, BulkUpdateMixin, SendMessageAdminMixin, admin.ModelAdmin):
    actions = SendMessageAdminMixin.actions + BulkUpdateMixin.actions + AdminExportMixin.actions
    bulk_update_exclude = ("activity", "order")
    list_display = (
        "activity",
        "name",
        "reg_from",
        "reg_to",
        "registration_price",
        "participant_price",
        "school_year_division",
        "get_registrations_link",
        "order",
    )
    list_editable = ("order",)
    list_filter = (
        ("activity__school_year", SchoolYearListFilter),
        "activity__department",
        "activity__activity_type__model",
        ("activity__activity_type", ActivityTypeListFilter),
        ("activity", ActivityListFilter),
    )
    raw_id_fields = ("activity",)
    search_fields = ("name", "description", "activity__name", "activity__description")
    filter_horizontal = ("age_groups", "target_groups", "required_resources", "required_resource_groups")

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        if not object_id and request.method == "POST" and "activity" in request.POST:
            return HttpResponseRedirect(f"{request.path}?activity={request.POST['activity']}")
        else:
            return super().changeform_view(request, object_id, form_url, extra_context)

    def get_form(self, request: HttpRequest, obj: ActivityVariant | None, **kwargs):
        if obj:
            request.school_year = obj.activity.school_year
            request.activity = obj.activity
        else:
            # try to get activity from request.GET
            try:
                request.activity = Activity.objects.get(
                    school_year=request.school_year,
                    id=int(request.GET.get("activity")),
                )
            except (Activity.DoesNotExist, TypeError, ValueError):
                request.activity = None

        if request.activity:
            kwargs["form"] = type(ActivityVariantForm.__name__, (ActivityVariantForm,), {"activity": request.activity})
        else:
            kwargs["fields"] = ["activity"]

        return super().get_form(request, obj, **kwargs)

    def get_bulk_update_form(self, request: HttpRequest, fields: List[str]):
        form = super().get_bulk_update_form(request, fields)
        if "school_year_division" in form.base_fields:
            form = type(
                form.__name__,
                (form,),
                {"school_year_division": forms.ModelChoiceField(request.school_year.divisions.all())},
            )
        return form

    def get_exclude(self, request: HttpRequest, obj: ActivityVariant | None) -> Any:
        if not request.activity:
            return []
        exclude = ["activity", "order"]
        if request.activity:
            if request.activity.registration_type_participants:
                exclude.append("target_groups")
            if request.activity.registration_type_groups:
                exclude.append("age_groups")
            if request.activity.activity_type.model != ActivityModel.COURSE:
                exclude.append("school_year_division")
        return exclude

    def get_message_recipients(self, request, queryset):
        return (
            get_user_model()
            .objects.filter(
                leprikon_registrations__canceled=None,
                leprikon_registrations__activity_variant__in=queryset,
            )
            .distinct()
        )

    @attributes(short_description=_("registrations"))
    def get_registrations_link(self, obj):
        approved_registrations_count = obj.approved_registrations.count()
        unapproved_registrations_count = obj.unapproved_registrations.count()
        registration_model = {
            ActivityModel.COURSE: "courseregistration",
            ActivityModel.EVENT: "eventregistration",
            ActivityModel.ORDERABLE: "orderableregistration",
        }[obj.activity.activity_type.model]

        return mark_safe(
            format_html(
                '<a href="{url}">{approved}{unapproved}</a>',
                url=reverse(f"admin:leprikon_{registration_model}_changelist")
                + "?activity__id__exact={}&activity_variant__id__exact={}".format(obj.activity_id, obj.id),
                approved=approved_registrations_count,
                unapproved=" + {}".format(unapproved_registrations_count) if unapproved_registrations_count else "",
            )
            + format_html(
                '<a class="popup-link" href="{url}" style="background-position: 0 0" title="{title}">'
                '<img src="{icon}" alt="+"/></a>',
                url=reverse(f"admin:leprikon_{registration_model}_add") + f"?activity_variant={obj.id}",
                title=_("add registration"),
                icon=static("admin/img/icon-addlink.svg"),
            )
        )


class RegistrationParticipantInlineAdmin(admin.StackedInline):
    model = RegistrationParticipant
    extra = 0

    def get_min_num(self, request, obj=None, **kwargs):
        return request.activity_variant.min_participants_count

    def get_max_num(self, request, obj=None, **kwargs):
        return request.activity_variant.max_participants_count

    def get_formset(self, request, obj=None, **kwargs):
        questions = obj.all_questions if obj else request.activity.all_questions
        fields = dict(("q_" + q.slug, q.get_field()) for q in questions)
        fields["activity"] = request.activity
        fields["obj"] = obj
        kwargs["form"] = type(RegistrationParticipantAdminForm.__name__, (RegistrationParticipantAdminForm,), fields)
        return super().get_formset(request, obj, **kwargs)


class RegistrationGroupInlineAdmin(admin.StackedInline):
    model = RegistrationGroup
    extra = 1
    min_num = 1
    max_num = 1

    def get_formset(self, request, obj=None, **kwargs):
        questions = obj.all_questions if obj else request.activity.all_questions
        fields = dict(("q_" + q.slug, q.get_field()) for q in questions)
        fields["activity"] = request.activity
        fields["obj"] = obj
        kwargs["form"] = type(RegistrationGroupAdminForm.__name__, (RegistrationGroupAdminForm,), fields)
        return super().get_formset(request, obj, **kwargs)


class RegistrationGroupMemberInlineAdmin(admin.StackedInline):
    model = RegistrationGroupMember
    extra = 0

    def get_min_num(self, request, obj=None, **kwargs):
        return request.activity_variant.min_participants_count

    def get_max_num(self, request, obj=None, **kwargs):
        return request.activity_variant.max_participants_count


class RegistrationBillingInfoInlineAdmin(admin.TabularInline):
    model = RegistrationBillingInfo
    max_num = 1
    extra = 0


class RegistrationBaseAdmin(AdminExportMixin, SendMailAdminMixin, SendMessageAdminMixin, admin.ModelAdmin):
    actions = (
        SendMessageAdminMixin.actions
        + SendMailAdminMixin.actions
        + AdminExportMixin.actions
        + (
            "approve",
            "refuse",
            "request_payment",
            "offer_refund",
            "generate_refund_request",
            "export_invoices_xml",
            "cancel",
            "cancel_cancelation_request",
        )
    )
    form = RegistrationAdminForm
    inlines = (RegistrationBillingInfoInlineAdmin,)
    list_display = (
        "variable_symbol",
        "download_tag",
        "decision",
        "activity_name",
        "participants_list_html",
        "price",
        "discounts",
        "total_price",
        "received_payments",
        "returned_payments",
        "created_with_by",
        "approved_with_by",
        "payment_requested_with_by",
        "refund_offered_with_by",
        "cancelation_requested_with_by",
        "canceled_with_by",
        "note",
        "random_number",
    )
    list_editable = ("note",)
    list_export = (
        "id",
        "variable_symbol",
        "slug",
        "user",
        "activity",
        "activity_variant",
        "price",
        "discounts_export",
        "total_price_export",
        "received_payments_export",
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
        ("activity__school_year", SchoolYearListFilter),
        "activity__department",
        ("activity__activity_type", ActivityTypeListFilter),
        "activity__registration_type",
        "activity__organization",
        ApprovedListFilter,
        CanceledListFilter,
        "registration_link",
        ("billing_info", IsNullFieldListFilter),
        "activity__groups",
        ("activity", ActivityListFilter),
        ("activity__leaders", LeaderListFilter),
        "activity__place",
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
    exclude = ["activity"]
    raw_id_fields = (
        "activity_variant",
        "calendar_event",
        "user",
    )

    class Media:
        css = {"all": ["leprikon/css/registrations.changelist.css"]}
        js = ["leprikon/js/Popup.js"]

    def has_delete_permission(self, request, obj=None):
        if obj and obj.approved is None and obj.received_payments.count() == 0 and obj.returned_payments.count() == 0:
            return super().has_delete_permission(request, obj)
        else:
            return False

    def lookup_allowed(self, lookup: str, value: str) -> bool:
        return lookup in (
            "participants__birth_date",
            "participants__birth_num",
            "participants__first_name",
            "participants__last_name",
        ) or super().lookup_allowed(lookup, value)

    def get_actions(self, request):
        actions = super().get_actions(request)
        if "delete_selected" in actions:
            del actions["delete_selected"]
        return actions

    def get_changelist(self, request, **kwargs):
        ChangeListBase = super().get_changelist(request, **kwargs)

        class ChangeList(ChangeListBase):
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
                "received_payments",
                "returned_payments",
            )
            .select_related(
                "activity",
                "user",
            )
            .annotate(
                random_number=Random(),
                activity__organization__id=Coalesce(
                    F("activity__organization_id"),
                    F("activity__activity_type__organization_id"),
                ),
            )
        )

    @attributes(short_description=_("Approve selected registrations"))
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

    @attributes(short_description=_("Refuse selected registrations"))
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

    @attributes(short_description=_("Request payment for selected registrations"))
    def request_payment(self, request, queryset):
        for registration in queryset.all():
            registration.request_payment(request.user)
        self.message_user(request, _("Payment was requested for selected registrations."))

    @attributes(short_description=_("Offer refund for selected registrations"))
    def offer_refund(self, request, queryset):
        for registration in queryset.all():
            registration.offer_refund(request.user)
        self.message_user(request, _("Refund was offered for selected registrations."))

    @attributes(short_description=_("Generate refund requests for selected registrations"))
    def generate_refund_request(self, request, queryset):
        for registration in queryset.filter(refund_request__bank_account=None):
            registration.generate_refund_request(request.user)
        self.message_user(request, _("Refund requests were generated for selected registrations."))

    @attributes(short_description=_("Export selected registrations as invoices in XML"))
    def export_invoices_xml(self, request, queryset):
        response = SimpleTemplateResponse("leprikon/invoices.xml", {"registrations": queryset}, content_type="text/xml")
        response["Content-Disposition"] = 'attachment; filename="invoices.xml"'
        return response

    @attributes(short_description=_("Cancel selected registrations"))
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

    @attributes(short_description=_("Cancel cancelation request for selected registrations"))
    def cancel_cancelation_request(self, request, queryset):
        queryset.update(cancelation_requested=None, cancelation_requested_by=None)
        self.message_user(request, _("The cancelation requests have been removed from selected registrations."))

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        formfield = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == "activity_variant":
            limit_choices_to = {"activity__activity_type__model__exact": self.model.activity_type}
            formfield.limit_choices_to = limit_choices_to
            formfield.widget.rel.limit_choices_to = limit_choices_to
        return formfield

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        if not object_id and request.method == "POST" and "user" not in request.POST:
            return HttpResponseRedirect(
                "{}?activity_variant={}".format(request.path, request.POST.get("activity_variant", ""))
            )
        else:
            return super().changeform_view(request, object_id, form_url, extra_context)

    def get_form(self, request, obj: Optional[Registration], **kwargs):
        try:
            # first try request.POST (user may want to change the activity variant)
            request.activity_variant = ActivityVariant.objects.get(id=int(request.POST.get("activity_variant")))
        except (ActivityVariant.DoesNotExist, TypeError, ValueError):
            if obj:
                # use activity from object
                request.activity_variant = obj.activity_variant
            else:
                # try to get activity from request.GET
                try:
                    request.activity_variant = ActivityVariant.objects.get(id=int(request.GET.get("activity_variant")))
                except (Activity.DoesNotExist, TypeError, ValueError):
                    request.activity_variant = None

        request.activity = request.activity_variant and request.activity_variant.activity

        if request.activity_variant:
            kwargs["form"] = type(
                self.form.__name__,
                (self.form,),
                {"activity": request.activity, "activity_variant": request.activity_variant},
            )
        else:
            kwargs["form"] = forms.ModelForm
            kwargs["fields"] = ["activity_variant"]
        return super().get_form(request, obj, **kwargs)

    def get_inline_instances(self, request, obj=None):
        if request.activity:
            if request.activity.registration_type_participants:
                inlines = (RegistrationParticipantInlineAdmin,)
            elif request.activity.registration_type_groups:
                inlines = (RegistrationGroupInlineAdmin, RegistrationGroupMemberInlineAdmin)
            return [inline(self.model, self.admin_site) for inline in inlines] + super().get_inline_instances(
                request, obj
            )
        else:
            return []

    def save_model(self, request, obj, form, change):
        obj.activity = obj.activity_variant.activity
        if not change:
            if obj.activity.registration_type_participants:
                participants_count = int(form.data["participants-TOTAL_FORMS"])
            elif obj.activity.registration_type_groups:
                participants_count = int(form.data["group_members-TOTAL_FORMS"])
            obj.price = obj.activity_variant.get_price(participants_count)
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        if not change:
            form.instance.questions.set(form.instance.activity.all_questions)
            form.instance.agreements.set(form.instance.activity.all_registration_agreements)
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
            if obj.activity.full:
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

    @attributes(short_description=_("activity"))
    def activity_name(self, obj):
        return obj.activity.name

    @attributes(short_description=_("decision"))
    def decision(self, obj):
        if obj.approved or obj.canceled:
            return mark_safe(
                '<a href="{}">{}</a>'.format(
                    reverse(
                        "admin:{}_{}_event_pdf".format(self.model._meta.app_label, self.model._meta.model_name),
                        args=(obj.id, "decision"),
                    ),
                    _("admission decision") if obj.approved else _("refusal decision"),
                )
            )

    created_with_by = datetime_with_by("created", _("time of registration"))

    approved_with_by = datetime_with_by("approved", _("time of approval"))

    payment_requested_with_by = datetime_with_by("payment_requested", _("payment request time"))

    refund_offered_with_by = datetime_with_by("refund_offered", _("refund offer time"))

    cancelation_requested_with_by = datetime_with_by("cancelation_requested", _("time of cancellation request"))

    canceled_with_by = datetime_with_by("canceled", _("time of cancellation"))

    def get_message_recipients(self, request, queryset):
        return get_user_model().objects.filter(leprikon_registrations__in=queryset).distinct()

    @attributes(admin_order_field="random_number", short_description=_("random number"))
    def random_number(self, obj):
        return int(obj.random_number * 1000000000000)

    @attributes(short_description=_("received payments"))
    def received_payments(self, obj: Registration):
        return mark_safe(
            format_html(
                '<a style="color: {color}" href="{href_list}" title="{title}"><b>{amount}</b></a>'
                ' &nbsp; <a class="popup-link" href="{href_add}" style="background-position: 0 0" title="{title_add}">'
                '<img src="{icon_add}" alt="+"/></a>',
                amount=currency(obj.payment_status.received),
                color=obj.payment_status.color,
                href_add=reverse("admin:leprikon_receivedpayment_add") + f"?target_registration={obj.id}",
                href_list=reverse("admin:leprikon_receivedpayment_changelist") + f"?target_registration={obj.id}",
                icon_add=static("admin/img/icon-addlink.svg"),
                title=obj.payment_status.title,
                title_add=_("add received payment"),
            )
        )

    @attributes(short_description=_("returned payments"))
    def returned_payments(self, obj: Registration):
        return mark_safe(
            format_html(
                '<a href="{href_list}"><b>{amount}</b></a>'
                ' &nbsp; <a class="popup-link" href="{href_add}" style="background-position: 0 0" title="{title_add}">'
                '<img src="{icon_add}" alt="+"/></a>',
                amount=currency(obj.payment_status.returned),
                href_add=reverse("admin:leprikon_returnedpayment_add") + f"?source_registration={obj.id}",
                href_list=reverse("admin:leprikon_returnedpayment_changelist") + f"?source_registration={obj.id}",
                icon_add=static("admin/img/icon-addlink.svg"),
                title_add=_("add returned payment"),
            )
        )

    @attributes(short_description=_("total price"))
    def total_price(self, obj: Registration):
        return currency(obj.payment_status.receivable)


@admin.register(Registration)
class RegistrationAdmin(AdminExportMixin, SendMessageAdminMixin, ChangeformRedirectMixin, admin.ModelAdmin):
    """Hidden admin used for raw id fields"""

    actions = SendMessageAdminMixin.actions + AdminExportMixin.actions
    list_display = (
        "id",
        "variable_symbol",
        "activity",
        "participants_list_html",
        "group",
        "created",
        "canceled",
    )
    list_filter = (
        ("activity__school_year", SchoolYearListFilter),
        "activity__department",
        ("activity__activity_type", ActivityTypeListFilter),
        ApprovedListFilter,
        CanceledListFilter,
        ("activity", ActivityListFilter),
        ("activity__leaders", LeaderListFilter),
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

    def lookup_allowed(self, lookup: str, value: str) -> bool:
        return lookup in (
            "participants__birth_date",
            "participants__birth_num",
            "participants__first_name",
            "participants__last_name",
        ) or super().lookup_allowed(lookup, value)

    def get_model_perms(self, request):
        return {}

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        return {}


class ActivityDiscountBaseAdmin(TransactionAdminMixin, AdminExportMixin, admin.ModelAdmin):
    list_filter = (
        ("registration__activity__school_year", SchoolYearListFilter),
        "registration__activity__department",
        ("registration__activity__activity_type", ActivityTypeListFilter),
        ("registration__activity", ActivityListFilter),
        ("registration__activity__leaders", LeaderListFilter),
    )
    search_fields = (
        "registration__variable_symbol",
        "registration__activity__name",
        "registration__participants__first_name",
        "registration__participants__last_name",
        "registration__participants__birth_num",
    )
    raw_id_fields = ("registration",)
    closed_fields = ("accounted", "registration", "amount")

    @attributes(short_description=_("activity"))
    def activity(self, obj):
        return obj.registration.activity

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


class PaymentAdminMixin:
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

    @attributes(short_description=_("variable symbol"))
    def variable_symbol(self, obj):
        return obj.registration.variable_symbol


@admin.register(ReceivedPayment)
class ReceivedPaymentAdmin(PaymentAdminMixin, TransactionBaseAdmin):
    exclude = ("donor", "organization")
    list_filter = (
        ("target_registration__activity__school_year", SchoolYearListFilter),
        ("transaction_type", TransactionTypeListFilter),
        "target_registration__activity__department",
        ("target_registration__activity__activity_type", ActivityTypeListFilter),
        ("target_registration__activity", ActivityListFilter),
        ("target_registration__activity__leaders", LeaderListFilter),
    )
    search_fields = (
        "target_registration__activity__name",
        "target_registration__participants__first_name",
        "target_registration__participants__last_name",
        "target_registration__participants__birth_num",
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["target_registration"].required = True
        return form


@admin.register(ReturnedPayment)
class ReturnedPaymentAdmin(PaymentAdminMixin, TransactionBaseAdmin):
    exclude = ("pays_payment",)
    list_filter = (
        ("source_registration__activity__school_year", SchoolYearListFilter),
        ("transaction_type", TransactionTypeListFilter),
        "source_registration__activity__department",
        ("source_registration__activity__activity_type", ActivityTypeListFilter),
        ("source_registration__activity", ActivityListFilter),
        ("source_registration__activity__leaders", LeaderListFilter),
    )
    search_fields = (
        "source_registration__activity__name",
        "source_registration__participants__first_name",
        "source_registration__participants__last_name",
        "source_registration__participants__birth_num",
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["source_registration"].required = True
        return form

    @attributes(admin_order_field="amount", short_description=_("amount"))
    def amount_html(self, obj):
        return mark_safe(
            format_html(
                '<b style="color: {color}">{amount}</b>',
                color=amount_color(-obj.amount),
                amount=currency(obj.amount),
            )
        )
