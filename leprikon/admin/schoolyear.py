from django import forms
from django.contrib import admin
from django.db import IntegrityError
from django.shortcuts import render
from django.utils.translation import ugettext_lazy as _

from ..models.schoolyear import SchoolYear, SchoolYearDivision, SchoolYearPeriod
from .filters import SchoolYearListFilter


@admin.register(SchoolYear)
class SchoolYearAdmin(admin.ModelAdmin):
    list_display = ("name", "active")
    list_editable = ("active",)

    # do not allow to delete entries in admin
    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return obj and ("year",) or ()

    def get_actions(self, request):
        actions = super().get_actions(request)
        if "delete_selected" in actions:
            del actions["delete_selected"]
        return actions


class SchoolYearPeriodInlineAdmin(admin.TabularInline):
    model = SchoolYearPeriod
    extra = 0
    min_num = 1


@admin.register(SchoolYearDivision)
class SchoolYearDivisionAdmin(admin.ModelAdmin):
    actions = ("copy_to_school_year",)
    inlines = (SchoolYearPeriodInlineAdmin,)
    list_display = ("name",)
    list_filter = (("school_year", SchoolYearListFilter),)

    def copy_to_school_year(self, request, queryset):
        class SchoolYearForm(forms.Form):
            school_year = forms.ModelChoiceField(
                label=_("Target school year"),
                help_text=_("All selected school year divisions will be copied to selected school year."),
                queryset=SchoolYear.objects.all(),
            )

        if request.POST.get("post", "no") == "yes":
            form = SchoolYearForm(request.POST)
            if form.is_valid():
                school_year = form.cleaned_data["school_year"]
                for school_year_division in queryset.all():
                    try:
                        school_year_division.copy_to_school_year(school_year)
                    except IntegrityError:
                        # division already exists for target year
                        pass
                self.message_user(
                    request,
                    _("Selected school year divisions were copied to school year {}.").format(school_year),
                )
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

    copy_to_school_year.short_description = _("Copy selected school year divisions to another school year")

    def get_readonly_fields(self, request, obj=None):
        return ("school_year",) if obj else ()
