from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import AdminRadioSelect, FilteredSelectMultiple
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.db.models import F
from django.shortcuts import render
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from ..forms.courses import CourseDiscountAdminForm, CourseRegistrationAdminForm
from ..models.courses import Course, CourseDiscount, CourseRegistration, CourseRegistrationHistory, CourseTime
from ..models.schoolyear import SchoolYear, SchoolYearDivision
from ..models.subjects import SubjectType
from ..utils import currency
from .pdf import PdfExportAdminMixin
from .subjects import SubjectBaseAdmin, SubjectDiscountBaseAdmin, SubjectRegistrationBaseAdmin


class CourseTimeInlineAdmin(admin.TabularInline):
    model = CourseTime
    extra = 0


@admin.register(Course)
class CourseAdmin(SubjectBaseAdmin):
    subject_type_type = SubjectType.COURSE
    registration_model = CourseRegistration
    list_display = (
        "id",
        "code",
        "name",
        "subject_type",
        "get_groups_list",
        "get_leaders_list",
        "get_times_list",
        "place",
        "public",
        "registration_allowed_icon",
        "get_registrations_link",
        "get_journal_link",
        "icon",
        "note",
    )
    list_export = (
        "id",
        "school_year",
        "code",
        "name",
        "department",
        "subject_type",
        "registration_type",
        "get_groups_list",
        "get_leaders_list",
        "get_age_groups_list",
        "get_target_groups_list",
        "get_times_list",
        "place",
        "public",
        "price",
        "min_participants_count",
        "max_participants_count",
        "min_group_members_count",
        "max_group_members_count",
        "min_registrations_count",
        "max_registrations_count",
        "get_approved_registrations_count",
        "get_unapproved_registrations_count",
        "note",
    )
    inlines = (CourseTimeInlineAdmin,) + SubjectBaseAdmin.inlines
    actions = (
        "publish",
        "unpublish",
        "copy_to_school_year",
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if "school_year_division" in form.base_fields:
            # school year division choices
            school_year_division_choices = form.base_fields["school_year_division"].widget.widget.choices
            school_year_division_choices.queryset = SchoolYearDivision.objects.filter(
                school_year=obj.school_year if obj else request.school_year,
            )
            form.base_fields["school_year_division"].choices = school_year_division_choices
        return form

    def publish(self, request, queryset):
        Course.objects.filter(id__in=[reg["id"] for reg in queryset.values("id")]).update(public=True)
        self.message_user(request, _("Selected courses were published."))

    publish.short_description = _("Publish selected courses")

    def unpublish(self, request, queryset):
        Course.objects.filter(id__in=[reg["id"] for reg in queryset.values("id")]).update(public=False)
        self.message_user(request, _("Selected courses were unpublished."))

    unpublish.short_description = _("Unpublish selected courses")

    def copy_to_school_year(self, request, queryset):
        class SchoolYearForm(forms.Form):
            school_year = forms.ModelChoiceField(
                label=_("Target school year"),
                help_text=_("All selected courses will be copied to selected school year."),
                queryset=SchoolYear.objects.all(),
            )

        if request.POST.get("post", "no") == "yes":
            form = SchoolYearForm(request.POST)
            if form.is_valid():
                school_year = form.cleaned_data["school_year"]
                for course in queryset.all():
                    course.copy_to_school_year(school_year)
                self.message_user(request, _("Selected courses were copied to school year {}.").format(school_year))
                return
        else:
            form = SchoolYearForm()

        adminform = admin.helpers.AdminForm(
            form,
            [(None, {"fields": list(form.base_fields)})],
            {},
            None,
            model_admin=self,
        )

        return render(
            request,
            "leprikon/admin/action_form.html",
            dict(
                title=_("Select target school year"),
                opts=self.model._meta,
                adminform=adminform,
                media=self.media + adminform.media,
                action="copy_to_school_year",
                action_checkbox_name=admin.helpers.ACTION_CHECKBOX_NAME,
                select_across=request.POST["select_across"],
                selected=request.POST.getlist(admin.helpers.ACTION_CHECKBOX_NAME),
            ),
        )

    copy_to_school_year.short_description = _("Copy selected courses to another school year")

    def get_message_recipients(self, request, queryset):
        return (
            get_user_model()
            .objects.filter(
                leprikon_registrations__subject__in=queryset,
            )
            .distinct()
        )


class CourseRegistrationHistoryInlineAdmin(admin.TabularInline):
    model = CourseRegistrationHistory
    extra = 0
    readonly_fields = ("course",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CourseRegistration)
class CourseRegistrationAdmin(PdfExportAdminMixin, SubjectRegistrationBaseAdmin):
    form = CourseRegistrationAdminForm
    subject_type_type = SubjectType.COURSE
    actions = ("add_discounts",)
    inlines = SubjectRegistrationBaseAdmin.inlines + (CourseRegistrationHistoryInlineAdmin,)
    list_display = (
        "variable_symbol",
        "download_tag",
        "subject_name",
        "participants_list_html",
        "price",
        "course_discounts",
        "course_payments",
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

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                "course_registration_periods",
            )
        )

    def add_discounts(self, request, queryset):
        ABSOLUTE = "A"
        RELATIVE = "R"

        class DiscountBaseForm(forms.Form):
            discount_type = forms.ChoiceField(
                label=_("Discount type"),
                choices=((ABSOLUTE, _("absolute amount")), (RELATIVE, _("relative amount in percents"))),
                widget=AdminRadioSelect(),
            )
            amount = forms.DecimalField(label=_("Amount or number of percents"))
            explanation = CourseDiscount._meta.get_field("explanation").formfield()

        school_year_divisions = {
            school_year_division.id: school_year_division
            for school_year_division in SchoolYearDivision.objects.filter(
                courses__registrations__in=queryset,
            ).distinct()
        }

        label = _("Periods of school year division: {school_year_division}")
        DiscountForm = type(
            "DiscountForm",
            (DiscountBaseForm,),
            {
                f"periods_{school_year_division.id}": forms.ModelMultipleChoiceField(
                    label=label.format(
                        school_year_division=school_year_division.name,
                    ),
                    queryset=school_year_division.periods.all(),
                    widget=FilteredSelectMultiple(
                        verbose_name=label.format(
                            school_year_division=school_year_division.name,
                        ),
                        is_stacked=False,
                    ),
                )
                for school_year_division in school_year_divisions.values()
            },
        )
        if request.POST.get("post", "no") == "yes":
            form = DiscountForm(request.POST)
            if form.is_valid():
                CourseDiscount.objects.bulk_create(
                    CourseDiscount(
                        registration=registration,
                        registration_period=registration_period,
                        amount=(
                            form.cleaned_data["amount"]
                            if form.cleaned_data["discount_type"] == ABSOLUTE
                            else (
                                registration.price
                                - sum(
                                    discount.amount
                                    for discount in registration.all_discounts
                                    if discount.registration_period_id == registration_period.id
                                )
                            )
                            * form.cleaned_data["amount"]
                            / 100
                        ),
                        explanation=form.cleaned_data["explanation"],
                    )
                    for registration in queryset.annotate(
                        school_year_division_id=F("subject__course__school_year_division_id")
                    )
                    for registration_period in registration.course_registration_periods.filter(
                        period__in=form.cleaned_data[f"periods_{registration.school_year_division_id}"]
                    )
                )
                self.message_user(request, _("The discounts have been created for selected registrations."))
                return
        else:
            form = DiscountForm()

        adminform = admin.helpers.AdminForm(
            form,
            [(None, {"fields": list(form.base_fields)})],
            {},
            None,
            model_admin=self,
        )

        return render(
            request,
            "leprikon/admin/action_form.html",
            dict(
                title=_("Add discounts"),
                opts=self.model._meta,
                adminform=adminform,
                media=self.media + adminform.media,
                action="add_discounts",
                action_checkbox_name=admin.helpers.ACTION_CHECKBOX_NAME,
                select_across=request.POST["select_across"],
                selected=request.POST.getlist(admin.helpers.ACTION_CHECKBOX_NAME),
            ),
        )

    add_discounts.short_description = _("Add discounts to selected registrations")

    def course_discounts(self, obj):
        html = []
        for status in obj.period_payment_statuses:
            query = f"?registration={obj.id}&registration_period={status.registration_period.id}"
            html.append(
                format_html(
                    '{period}: <a href="{href}"><b>{amount}</b></a>',
                    period=status.registration_period.period.name,
                    href=reverse("admin:leprikon_coursediscount_changelist") + query,
                    amount=currency(status.status.discount),
                )
                + format_html(
                    '<a class="popup-link" href="{href}" style="background-position: 0 0" title="{title}">'
                    '<img src="{icon}" alt="+"/></a>',
                    href=reverse("admin:leprikon_coursediscount_add") + query,
                    title=_("add discount"),
                    icon=static("admin/img/icon-addlink.svg"),
                )
            )
        return "<br/>".join(html)

    course_discounts.allow_tags = True
    course_discounts.short_description = _("course discounts")

    def course_payments(self, obj):
        html = []
        for period in obj.period_payment_statuses:
            html.append(
                format_html(
                    '{period}: <a style="color: {color}" href="{href}" title="{title}">' "<b>{amount}</b></a>",
                    period=period.registration_period.period.name,
                    color=period.status.color,
                    href=reverse("admin:leprikon_subjectreceivedpayment_changelist") + f"?target_registration={obj.id}",
                    title=period.status.title,
                    amount=currency(period.status.paid),
                )
                + format_html(
                    '<a class="popup-link" href="{href}" style="background-position: 0 0" title="{title}">'
                    '<img src="{icon}" alt="+"/></a>',
                    href=reverse("admin:leprikon_subjectreceivedpayment_add") + f"?target_registration={obj.id}",
                    title=_("add payment"),
                    icon=static("admin/img/icon-addlink.svg"),
                )
            )
        return "<br/>".join(html)

    course_payments.allow_tags = True
    course_payments.short_description = _("course payments")


@admin.register(CourseDiscount)
class CourseDiscountAdmin(PdfExportAdminMixin, SubjectDiscountBaseAdmin):
    form = CourseDiscountAdminForm
    list_display = ("accounted", "registration", "subject", "period", "amount_html", "explanation")
    list_export = ("accounted", "registration", "subject", "period", "amount", "explanation")
    closed_fields = ("accounted", "registration", "period", "amount")
