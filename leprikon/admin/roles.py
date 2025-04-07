from adminsortable2.admin import SortableInlineAdminMixin
from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.shortcuts import render
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from ..models.activities import ActivityModel
from ..models.roles import Contact, Leader
from ..models.schoolyear import SchoolYear
from ..utils import attributes
from .export import AdminExportMixin
from .filters import SchoolYearListFilter
from .messages import SendMessageAdminMixin


class ContactInlineAdmin(SortableInlineAdminMixin, admin.TabularInline):
    model = Contact
    extra = 0


@admin.register(Leader)
class LeaderAdmin(AdminExportMixin, SendMessageAdminMixin, admin.ModelAdmin):
    actions = SendMessageAdminMixin.actions + AdminExportMixin.actions + ("add_school_year",)
    filter_horizontal = ("school_years",)
    inlines = (ContactInlineAdmin,)
    search_fields = ("user__first_name", "user__last_name", "contacts__contact")
    list_display = (
        "id",
        "first_name",
        "last_name",
        "email",
        "courses_link",
        "events_link",
        "orderables_link",
        "contacts",
        "user_link",
        "icon",
    )
    list_export = (
        "id",
        "user__first_name",
        "user__last_name",
        "user__email",
        "contacts__contact_type",
        "contacts__contact",
        "contacts__public",
    )
    ordering = ("user__first_name", "user__last_name")
    list_filter = (("school_years", SchoolYearListFilter),)
    raw_id_fields = ("user",)

    @attributes(short_description=_("Add selected leaders to another school year"))
    def add_school_year(self, request, queryset):
        class SchoolYearForm(forms.Form):
            school_year = forms.ModelChoiceField(
                label=_("Target school year"),
                help_text=_("All selected leaders will be added to selected school year."),
                queryset=SchoolYear.objects.all(),
            )

        if request.POST.get("post", "no") == "yes":
            form = SchoolYearForm(request.POST)
            if form.is_valid():
                school_year = form.cleaned_data["school_year"]
                for leader in queryset.all():
                    leader.school_years.add(school_year)
                self.message_user(request, _("Selected leaders were added to school year {}.").format(school_year))
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
                action="add_school_year",
                action_checkbox_name=admin.helpers.ACTION_CHECKBOX_NAME,
                select_across=request.POST["select_across"],
                selected=request.POST.getlist(admin.helpers.ACTION_CHECKBOX_NAME),
            ),
        )

    @attributes(admin_order_field="user__first_name", short_description=_("first name"))
    def first_name(self, obj):
        return obj.user.first_name

    @attributes(admin_order_field="user__last_name", short_description=_("last name"))
    def last_name(self, obj):
        return obj.user.last_name

    @attributes(admin_order_field="user__email", short_description=_("email"))
    def email(self, obj):
        return obj.user.email

    @attributes(short_description=_("contacts"))
    def contacts(self, obj):
        return ", ".join(c.contact for c in obj.all_contacts)

    @attributes(short_description=_("user"))
    def user_link(self, obj):
        return mark_safe(
            '<a href="{url}">{user}</a>'.format(
                url=reverse(
                    f"admin:{obj.user._meta.app_label}_{obj.user._meta.model_name}_change", args=(obj.user.id,)
                ),
                user=obj.user,
            )
        )

    @cached_property
    def courses_url(self):
        return reverse("admin:leprikon_course_changelist")

    @cached_property
    def events_url(self):
        return reverse("admin:leprikon_event_changelist")

    @cached_property
    def orderables_url(self):
        return reverse("admin:leprikon_orderable_changelist")

    @attributes(short_description=_("courses"))
    def courses_link(self, obj):
        return mark_safe(
            '<a href="{url}?leaders__id={leader}">{count}</a>'.format(
                url=self.courses_url,
                leader=obj.id,
                count=obj.activities.filter(activity_type__model=ActivityModel.COURSE).count(),
            )
        )

    @attributes(short_description=_("events"))
    def events_link(self, obj):
        return mark_safe(
            '<a href="{url}?leaders__id={leader}">{count}</a>'.format(
                url=self.events_url,
                leader=obj.id,
                count=obj.activities.filter(activity_type__model=ActivityModel.EVENT).count(),
            )
        )

    @attributes(short_description=_("orderable events"))
    def orderables_link(self, obj):
        return mark_safe(
            '<a href="{url}?leaders__id={leader}">{count}</a>'.format(
                url=self.orderables_url,
                leader=obj.id,
                count=obj.activities.filter(activity_type__model=ActivityModel.ORDERABLE).count(),
            )
        )

    @attributes(short_description=_("photo"))
    def icon(self, obj):
        try:
            return mark_safe('<img src="{}" alt="{}"/>'.format(obj.photo.icons["48"], obj.photo.label))
        except (AttributeError, KeyError):
            return ""

    def get_message_recipients(self, request, queryset):
        return (
            get_user_model()
            .objects.filter(
                leprikon_leader__in=queryset,
            )
            .distinct()
        )
