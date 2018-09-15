from django.contrib import messages
from django.core.urlresolvers import reverse_lazy as reverse
from django.utils.http import is_safe_url
from django.utils.translation import ugettext_lazy as _
from django.views.generic import (
    CreateView as _CreateView, DeleteView as _DeleteView,
    DetailView as _DetailView, FormView as _FormView, ListView as _ListView,
    TemplateView as _TemplateView, UpdateView as _UpdateView,
)

from ..conf import settings
from ..forms.confirm import ConfirmForm


class GenericViewMixin(object):
    title       = ''

    def get_context_data(self, *args, **kwargs):
        context = super(GenericViewMixin, self).get_context_data(
            *args,
            placeholder = self.__class__.__name__,
            title       = self.get_title(),
            **kwargs
        )
        return context

    def get_title(self):
        return self.title



class ListView(GenericViewMixin, _ListView):
    template_name       = 'leprikon/list.html'
    add_url             = None
    add_label           = _('add')
    add_title           = ''
    message_empty       = _('No items found.')
    preview_template    = ''

    def get_add_url(self):
        return self.add_url

    def get_add_label(self):
        return self.add_label

    def get_add_title(self):
        return self.add_title

    def get_message_empty(self):
        return self.message_empty

    def get_context_data(self, *args, **kwargs):
        return super(ListView, self).get_context_data(
            *args,
            preview_template = self.preview_template,
            add_url = self.get_add_url(),
            add_label = self.get_add_label(),
            add_title = self.get_add_title(),
            message_empty = self.get_message_empty(),
            **kwargs
        )



class FilteredListView(ListView):
    form_class      = None
    message_empty   = _('No items found matching given search parameters.')

    def get_form(self):
        return self.form_class(data=self.request.GET)

    def get_context_data(self, *args, **kwargs):
        return super(FilteredListView, self).get_context_data(*args, form=self.get_form(), **kwargs)



class BackViewMixin(object):
    back_url    = reverse('leprikon:summary')
    back_label  = _('Back')

    def get_context_data(self, *args, **kwargs):
        return super(BackViewMixin, self).get_context_data(
            *args,
            back_url        = self.get_back_url(),
            back_label      = self.get_back_label(),
            **kwargs
        )

    def get_back_label(self):
        return self.back_label

    def get_back_url(self):
        url = self.request.POST.get(settings.LEPRIKON_PARAM_BACK,
                                    self.request.GET.get(settings.LEPRIKON_PARAM_BACK, ''))
        if is_safe_url(url=url, host=self.request.get_host()):
            return url
        else:
            return self.back_url



class FormViewMixin(BackViewMixin, GenericViewMixin):
    template_name   = 'leprikon/form.html'
    form_item_template_name = 'leprikon/form_item.html'
    instructions    = ''
    submit_label    = _('Save')
    success_url     = reverse('leprikon:summary')
    message         = None

    def get_context_data(self, *args, **kwargs):
        return super(FormViewMixin, self).get_context_data(
            *args,
            form_item_template = self.get_form_item_template_name(),
            instructions    = self.get_instructions(),
            submit_label    = self.get_submit_label(),
            **kwargs
        )

    def get_form_item_template_name(self):
        return self.form_item_template_name

    def get_instructions(self):
        return self.instructions

    def get_submit_label(self):
        return self.submit_label

    def get_success_url(self):
        return self.get_back_url()

    def get_message(self):
        return self.message

    def form_valid(self, form):
        response = super(FormViewMixin, self).form_valid(form)
        message = self.get_message()
        if message:
            messages.info(
                self.request,
                message,
            )
        return response



class GetFormViewMixin(FormViewMixin):
    def get_form_kwargs(self):
        return {
            'data': self.request.GET,
            'prefix': self.get_prefix(),
        }

    def get(self, reqest, *args, **kwargs):
        return self.post(self, reqest, *args, **kwargs)



class ConfirmFormViewMixin(FormViewMixin):
    form_class      = ConfirmForm
    template_name   = 'leprikon/confirm_form.html'
    question        = ''
    submit_label    = _('Yes')

    def get_question(self):
        return self.question

    def get_context_data(self, *args, **kwargs):
        return super(ConfirmFormViewMixin, self).get_context_data(*args, question=self.get_question(), **kwargs)

    def form_valid(self, form):
        self.confirmed()
        return super(ConfirmFormViewMixin, self).form_valid(form)

    def confirmed(self):
        pass



class DetailView(GenericViewMixin, _DetailView):
    pass



class CreateView(FormViewMixin, _CreateView):
    pass



class ConfirmCreateView(ConfirmFormViewMixin, _CreateView):
    pass



class UpdateView(FormViewMixin, _UpdateView):
    pass



class ConfirmUpdateView(ConfirmFormViewMixin, _UpdateView):
    pass



class DeleteView(ConfirmFormViewMixin, _DeleteView):
    submit_label = _('Delete')

    def delete(self, request, *args, **kwargs):
        response = super(DeleteView, self).delete(request, *args, **kwargs)
        message = self.get_message()
        if message:
            messages.info(
                self.request,
                message,
            )
        return response



class FormView(FormViewMixin, _FormView):
    pass



class GetFormView(GetFormViewMixin, _FormView):
    pass



class TemplateView(GenericViewMixin, _TemplateView):
    pass
