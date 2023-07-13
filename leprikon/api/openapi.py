from typing import List

from drf_spectacular.openapi import AutoSchema


class Schema(AutoSchema):
    def get_tags(self) -> List[str]:
        return ["leprikon"]
