import json

from models.course import Course


class Curriculum:

    def __init__(self, json_path):

        with open(
            json_path,
            "r",
            encoding="utf-8"
        ) as f:

            self.data = json.load(f)

        self.courses = {}

        self._load_courses()

    def _load_courses(self):

        for code, info in self.data["courses"].items():

            self.courses[code] = Course(
                code=code,
                name=info["course_name"],
                credits=info["credits"],
                category=info["category"],
                prerequisites=info["prerequisites"],
                is_elective=info["is_elective"],
                track=info["track"]
            )

    def get_course(self, code):

        return self.courses.get(code)

    def get_all_courses(self):

        return self.courses

    def get_prerequisites(self, code):

        course = self.get_course(code)

        if course:
            return course.prerequisites

        return []