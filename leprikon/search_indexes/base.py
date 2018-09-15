from haystack import indexes


class BaseIndex(indexes.SearchIndex, indexes.Indexable):
    text        = indexes.CharField(document=True, use_template=True, template_name='leprikon/search.txt')
    title       = indexes.CharField(stored=True, indexed=False, model_attr='name')
    url         = indexes.CharField(stored=True, indexed=False)
    school_year = indexes.IntegerField(stored=True, indexed=True, model_attr='school_year_id')

    def prepare_url(self, obj):
        return obj.get_absolute_url()
