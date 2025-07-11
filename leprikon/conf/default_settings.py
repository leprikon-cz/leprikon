from django.utils.translation import gettext_lazy as _

PRICE_DECIMAL_PLACES = 2
PRICE_MAX_DIGITS = 10

LEPRIKON_SHOW_ACTIVITY_CODE = False

LEPRIKON_COUNTRY = "CZ"

LEPRIKON_CONTACT_TYPES = (
    ("email", _("email")),
    ("phone", _("phone")),
    ("address", _("address")),
    ("url", _("url")),
)

LEPRIKON_COURSE_TEMPLATES = (("default", _("Default")),)

LEPRIKON_EVENT_TEMPLATES = (("default", _("Default")),)

LEPRIKON_ORDERABLE_TEMPLATES = (("default", _("Default")),)

LEPRIKON_LEADER_TEMPLATES = (("default", _("Default")),)

LEPRIKON_COURSELIST_TEMPLATES = (
    ("default", _("Default")),
    ("grouped", _("Grouped by course groups")),
)

LEPRIKON_EVENTLIST_TEMPLATES = (
    ("default", _("Default")),
    ("grouped", _("Grouped by event groups")),
)

LEPRIKON_ORDERABLELIST_TEMPLATES = (
    ("default", _("Default")),
    ("grouped", _("Grouped by event groups")),
)

LEPRIKON_LEADERLIST_TEMPLATES = (("default", _("Default")),)

LEPRIKON_COLOR_POSITIVE = LEPRIKON_COLOR_PAID = "#0a0"
LEPRIKON_COLOR_NEGATIVE = LEPRIKON_COLOR_NOTPAID = "#e60"
LEPRIKON_COLOR_ZERO = LEPRIKON_COLOR_OVERPAID = "#00a"
LEPRIKON_COLOR_OVERDUE = "#e00"

LEPRIKON_QUESTION_FIELDS = {
    "boolean": {
        "name": _("boolean field"),
        "class": "django.forms.BooleanField",
    },
    "char": {
        "name": _("char field"),
        "class": "django.forms.CharField",
    },
    "text": {
        "name": _("text field"),
        "class": "leprikon.forms.fields.TextField",
    },
    "choice": {
        "name": _("choice field"),
        "class": "django.forms.ChoiceField",
    },
    "required_optional": {
        "name": _("required field with an empty option"),
        "class": "leprikon.forms.fields.RequiredOptionalField",
    },
    "date": {
        "name": _("date field"),
        "class": "django.forms.DateField",
    },
}

LEPRIKON_PARAM_BACK = "zpet"

LEPRIKON_URL = None

LEPRIKON_URL_SUMMARY = "prehled"
LEPRIKON_URL_LEADER = "pro-vedouci"
LEPRIKON_URL_CREATE_ACCOUNT = "novy-uzivatel"
LEPRIKON_URL_COURSES = "kurzy"
LEPRIKON_URL_EVENTS = "akce"
LEPRIKON_URL_ORDERABLES = "na-objednani"
LEPRIKON_URL_LEADERS = "vedouci"
LEPRIKON_URL_MESSAGES = "zpravy"
LEPRIKON_URL_TIMESHEETS = "vykazy"
LEPRIKON_URL_SUBMIT = "odevzdat"
LEPRIKON_URL_ENTRY = "zaznam"
LEPRIKON_URL_PARENT = "zastupce"
LEPRIKON_URL_PARTICIPANT = "ucastnik"
LEPRIKON_URL_PARTICIPANTS = "ucastnici"
LEPRIKON_URL_BILLING_INFO = "fakturacni-udaje"
LEPRIKON_URL_USER = "uzivatel"
LEPRIKON_URL_AGREEMENT = "souhlas"
LEPRIKON_URL_PASSWORD = "heslo"
LEPRIKON_URL_PASSWORD_RESET = "reset-hesla"
LEPRIKON_URL_LOGIN = "prihlasit"
LEPRIKON_URL_LOGOUT = "odhlasit"
LEPRIKON_URL_SCHOOL_YEAR = "skolni-rok"
LEPRIKON_URL_SUPPORT = "pomoc"
LEPRIKON_URL_EDIT = "upravit"
LEPRIKON_URL_JOURNAL = "denik"
LEPRIKON_URL_JOURNALS = "deniky"
LEPRIKON_URL_JOURNALENTRY = "zaznam-deniku"
LEPRIKON_URL_MINE = "moje"
LEPRIKON_URL_ALTERNATING = "zastup"
LEPRIKON_URL_REPORTS = "reporty"
LEPRIKON_URL_PAYMENT_REQUEST = "vyzva-k-platbe"
LEPRIKON_URL_PAYMENTS = "platby"
LEPRIKON_URL_RECEIVED_PAYMENTS = "prijate-platby"
LEPRIKON_URL_RETURNED_PAYMENTS = "vracene-platby"
LEPRIKON_URL_REFUND_REQUESTS = "vraceni-preplatku"
LEPRIKON_URL_PAYMENT_TRANSFER = "prevedeni-platby"
LEPRIKON_URL_DONATIONS = "dary"
LEPRIKON_URL_PAYMENTS_STATUS = "stav-plateb"
LEPRIKON_URL_DEBTORS = "dluznici"
LEPRIKON_URL_ADD = "pridat"
LEPRIKON_URL_DELETE = "smazat"
LEPRIKON_URL_CANCEL = "zrusit"
LEPRIKON_URL_REGISTRATION = "prihlaska"
LEPRIKON_URL_REGISTRATIONS = "prihlasky"
LEPRIKON_URL_REGISTRATION_LINK = "prihlasovaci-odkaz"
LEPRIKON_URL_TERMS_CONDITIONS = "obchodni-podminky"
LEPRIKON_URL_STATS = "statistiky"
LEPRIKON_URL_EMAIL = "email"

LEPRIKON_MENU_ADD_LOGOUT = True

LEPRIKON_SITE_CACHE_MAX_AGE = 5

# expression to create variable symbol (activity.code + last two digits of year + last four digits of id)
LEPRIKON_VARIABLE_SYMBOL_EXPRESSION = (
    "reg.activity.code * 1000000 + (reg.created.year % 100) * 10000 + (reg.id % 10000)"
)

SESSION_STAFF_COOKIE_AGE = 60 * 60 * 10
