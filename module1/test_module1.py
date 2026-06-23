from curriculum import Curriculum

from graph_builder import CurriculumGraph

from eligibility import (
    get_eligible_courses,
    get_blocked_courses
)

curriculum = Curriculum(
    "data/ctdt_ky_thuat_robot.json"
)

graph = CurriculumGraph(
    curriculum
)

passed_courses = [
    "MAT1041",
    "INT1008",
    "EPN1095"
]

eligible = get_eligible_courses(
    passed_courses,
    curriculum
)

blocked = get_blocked_courses(
    passed_courses,
    curriculum
)

print("\n=== ELIGIBLE ===")

for c in eligible:
    print(c)

print("\n=== BLOCKED ===")

for c, missing in blocked.items():
    print(c, "->", missing)