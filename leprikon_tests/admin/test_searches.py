import pytest
from django.contrib import admin


@pytest.mark.skip(reason="TODO")
@pytest.mark.parametrize(
    "model_admin",
    [model_admin for model_admin in admin.site._registry.values() if hasattr(model_admin, "search_fields")],
)
@pytest.mark.django_db
def test_searches(model_admin: admin.ModelAdmin):
    pass  # TODO
