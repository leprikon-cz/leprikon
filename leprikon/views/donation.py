from django.utils.translation import ugettext_lazy as _

from ..models.donation import Donation
from .generic import DetailView, ListView
from .subjects import PDFMixin


class DonationViewMixin:
    model = Donation

    def get_queryset(self):
        return super().get_queryset().filter(donor=self.request.user)


class DonationListView(DonationViewMixin, ListView):
    template_name = "leprikon/donations.html"
    paginate_by = 20

    def get_title(self):
        return _("Donations")


class DonationPdfView(DonationViewMixin, PDFMixin, DetailView):
    pass
