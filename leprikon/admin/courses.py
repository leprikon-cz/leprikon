from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import AdminRadioSelect, FilteredSelectMultiple
from django.shortcuts import render
from django.templatetags.static import static
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from ..forms.courses import CourseDiscountAdminForm, CourseRegistrationAdminForm
from ..models.activities import ActivityModel
from ..models.courses import Course, CourseDiscount, CourseRegistration
from ..models.schoolyear import SchoolYear, SchoolYearDivision
from ..utils import attributes, currency
from .activities import ActivityBaseAdmin, ActivityDiscountBaseAdmin, RegistrationBaseAdmin
from .pdf import PdfExportAdminMixin


@admin.register(Course)
class CourseAdmin(ActivityBaseAdmin):
    activity_type_model = ActivityModel.COURSE
    registration_model = CourseRegistration
    list_display = (
        "id",
        "code",
        "name",
        "activity_type",
        "get_groups_list",
        "get_leaders_list",
        "get_times_list",
        "place",
        "get_registering_link",
        "get_registrations_link",
        "journals_link",
        "icon",
        "note",
    )
    list_export = (
        "id",
        "school_year",
        "code",
        "name",
        "department",
        "activity_type",
        "registration_type",
        "get_groups_list",
        "get_leaders_list",
        "get_age_groups_list",
        "get_target_groups_list",
        "get_times_list",
        "place",
        "public",
        "min_registrations_count",
        "max_registrations_count",
        "get_approved_registrations_count",
        "get_unapproved_registrations_count",
        "note",
    )
    actions = ActivityBaseAdmin.actions + (
        "publish",
        "unpublish",
        "copy_to_school_year",
    )

    @attributes(short_description=_("Publish selected courses"))
    def publish(self, request, queryset):
        Course.objects.filter(id__in=[reg["id"] for reg in queryset.values("id")]).update(public=True)
        self.message_user(request, _("Selected courses were published."))

    @attributes(short_description=_("Unpublish selected courses"))
    def unpublish(self, request, queryset):
        Course.objects.filter(id__in=[reg["id"] for reg in queryset.values("id")]).update(public=False)
        self.message_user(request, _("Selected courses were unpublished."))

    @attributes(short_description=_("Copy selected courses to another school year"))
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


@admin.register(CourseRegistration)
class CourseRegistrationAdmin(PdfExportAdminMixin, RegistrationBaseAdmin):
    form = CourseRegistrationAdminForm
    activity_type_model = ActivityModel.COURSE
    actions = RegistrationBaseAdmin.actions + PdfExportAdminMixin.actions + ("add_discounts",)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                "course_registration_periods",
            )
        )

    @attributes(short_description=_("Add discounts to selected registrations"))
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
                variants__activity__registrations__in=queryset,
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
                    required=False,
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
                    for registration in queryset.all()
                    for registration_period in registration.course_registration_periods.filter(
                        period__in=form.cleaned_data[f"periods_{registration.activity_variant.school_year_division_id}"]
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

    @attributes(short_description=_("discounts"))
    def discounts(self, obj: CourseRegistration):
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
        return mark_safe("<br/>".join(html))

    @attributes(short_description=_("total price"))
    def total_price(self, obj: CourseRegistration):
        html = []
        for status in obj.period_payment_statuses:
            html.append(
                format_html(
                    "{period}: <b>{amount}</b>",
                    period=status.registration_period.period.name,
                    amount=currency(status.status.receivable),
                )
            )
        return mark_safe("<br/>".join(html))

    @attributes(short_description=_("received payments"), admin_order_field="cached_balance")
    def received_payments(self, obj: CourseRegistration):
        html = []
        for period in obj.period_payment_statuses:
            html.append(
                format_html(
                    '{period}: <a style="color: {color}" href="{href}" title="{title}">' "<b>{amount}</b></a>",
                    period=period.registration_period.period.name,
                    color=period.status.color,
                    href=reverse("admin:leprikon_receivedpayment_changelist") + f"?target_registration={obj.id}",
                    title=period.status.title,
                    amount=currency(period.status.received),
                )
                + format_html(
                    '<a class="popup-link" href="{href}" style="background-position: 0 0" title="{title}">'
                    '<img src="{icon}" alt="+"/></a>',
                    href=reverse("admin:leprikon_receivedpayment_add") + f"?target_registration={obj.id}",
                    title=_("add payment"),
                    icon=static("admin/img/icon-addlink.svg"),
                )
            )
        return mark_safe("<br/>".join(html))

    @attributes(short_description=_("discounts"))
    def discounts_export(self, obj: CourseRegistration):
        return "\n".join(
            f"{status.registration_period.period.name}: {currency(status.status.discount)}"
            for status in obj.period_payment_statuses
        )

    @attributes(short_description=_("total price"))
    def total_price_export(self, obj: CourseRegistration):
        return "\n".join(
            f"{status.registration_period.period.name}: {currency(status.status.receivable)}"
            for status in obj.period_payment_statuses
        )

    @attributes(short_description=_("received payments"))
    def received_payments_export(self, obj: CourseRegistration):
        return "\n".join(
            f"{status.registration_period.period.name}: {currency(status.status.received)}"
            for status in obj.period_payment_statuses
        )


@admin.register(CourseDiscount)
class CourseDiscountAdmin(ActivityDiscountBaseAdmin):
    actions = ActivityDiscountBaseAdmin.actions
    form = CourseDiscountAdminForm
    list_display = ("accounted", "registration", "activity", "period", "amount_html", "explanation")
    list_export = ("accounted", "registration", "activity", "period", "amount", "explanation")
    closed_fields = ("accounted", "registration", "period", "amount")
