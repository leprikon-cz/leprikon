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
        "accounted_date": "Datum splatnosti",
        "entry_date": "Datum odepsání z jiné banky",
        "remote_account_number": "Protiúčet a kód banky",
        "remote_account_name": "Název protiúčtu",
        "amount": "Částka",
        "variable_symbol": "VS",
        "constant_symbol": "KS",
        "specific_symbol": "SS",
        "transaction_id": "Identifikace transakce",
        "sender_description": "Popis příkazce",
        "recipient_description": "Popis pro příjemce",
    }
    date_format = "%d.%m.%Y"
    decimal_separator = ","


@register_reader
class CsCsvReader(CsvReader):
    label = "Česká spořitelna, CSV"
    encoding = "utf16"
    column_mapping = {
        "accounted_date": "Datum zaúčtování",
        "entry_date": "Datum zaúčtování",
        "remote_account_number": "Protiúčet",
        "remote_account_name": "Název protiúčtu",
        "amount": "Částka",
        "variable_symbol": "Variabilní symbol",
        # "constant_symbol": "",
        # "specific_symbol": "",
        "transaction_id": "ID transakce",
        "sender_description": "Zpráva pro mě",
        "recipient_description": "Zpráva pro příjemce",
    }
    date_format = "%d.%m.%Y"
    decimal_separator = ","


@register_reader
class UniCreditReader(MT940Reader):
    label = "UniCredit Bank, MT940 (.sta)"
