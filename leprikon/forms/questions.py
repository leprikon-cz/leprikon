from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from json import dumps



class QuestionsFormMixin(object):

    questions = []

    def __init__(self, *args, **kwargs):
        super(QuestionsFormMixin, self).__init__(*args, **kwargs)
        try:
            answers = kwargs['instance'].get_answers()
        except:
            answers = {}
        for q in self.questions:
            self.fields['q_'+q.name] = q.get_field(initial=answers.get(q.name, None))
            self.base_fields['q_'+q.name] = q.get_field(initial=answers.get(q.name, None))

    def save(self, commit=True):
        answers = {}
        for q in self.questions:
            answers[q.name] = self.cleaned_data['q_'+q.name]
        self.instance.answers = dumps(answers)
        return super(QuestionsFormMixin, self).save(commit)
    save.alters_data = True


