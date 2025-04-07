from string import ascii_letters, digits

from django.contrib import admin
from django.db import transaction
from django.db.models import Count
from django.db.utils import IntegrityError
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from ..forms.registrationlink import RegistrationLinkAdminForm
from ..models.activities import ActivityModel, ActivityType
from ..models.courses import CourseRegistration
from ..models.events import EventRegistration
from ..models.orderables import OrderableRegistration
from ..models.registrationlink import RegistrationLink
from ..utils import attributes
from .export import AdminExportMixin
from .filters import ActivityTypeListFilter, SchoolYearListFilter


@admin.register(RegistrationLink)
class RegistrationLinkAdmin(AdminExportMixin, admin.ModelAdmin):
    _registration_models = {
        ActivityModel.COURSE: CourseRegistration,
        ActivityModel.EVENT: EventRegistration,
        ActivityModel.ORDERABLE: OrderableRegistration,
    }
    list_display = (
        "id",
        "name",
        "get_link",
        "activity_type",
        "reg_from",
        "reg_to",
        "get_registrations_link",
    )
    list_filter = (
        ("school_year", SchoolYearListFilter),
        "activity_type__model",
        ("activity_type", ActivityTypeListFilter),
    )
    filter_horizontal = ("activity_variants",)

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        if not object_id and request.method == "POST" and len(request.POST) == 3:
            return HttpResponseRedirect(
                "{}?activity_type={}".format(
                    request.path,
                    request.POST.get("activity_type", ""),
                )
            )
        else:
            return super().changeform_view(request, object_id, form_url, extra_context)

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

        if request.activity_type:
            kwargs["form"] = type(
                RegistrationLinkAdminForm.__name__,
                (RegistrationLinkAdminForm,),
                {
                    "school_year": request.school_year,
                    "activity_type": request.activity_type,
                },
            )
        else:
            kwargs["fields"] = ["activity_type"]

        return super().get_form(request, obj, **kwargs)

    def save_form(self, request, form, change):
        obj = super().save_form(request, form, change)
        obj.school_year = request.school_year
        return obj

    def save_model(self, request, obj, form, change):
        if change:
            obj.save()
        else:
            obj.school_year = request.school_year
            while not obj.id:
                try:
                    with transaction.atomic():
                        obj.slug = get_random_string(64, ascii_letters + digits)
                        obj.save()
                except IntegrityError:
                    pass

    @attributes(short_description=_("registration link"))
    def get_link(self, obj):
        return mark_safe(
            '<a href="{url}" title="{title}" target="_blank">{url}</a>'.format(
                url=obj.link,
                title=_("registration link"),
            )
        )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("activity_type")
            .annotate(registrations_count=Count("registrations"))
        )

    @attributes(short_description=_("registrations"))
    def get_registrations_link(self, obj):
        registration_model = self._registration_models[obj.activity_type.model]
        return mark_safe(
            format_html(
                '<a href="{url}">{count}</a>',
                url=reverse(
                    "admin:{}_{}_changelist".format(
                        registration_model._meta.app_label,
                        registration_model._meta.model_name,
                    )
                )
                + "?registration_link__id__exact={}".format(obj.id),
                count=obj.registrations_count,
            )
        )
