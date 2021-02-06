from django.urls import reverse_lazy as reverse
from django.utils.translation import ugettext_lazy as _

from ..forms.parent import ParentForm
from ..models.roles import Parent
from .generic import CreateView, DeleteView, UpdateView


class ParentCreateView(CreateView):
    model = Parent
    form_class = ParentForm
    success_url = reverse("leprikon:summary")
    title = _("New parent")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        if self.request.user.leprikon_parents.count() == 0:
            kwargs["initial"] = dict(
                (attr, getattr(self.request.user, attr)) for attr in ["first_name", "last_name", "email"]
            )
        return kwargs

    def get_message(self):
        return _("New parent {} has been created.").format(self.object)


class ParentUpdateView(UpdateView):
    model = Parent
    form_class = ParentForm
    success_url = reverse("leprikon:summary")
    title = _("Change parent")

    def get_queryset(self):
        # only allow to edit user's own parents
        return super().get_queryset().filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_message(self):
        return _("The parent {} has been updated.").format(self.object)


class ParentDeleteView(DeleteView):
    model = Parent
    title = _("Delete information about parent")
    message = _("Information about parent has been deleted.")

    def get_queryset(self):
        # only allow to delete user's own parents
        return super().get_queryset().filter(user=self.request.user)

    def get_question(self):
        return _("Do You really want to delete the information about parent: {}?").format(self.object)
