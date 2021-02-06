from functools import partial

from django import forms
from django.contrib import admin, messages
from django.forms.models import modelform_factory
from django.forms.widgets import CheckboxSelectMultiple
from django.shortcuts import render
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from sentry_sdk import capture_exception


class BulkUpdateMixin:
    actions = ("bulk_update",)

    bulk_update_fields = None
    bulk_update_exclude = None
    bulk_update_form = None

    @cached_property
    def BulkUpdateFieldsForm(self):
        return type(
            "BulkUpdateFieldsForm",
            (forms.Form,),
            {
                "fields": forms.MultipleChoiceField(
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

    def bulk_update(self, request, queryset):
        phase = request.POST.get("phase")
        hidden_fields = []
        # phases: None > 'fields' > 'update'
        if phase is not None:
            form = self.BulkUpdateFieldsForm(request.POST)
            if form.is_valid():
                hidden_fields = [("fields", field) for field in form.cleaned_data["fields"]]
                BulkUpdateForm = modelform_factory(
                    self.model,
                    form=self.bulk_update_form or self.form,
                    fields=form.cleaned_data["fields"],
                    formfield_callback=partial(self.formfield_for_dbfield, request=request),
                )
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
                                    _(f"Failed to update item {instance}."),
                                    messages.ERROR,
                                )
                            else:
                                num_updated += 1
                        self.message_user(request, _(f"{num_updated} items were updated."))
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

    bulk_update.short_description = _("Bulk update selected items")
