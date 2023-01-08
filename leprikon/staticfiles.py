from django.contrib.staticfiles.storage import ManifestStaticFilesStorage


class NotStrictManifestStaticFilesStorage(ManifestStaticFilesStorage):
    manifest_strict = False
