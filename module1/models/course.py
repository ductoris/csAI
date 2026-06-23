class Course:

    def __init__(
        self,
        code,
        name,
        credits,
        category,
        prerequisites,
        is_elective,
        track
    ):
        self.code = code
        self.name = name
        self.credits = credits
        self.category = category
        self.prerequisites = prerequisites
        self.is_elective = is_elective
        self.track = track

    def __repr__(self):
        return f"{self.code} - {self.name}"