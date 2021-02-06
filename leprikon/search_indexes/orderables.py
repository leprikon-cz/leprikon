from ..models.orderables import Orderable
from .base import BaseIndex


class OrderableIndex(BaseIndex):
    def get_model(self):
        return Orderable
