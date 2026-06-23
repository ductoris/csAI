def can_take(
    course_code,
    passed_courses,
    curriculum
):

    prereqs = curriculum.get_prerequisites(
        course_code
    )

    return all(
        p in passed_courses
        for p in prereqs
    )


def get_eligible_courses(
    passed_courses,
    curriculum
):

    eligible = []

    for code in curriculum.courses:

        if code in passed_courses:
            continue

        if can_take(
            code,
            passed_courses,
            curriculum
        ):
            eligible.append(code)

    return eligible


def get_blocked_courses(
    passed_courses,
    curriculum
):

    blocked = {}

    for code, course in curriculum.courses.items():

        if code in passed_courses:
            continue

        missing = []

        for prereq in course.prerequisites:

            if prereq not in passed_courses:

                missing.append(prereq)

        if missing:

            blocked[code] = missing

    return blocked