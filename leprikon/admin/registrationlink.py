from string import ascii_letters, digits

from django.contrib import admin
from django.db import transaction
from django.db.models import Count
from django.db.utils import IntegrityError
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from ..forms.registrationlink import RegistrationLinkAdminForm
from ..models.courses import CourseRegistration
from ..models.events import EventRegistration
from ..models.orderables import OrderableRegistration
from ..models.registrationlink import RegistrationLink
from ..models.subjects import SubjectType
from .export import AdminExportMixin
from .filters import SchoolYearListFilter, SubjectTypeListFilter


@admin.register(RegistrationLink)
class RegistrationLinkAdmin(AdminExportMixin, admin.ModelAdmin):
    _registration_models = {
        SubjectType.COURSE: CourseRegistration,
        SubjectType.EVENT: EventRegistration,
        SubjectType.ORDERABLE: OrderableRegistration,
    }
    list_display = (
        "id",
        "name",
        "get_link",
        "subject_type",
        "reg_from",
        "reg_to",
        "get_registrations_link",
    )
    list_filter = (
        ("school_year", SchoolYearListFilter),
        "subject_type__subject_type",
        ("subject_type", SubjectTypeListFilter),
    )
    filter_horizontal = ("subjects",)

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        if not object_id and request.method == "POST" and len(request.POST) == 3:
            return HttpResponseRedirect(
                "{}?subject_type={}".format(
                    request.path,
                    request.POST.get("subject_type", ""),
                )
            )
        else:
            return super().changeform_view(request, object_id, form_url, extra_context)

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

        if request.subject_type:
            kwargs["form"] = type(
                RegistrationLinkAdminForm.__name__,
                (RegistrationLinkAdminForm,),
                {
                    "school_year": request.school_year,
                    "subject_type": request.subject_type,
                },
            )
        else:
            kwargs["fields"] = ["subject_type"]

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

    def get_link(self, obj):
        return '<a href="{url}" title="{title}" target="_blank">{url}</a>'.format(
            url=obj.link,
            title=_("registration link"),
        )

    get_link.short_description = _("registration link")
    get_link.allow_tags = True

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("subject_type")
            .annotate(registrations_count=Count("registrations"))
        )

    def get_registrations_link(self, obj):
        registration_model = self._registration_models[obj.subject_type.subject_type]
        return format_html(
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

    get_registrations_link.short_description = _("registrations")
    get_registrations_link.allow_tags = True
