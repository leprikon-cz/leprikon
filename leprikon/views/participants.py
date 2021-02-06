from django.urls import reverse_lazy as reverse
from django.utils.translation import ugettext_lazy as _

from ..forms.participant import ParticipantForm
from ..models.roles import Participant
from ..utils import reverse_with_back
from .generic import CreateView, DeleteView, ListView, UpdateView


class ParticipantListView(ListView):
    add_label = _("add participant")
    model = Participant
    template_name = "leprikon/participants.html"
    preview_template = "leprikon/participant_preview.html"

    def get_title(self):
        return _("Participants and parents")

    def get_queryset(self):
        return self.request.user.leprikon_participants.all()

    def get_add_url(self):
        return reverse_with_back(self.request, "leprikon:participant_create")


class ParticipantCreateView(CreateView):
    model = Participant
    form_class = ParticipantForm
    success_url = reverse("leprikon:summary")
    title = _("New participant")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        parent = self.request.user.leprikon_parents.first()
        if parent:
            kwargs["initial"] = dict((attr, getattr(parent, attr)) for attr in ["street", "city", "postal_code"])
        return kwargs

    def get_message(self):
        return _("New participant {} has been created.").format(self.object)


class ParticipantUpdateView(UpdateView):
    model = Participant
    form_class = ParticipantForm
    success_url = reverse("leprikon:summary")
    title = _("Change participant")

    def get_queryset(self):
        # only allow to edit user's own participants
        return super().get_queryset().filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_message(self):
        return _("The participant {} has been updated.").format(self.object)


class ParticipantDeleteView(DeleteView):
    model = Participant
    title = _("Delete information about participant")
    message = _("Information about participant has been deleted.")

    def get_queryset(self):
        # only allow to delete user's own participants
        return super().get_queryset().filter(user=self.request.user)

    def get_question(self):
        return _("Do You really want to delete the information about participant: {}?").format(self.object)
