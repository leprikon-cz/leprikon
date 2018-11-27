from django.core.urlresolvers import reverse_lazy as reverse
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext_lazy as _

from ..forms.subjects import (
    CourseRegistrationForm, EventRegistrationForm, SubjectFilterForm,
    SubjectForm,
)
from ..models.courses import Course
from ..models.events import Event
from ..models.leprikonsite import LeprikonSite
from ..models.subjects import (
    Subject, SubjectPayment, SubjectRegistration, SubjectType,
)
from .generic import (
    ConfirmUpdateView, CreateView, DetailView, FilteredListView, ListView,
    UpdateView,
)


class SubjectTypeMixin(object):
    _models = {
        SubjectType.COURSE: Course,
        SubjectType.EVENT:  Event,
    }

    def get_template_names(self):
        return [
            'leprikon/{}{}.html'.format(self.subject_type.slug, self.template_name_suffix),
            'leprikon/{}{}.html'.format(self.subject_type.subject_type, self.template_name_suffix),
            'leprikon/subject{}.html'.format(self.template_name_suffix),
        ]

    def dispatch(self, request, subject_type, *args, **kwargs):
        self.subject_type = get_object_or_404(SubjectType, slug=subject_type)
        self.model = self._models[self.subject_type.subject_type]
        return super(SubjectTypeMixin, self).dispatch(request, **kwargs)

    def get_queryset(self):
        return super(SubjectTypeMixin, self).get_queryset().filter(subject_type=self.subject_type)



class SubjectListView(SubjectTypeMixin, FilteredListView):
    form_class          = SubjectFilterForm
    preview_template    = 'leprikon/subject_preview.html'
    paginate_by         = 10

    def get_title(self):
        return _('{subject_type} in school year {school_year}').format(
            subject_type    = self.subject_type.plural,
            school_year     = self.request.school_year,
        )

    def get_message_empty(self):
        return _('No {subject_type} matching given search parameters found.').format(
            subject_type = self.subject_type.plural,
        )

    def get_form(self):
        return self.form_class(
            subject_type_type   = self.subject_type.subject_type,
            subject_types       = [self.subject_type],
            school_year         = self.request.school_year,
            is_staff            = self.request.user.is_staff,
            data                = self.request.GET,
        )

    def get_queryset(self):
        return self.get_form().get_queryset()



class SubjectListMineView(SubjectListView):

    def get_template_names(self):
        return [
            'leprikon/{}_list_mine.html'.format(self.subject_type.slug),
            'leprikon/{}_list_mine.html'.format(self.subject_type.subject_type),
            'leprikon/subject_list_mine.html',
        ] + super(SubjectListMineView, self).get_template_names()

    def get_title(self):
        return _('My {subject_type} in school year {school_year}').format(
            subject_type = self.subject_type.plural,
            school_year = self.request.school_year,
        )

    def get_queryset(self):
        return super(SubjectListMineView, self).get_queryset().filter(leaders=self.request.leader)



class SubjectDetailView(SubjectTypeMixin, DetailView):

    def get_queryset(self):
        qs = super(SubjectDetailView, self).get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(public=True)
        return qs



class SubjectRegistrationsView(SubjectTypeMixin, DetailView):
    template_name_suffix = '_registrations'

    def get_queryset(self):
        qs = super(SubjectRegistrationsView, self).get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(leaders=self.request.leader)
        return qs

    def get_context_data(self, **kwargs):
        context = super(SubjectRegistrationsView, self).get_context_data(**kwargs)
        context['site'] = LeprikonSite.objects.get_current()
        return context


class SubjectUpdateView(SubjectTypeMixin, UpdateView):
    form_class  = SubjectForm

    def get_title(self):
        return _('Change {subject_type} {subject}').format(
            subject_type = self.subject_type.name_akuzativ,
            subject = self.object.name,
        )

    def get_message(self):
        return _('The changes in {subject_type} {subject} have been saved.').format(
            subject_type = self.subject_type.name_genitiv,
            subject = self.object.name,
        )

    def get_queryset(self):
        qs = super(SubjectUpdateView, self).get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(leaders=self.request.leader)
        return qs



class SubjectRegistrationFormView(CreateView):
    back_url        = reverse('leprikon:registration_list')
    submit_label    = _('Submit registration')
    message         = _('The registration has been saved. We will inform you about its further processing.')
    _models = {
        SubjectType.COURSE: Course,
        SubjectType.EVENT:  Event,
    }
    _form_classes = {
        SubjectType.COURSE: CourseRegistrationForm,
        SubjectType.EVENT:  EventRegistrationForm,
    }

    def get_template_names(self):
        return [
            'leprikon/{}_registration_form.html'.format(self.subject_type.slug, self.template_name_suffix),
            'leprikon/{}_registration_form.html'.format(self.subject_type.subject_type, self.template_name_suffix),
            'leprikon/subject_registration_form.html'.format(self.template_name_suffix),
        ]

    def get_title(self):
        return _('Registration for {subject_type} {subject}').format(
            subject_type = self.subject_type.name_akuzativ,
            subject = self.subject.name,
        )

    def dispatch(self, request, subject_type, pk, **kwargs):
        self.subject_type = get_object_or_404(SubjectType, slug=subject_type)
        lookup_kwargs = {
            'subject_type': self.subject_type,
            'id':           int(pk),
        }
        if not self.request.user.is_staff:
            lookup_kwargs['public'] = True
        self.subject = get_object_or_404(Subject, **lookup_kwargs)
        if not self.subject.registration_allowed:
            return redirect(self.subject)
        self.request.school_year = self.subject.school_year
        self.model = self._models[self.subject.subject_type.subject_type]
        return super(SubjectRegistrationFormView, self).dispatch(request, **kwargs)

    def get_form_class(self):
        return self._form_classes[self.subject.subject_type.subject_type]

    def get_form_kwargs(self):
        kwargs  = super(SubjectRegistrationFormView, self).get_form_kwargs()
        kwargs['subject'] = self.subject
        kwargs['user'] = self.request.user
        return kwargs



class UserRegistrationMixin(object):
    model = SubjectRegistration

    def get_queryset(self):
        return super(UserRegistrationMixin, self).get_queryset().filter(user=self.request.user)

    def get_template_names(self):
        return [self.template_name] if self.template_name else [
            'leprikon/{}_registration{}.html'.format(self.object.subject.subject_type.slug,
                                                     self.template_name_suffix),
            'leprikon/{}_registration{}.html'.format(self.object.subject.subject_type.subject_type,
                                                     self.template_name_suffix),
            'leprikon/subject_registration{}.html'.format(self.template_name_suffix),
        ]



class SubjectRegistrationPdfView(UserRegistrationMixin, DetailView):

    def get(self, request, *args, **kwargs):
        # get registration
        registration = self.get_object()

        # create PDF response object
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(registration.pdf_filename)

        # create basic pdf registration from rml template
        return registration.write_pdf(response)


class SubjectRegistrationCancelView(UserRegistrationMixin, ConfirmUpdateView):
    template_name_suffix = '_cancel'
    title = _('Registration cancellation request')

    def get_question(self):
        return _('Are you sure You want to cancel the registration "{}"?').format(self.object)

    def get_message(self):
        return _('The cancellation request for {} has been saved.').format(self.object)

    def confirmed(self):
        self.object.cancel_request = True
        self.object.save()


class UserPaymentMixin(object):
    model = SubjectPayment

    def get_queryset(self):
        return super(UserPaymentMixin, self).get_queryset().filter(
            registration__user=self.request.user
        ).order_by('-accounted')


class SubjectPaymentsListView(UserPaymentMixin, ListView):
    template_name = 'leprikon/payments.html'
    paginate_by = 20

    def get_title(self):
        return _('Payments')


class SubjectPaymentPdfView(UserPaymentMixin, DetailView):
    def get(self, request, *args, **kwargs):
        # get payment
        payment = self.get_object()

        # create PDF response object
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(payment.pdf_filename)

        # create basic pdf payment from rml template
        return payment.write_pdf(response)
