import csv

import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory

from leprikon.admin.export import AdminExportMixin

User = get_user_model()


class ExportModelAdmin(AdminExportMixin, admin.ModelAdmin):
    pass


@pytest.mark.skip(reason="TODO")
@pytest.mark.parametrize(
    "model_admin",
    [model_admin for model_admin in admin.site._registry.values() if issubclass(type(model_admin), AdminExportMixin)],
)
@pytest.mark.django_db
def test_exports(model_admin: ExportModelAdmin) -> None:
    request = RequestFactory().post("/")  # export doesn't care about request
    request.user = User(is_superuser=True)
    content = model_admin.export_as_csv(request, model_admin.get_queryset(request)).content
    assert 0 < len(content)
    content = content.decode()
    reader = csv.reader(content.strip().split("\n"))
    num_columns = len(model_admin.get_list_export(request))
    assert all(len(row) == num_columns for row in reader)
