from bankreader.readers import register_reader
from bankreader.readers.best import BestReader
from bankreader.readers.csv import CsvReader


@register_reader
class KbBestReader(BestReader):
    label = 'Komerční banka Best'


@register_reader
class KbCsvReader(CsvReader):
    label = 'Komerční banka CSV'
    encoding = 'cp1250'
    delimiter = ';'
    column_mapping = {
        'Datum splatnosti': 'accounted_date',
        'Datum odepsání z jiné banky': 'entry_date',
        'Protiúčet a kód banky': 'remote_account_number',
        'Název protiúčtu': 'remote_account_name',
        'Částka': 'amount',
        'VS': 'variable_symbol',
        'KS': 'constant_symbol',
        'SS': 'specific_symbol',
        'Identifikace transakce': 'transaction_id',
        'Popis příkazce': 'sender_description',
        'Popis pro příjemce': 'recipient_description',
    }
    date_format = '%d.%m.%Y'
    decimal_separator = ','
