import csv

from django.contrib import admin
from django.test import TestCase, RequestFactory
from django.utils.encoding import force_text

class SimpleTest(TestCase):
    def test_exports(self):
        request = RequestFactory().post('/')  # export doesn't care about request
        for a in (a for a in admin.site._registry.values() if hasattr(a, 'export_as_csv')):
            content = a.export_as_csv(request, a.get_queryset(request)).content
            self.assertLess(0, len(content))
            content = content.decode()
            reader = csv.reader(content.strip().split('\n'))
            num_columns = len(a.get_list_export(request))
            self.assertTrue(all(len(row) == num_columns for row in reader))
