from bankreader.readers import register_reader
from bankreader.readers.best import BestReader
from bankreader.readers.csv import CsvReader
from bankreader.readers.gpc import GpcReader
from bankreader.readers.mt940 import MT940Reader


@register_reader
class CsobGpcReader(GpcReader):
    label = "ČSOB, GPC"
    encoding = "cp1250"


@register_reader
class KbBestReader(BestReader):
    label = "Komerční banka, Best"


@register_reader
class KbCsvReader(CsvReader):
    label = "Komerční banka, CSV"
    encoding = "cp1250"
    delimiter = ";"
    column_mapping = {
        "Datum splatnosti": "accounted_date",
        "Datum odepsání z jiné banky": "entry_date",
        "Protiúčet a kód banky": "remote_account_number",
        "Název protiúčtu": "remote_account_name",
        "Částka": "amount",
        "VS": "variable_symbol",
        "KS": "constant_symbol",
        "SS": "specific_symbol",
        "Identifikace transakce": "transaction_id",
        "Popis příkazce": "sender_description",
        "Popis pro příjemce": "recipient_description",
    }
    date_format = "%d.%m.%Y"
    decimal_separator = ","


@register_reader
class CsCsvReader(CsvReader):
    label = "Česká spořitelna, CSV"
    encoding = "utf16"
    column_mapping = {
        "Datum zaúčtování": "accounted_date",
        # "": "entry_date",
        "Protiúčet": "remote_account_number",
        "Název protiúčtu": "remote_account_name",
        "Částka": "amount",
        "Variabilní symbol": "variable_symbol",
        # "": "constant_symbol",
        # "": "specific_symbol",
        "ID transakce": "transaction_id",
        "Zpráva pro mě": "sender_description",
        "Zpráva pro příjemce": "recipient_description",
    }
    date_format = "%d.%m.%Y"
    decimal_separator = ","


@register_reader
class UniCreditReader(MT940Reader):
    label = "UniCredit Bank, MT940 (.sta)"
