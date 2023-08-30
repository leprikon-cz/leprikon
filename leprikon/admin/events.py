from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import AdminRadioSelect
from django.shortcuts import render
from django.templatetags.static import static
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from ..models.events import Event, EventDiscount, EventRegistration
from ..models.schoolyear import SchoolYear
from ..models.subjects import SubjectType
from ..utils import attributes, currency
from .pdf import PdfExportAdminMixin
from .subjects import SubjectBaseAdmin, SubjectDiscountBaseAdmin, SubjectRegistrationBaseAdmin


@admin.register(Event)
class EventAdmin(SubjectBaseAdmin):
    subject_type_type = SubjectType.EVENT
    registration_model = EventRegistration
    actions = SubjectBaseAdmin.actions + (
        "publish",
        "unpublish",
        "copy_to_school_year",
    )
    list_display = (
        "id",
        "code",
        "name",
        "subject_type",
        "get_groups_list",
        "get_leaders_list",
        "get_times_list",
        "event_date",
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
        "subject_type",
        "registration_type",
        "get_groups_list",
        "get_leaders_list",
        "get_age_groups_list",
        "get_target_groups_list",
        "get_times_list",
        "start_date",
        "start_time",
        "end_date",
        "end_time",
        "place",
        "public",
        "min_registrations_count",
        "max_registrations_count",
        "get_approved_registrations_count",
        "get_unapproved_registrations_count",
        "note",
    )
    date_hierarchy = "start_date"

    @attributes(short_description=_("Publish selected events"))
    def publish(self, request, queryset):
        Event.objects.filter(id__in=[reg["id"] for reg in queryset.values("id")]).update(public=True)
        self.message_user(request, _("Selected events were published."))

    @attributes(short_description=_("Unpublish selected events"))
    def unpublish(self, request, queryset):
        Event.objects.filter(id__in=[reg["id"] for reg in queryset.values("id")]).update(public=False)
        self.message_user(request, _("Selected events were unpublished."))

    @attributes(short_description=_("Copy selected events to another school year"))
    def copy_to_school_year(self, request, queryset):
        class SchoolYearForm(forms.Form):
            school_year = forms.ModelChoiceField(
                label=_("Target school year"),
                help_text=_("All selected events will be copied to selected school year."),
                queryset=SchoolYear.objects.all(),
            )

        if request.POST.get("post", "no") == "yes":
            form = SchoolYearForm(request.POST)
            if form.is_valid():
                school_year = form.cleaned_data["school_year"]
                for event in queryset.all():
                    event.copy_to_school_year(school_year)
                self.message_user(request, _("Selected events were copied to school year {}.").format(school_year))
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


@admin.register(EventRegistration)
class EventRegistrationAdmin(PdfExportAdminMixin, SubjectRegistrationBaseAdmin):
    subject_type_type = SubjectType.EVENT
    actions = SubjectRegistrationBaseAdmin.actions + PdfExportAdminMixin.actions + ("add_discounts",)

    @attributes(short_description=_("Add discounts to selected registrations"))
    def add_discounts(self, request, queryset):
        ABSOLUTE = "A"
        RELATIVE = "R"

        class DiscountForm(forms.Form):
            discount_type = forms.ChoiceField(
                label=_("Discount type"),
                choices=((ABSOLUTE, _("absolute amount")), (RELATIVE, _("relative amount in percents"))),
                widget=AdminRadioSelect(),
            )
            amount = forms.DecimalField(label=_("Amount or number of percents"))
            explanation = EventDiscount._meta.get_field("explanation").formfield()

        if request.POST.get("post", "no") == "yes":
            form = DiscountForm(request.POST)
            if form.is_valid():
                EventDiscount.objects.bulk_create(
                    EventDiscount(
                        registration=registration,
                        amount=(
                            form.cleaned_data["amount"]
                            if form.cleaned_data["discount_type"] == ABSOLUTE
                            else (registration.price - sum(discount.amount for discount in registration.all_discounts))
                            * form.cleaned_data["amount"]
                            / 100
                        ),
                        explanation=form.cleaned_data["explanation"],
                    )
                    for registration in queryset.all()
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
    def discounts(self, obj: EventRegistration):
        return mark_safe(
            format_html(
                '<a href="{href_list}"><b>{amount}</b></a>'
                ' &nbsp; <a class="popup-link" href="{href_add}" style="background-position: 0 0" title="{title_add}">'
                '<img src="{icon_add}" alt="+"/></a>',
                href_list=reverse("admin:leprikon_eventdiscount_changelist") + f"?registration={obj.id}",
                amount=currency(obj.payment_status.discount),
                href_add=reverse("admin:leprikon_eventdiscount_add") + f"?registration={obj.id}",
                icon_add=static("admin/img/icon-addlink.svg"),
                title_add=_("add discount"),
            )
        )

    @attributes(short_description=_("discounts"))
    def discounts_export(self, obj: EventRegistration):
        return currency(obj.payment_status.discount)

    @attributes(short_description=_("total price"))
    def total_price_export(self, obj: EventRegistration):
        return currency(obj.payment_status.receivable)

    @attributes(short_description=_("received payments"))
    def received_payments_export(self, obj: EventRegistration):
        return currency(obj.payment_status.received)


@admin.register(EventDiscount)
class EventDiscountAdmin(SubjectDiscountBaseAdmin):
    actions = SubjectDiscountBaseAdmin.actions
    list_display = ("accounted", "registration", "subject", "amount_html", "explanation")
    list_export = ("accounted", "registration", "subject", "amount", "explanation")
