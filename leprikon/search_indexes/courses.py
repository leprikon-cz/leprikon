from ..models.courses import Course
from .base import BaseIndex


class CourseIndex(BaseIndex):
    def get_model(self):
        return Course
