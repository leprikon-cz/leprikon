from django.db.migrations.operations.models import ModelOperation


class AlterModelBases(ModelOperation):
    reduce_to_sql = False
    reversible = True

    def __init__(self, name, bases):
        self.bases = bases
        super().__init__(name)

    def state_forwards(self, app_label, state):
        """
        Overwrite a models base classes with a custom list of
        bases instead, then force Django to reload the model
        with this (probably completely) different class hierarchy.
        """
        state.models[app_label, self.name_lower].bases = self.bases
        state.reload_model(app_label, self.name_lower)

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        pass

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        pass

    def describe(self):
        return "Update %s bases to %s" % (self.name, self.bases)
