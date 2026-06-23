import pandas as pd
import json

df = pd.read_csv("courses_uet_robotics_ctdt_official.csv")

courses = {}

for _, row in df.iterrows():

    course_code = str(row["course_code"]).strip()

    if course_code == "" or course_code == "nan":
        continue

    category = str(row["category"]).strip()

    prereqs = []

    if pd.notna(row["prerequisite_code"]):
        prereqs = [
            p.strip()
            for p in str(row["prerequisite_code"]).split(";")
            if p.strip()
        ]

    # ==========================
    # elective + track
    # ==========================

    is_elective = False
    track = None

    if "Định hướng tự động hóa trong công nghiệp" in category:
        is_elective = True
        track = ["automation"]

    elif "Định hướng các hệ thống Robot thông minh" in category:
        is_elective = True
        track = ["intelligent_robot"]

    elif course_code in ["REB3053", "RBE3056", "RBE3057"]:
        is_elective = True
        track = [
            "automation",
            "intelligent_robot"
        ]

    courses[course_code] = {
        "course_name": row["course_name"],
        "credits": int(row["credits"]),
        "semester": None,
        "category": category,
        "prerequisites": prereqs,
        "is_elective": is_elective,
        "track": track
    }

output = {
    "program_name": "Kỹ thuật Robot",
    "program_code": "7520217",
    "total_credits": 150,
    "tracks": {
        "automation": {
            "name": "Tự động hóa trong công nghiệp",
            "required_elective_credits": 12
        },
        "intelligent_robot": {
            "name": "Các hệ thống Robot thông minh",
            "required_elective_credits": 12
        }
    },
    "courses": courses
}

with open(
    "robot_curriculum.json",
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        output,
        f,
        ensure_ascii=False,
        indent=4
    )

print("Export completed!")