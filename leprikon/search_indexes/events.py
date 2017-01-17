from __future__ import unicode_literals

from ..models.events import Event
from .base import BaseIndex


class EventIndex(BaseIndex):

    def get_model(self):
        return Event
