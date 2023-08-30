from functools import partial
from typing import List, Type

from django import forms
from django.contrib import admin, messages
from django.forms.models import modelform_factory
from django.forms.widgets import CheckboxSelectMultiple
from django.http import HttpRequest
from django.shortcuts import render
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from sentry_sdk import capture_exception

from ..utils import attributes


class BulkUpdateMixin:
    actions = ("bulk_update",)

    bulk_update_fields = None
    bulk_update_exclude = None

    def get_bulk_update_form(self, request: HttpRequest, fields: List[str]) -> Type[forms.ModelForm]:
        return modelform_factory(
            self.model,
            form=self.form,
            fields=fields,
            formfield_callback=partial(self.formfield_for_dbfield, request=request),
        )

    @cached_property
    def BulkUpdateFieldsForm(self):
        return type(
            "BulkUpdateFieldsForm",
            (forms.Form,),
            {
                "bulk_update_fields": forms.MultipleChoiceField(
                    label=_("Fields to update"),
                    choices=[
                        (field_name, field.label)
                        for field_name, field in forms.models.fields_for_model(
                            self.model,
                            fields=self.bulk_update_fields,
                            exclude=self.bulk_update_exclude,
                        ).items()
                    ],
                    widget=CheckboxSelectMultiple,
                ),
            },
        )

    @attributes(short_description=_("Bulk update selected items"))
    def bulk_update(self, request, queryset):
        phase = request.POST.get("phase")
        hidden_fields = []
        # phases: None > 'fields' > 'update'
        if phase is not None:
            form = self.BulkUpdateFieldsForm(request.POST)
            if form.is_valid():
                hidden_fields = [("bulk_update_fields", field) for field in form.cleaned_data["bulk_update_fields"]]
                BulkUpdateForm = self.get_bulk_update_form(request, form.cleaned_data["bulk_update_fields"])
                if phase == "update":
                    form = BulkUpdateForm(request.POST)
                    if form.is_valid():
                        num_updated = 0
                        for instance in queryset.all():
                            try:
                                instance_form = BulkUpdateForm(request.POST, request.FILES, instance=instance)
                                assert instance_form.is_valid()
                                instance_form.save()
                            except Exception:
                                capture_exception()
                                self.message_user(
                                    request,
                                    _("Failed to update item {}.").format(instance),
                                    messages.ERROR,
                                )
                            else:
                                num_updated += 1
                        self.message_user(request, _("{} items were updated.").format(num_updated))
                        return
                else:
                    form = BulkUpdateForm()
                    phase = "update"
        else:
            form = self.BulkUpdateFieldsForm()
            phase = "fields"
        hidden_fields.append(("phase", phase))
        return render(
            request,
            "leprikon/admin/bulk_update_form.html",
            {
                "title": _("Bulk update"),
                "queryset": queryset,
                "opts": self.model._meta,
                "form": form,
                "media": self.media + form.media,
                "action": "bulk_update",
                "action_checkbox_name": admin.helpers.ACTION_CHECKBOX_NAME,
                "hidden_fields": hidden_fields,
            },
        )
