import pandas as pd
import argparse
import json
import unicodedata
from pathlib import Path
from collections import defaultdict


# =========================================================
# CONFIG
# =========================================================

DEFAULT_COURSES_FILE = "courses_uet_robotics_ctdt_official.csv"
DEFAULT_STUDENTS_FILE = "student_profiles.csv"
DEFAULT_OUTPUT_JSON = "module1_output.json"


# =========================================================
# BASIC UTILS
# =========================================================

def read_csv_auto(file_path):
    encodings = ["utf-8-sig", "utf-8", "cp1258", "latin1"]

    for enc in encodings:
        try:
            return pd.read_csv(file_path, encoding=enc)
        except Exception:
            pass

    raise ValueError(f"Không thể đọc file CSV: {file_path}")


def normalize_text(text):
    if pd.isna(text):
        return ""

    text = str(text).lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text


def is_empty(value):
    if pd.isna(value):
        return True

    value = str(value).strip()

    return value == "" or value.lower() in [
        "nan", "none", "null", "-", "không", "khong"
    ]


def parse_course_list(value):
    if is_empty(value):
        return set()

    text = str(value)
    text = text.replace(",", ";").replace("|", ";")

    return set(
        item.strip()
        for item in text.split(";")
        if item.strip() and item.strip().lower() != "nan"
    )


def parse_prerequisites(value):
    if is_empty(value):
        return []

    text = str(value)
    text = text.replace(",", ";").replace("/", ";").replace("|", ";")

    return [
        item.strip()
        for item in text.split(";")
        if item.strip() and item.strip().lower() != "nan"
    ]


def parse_grade_map(value):
    grade_map = {}

    if is_empty(value):
        return grade_map

    parts = str(value).split(";")

    for part in parts:
        part = part.strip()

        if ":" not in part:
            continue

        course, grade = part.split(":", 1)

        course = course.strip()
        grade = grade.strip()

        if course and grade:
            grade_map[course] = grade

    return grade_map


def to_json_safe(value):
    """
    Chuyển dữ liệu pandas/numpy sang kiểu JSON chuẩn.
    """
    if pd.isna(value):
        return None

    if isinstance(value, (int, float, str, bool)):
        return value

    return str(value)


# =========================================================
# COURSE KNOWLEDGE BASE
# =========================================================

class CourseKnowledgeBase:
    def __init__(self, df_courses):
        self.df_courses = self.clean_courses(df_courses)
        self.course_info = {}
        self.prerequisites = {}
        self.graph = defaultdict(list)
        self.valid_codes = set()

        self.build()

    def clean_courses(self, df):
        required_cols = [
            "course_code",
            "course_name",
            "credits",
            "semester",
            "category",
            "prerequisite_code"
        ]

        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"courses.csv thiếu cột bắt buộc: {col}")

        df = df.copy()

        df["course_code"] = df["course_code"].astype(str).str.strip()

        df = df[
            (df["course_code"] != "") &
            (df["course_code"].str.lower() != "nan")
        ]

        df["course_name"] = df["course_name"].astype(str).str.strip()
        df["category"] = df["category"].astype(str).str.strip()
        df["credits"] = pd.to_numeric(
            df["credits"],
            errors="coerce"
        ).fillna(0).astype(int)

        return df

    def build(self):
        for _, row in self.df_courses.iterrows():
            course = str(row["course_code"]).strip()

            self.valid_codes.add(course)

            self.course_info[course] = {
                "course_code": course,
                "course_name": str(row["course_name"]),
                "credits": int(row["credits"]),
                "semester": to_json_safe(row["semester"]),
                "category": str(row["category"]),
            }

        for _, row in self.df_courses.iterrows():
            course = str(row["course_code"]).strip()

            prereq_list = parse_prerequisites(row["prerequisite_code"])

            prereq_list = [
                p for p in prereq_list
                if p in self.valid_codes and p != course
            ]

            self.prerequisites[course] = prereq_list

            for p in prereq_list:
                self.graph[p].append(course)

    def get_name(self, course_code):
        return self.course_info.get(course_code, {}).get("course_name", "")

    def get_credits(self, course_code):
        return self.course_info.get(course_code, {}).get("credits", 0)

    def get_category(self, course_code):
        return self.course_info.get(course_code, {}).get("category", "")

    def get_semester(self, course_code):
        return self.course_info.get(course_code, {}).get("semester", None)

    def missing_prerequisites(self, course_code, passed_courses):
        required = self.prerequisites.get(course_code, [])

        return [
            p for p in required
            if p not in passed_courses
        ]

    def calculate_credits(self, course_set):
        return sum(
            self.get_credits(c)
            for c in course_set
            if c in self.valid_codes
        )

    def course_type(self, course_code):
        name = normalize_text(self.get_name(course_code))
        category = normalize_text(self.get_category(course_code))

        if course_code == "RBE4004":
            return "internship"

        if course_code == "RBE4001":
            return "graduation_thesis"

        if course_code == "RBE4003":
            return "replacement_project"

        if course_code == "RBE3052":
            return "major_project"

        if "nhap mon" in name or "trai nghiem" in name or "kham pha" in name:
            return "intro"

        if "khoi kien thuc chung" in category:
            return "general"

        if "theo linh vuc" in category:
            return "field"

        if "theo khoi nganh" in category:
            return "block"

        if "theo nhom nganh" in category:
            return "group"

        if "nganh bat buoc" in category:
            return "mandatory_major"

        if "robot thong minh" in category:
            return "smart_robot_track"

        if "tu dong hoa" in category:
            return "automation_track"

        if "bo tro" in category:
            return "support"

        return "other"

    def get_course_json(self, course_code):
        return {
            "course_code": course_code,
            "course_name": self.get_name(course_code),
            "credits": self.get_credits(course_code),
            "semester": self.get_semester(course_code),
            "category": self.get_category(course_code),
            "course_type": self.course_type(course_code),
            "prerequisites": self.prerequisites.get(course_code, [])
        }


# =========================================================
# CAREER TRACK
# =========================================================

SMART_ROBOT_CAREERS = {
    "Computer Vision Engineer",
    "Navigation Algorithm Engineer",
    "AI Robotics Engineer",
    "Motion Planning Engineer",
    "Kinematics & Dynamics Specialist",
    "Autonomous Mobile Robot (AMR) Engineer",
    "Mobile Robotics Developer",
    "Cloud Robotics Developer",
    "Machine Learning Engineer (Robotics)",
    "Vision-based Robotics Engineer",
}

AUTOMATION_CAREERS = {
    "IoT Robotics Engineer",
    "Microcontroller Programmer",
    "Embedded Robotics Engineer",
    "Industrial Automation Engineer",
    "Smart Home Robotics Specialist",
    "Automation PLC Engineer",
    "SCADA Systems Engineer",
    "Embedded Systems Developer",
    "PLC Programmer",
    "Firmware Engineer",
}


def infer_career_track(career_goal, existing_track=None):
    if not is_empty(existing_track):
        return str(existing_track).strip()

    if career_goal in SMART_ROBOT_CAREERS:
        return "Robot thông minh"

    if career_goal in AUTOMATION_CAREERS:
        return "Tự động hóa công nghiệp"

    return "Robot thông minh"


# =========================================================
# GPA RULES
# =========================================================

def get_credit_limit(gpa):
    if gpa < 2.0:
        return 14

    if gpa < 2.5:
        return 16

    if gpa < 3.2:
        return 18

    return 22


def get_study_hours(gpa):
    if gpa < 2.0:
        return 12

    if gpa < 2.5:
        return 10

    if gpa < 3.2:
        return 8

    return 6


def get_risk_level(gpa, failed_count):
    if gpa < 2.0 or failed_count >= 2:
        return "HIGH"

    if gpa < 3.0 or failed_count == 1:
        return "MEDIUM"

    return "LOW"


# =========================================================
# MODULE 1 RULE ENGINE
# =========================================================

class Module1RuleEngine:
    def __init__(self, knowledge_base):
        self.kb = knowledge_base

    def extract_student_state(self, student_row):
        completed_courses = parse_course_list(student_row.get("completed_courses", ""))
        failed_courses = parse_course_list(student_row.get("failed_courses", ""))
        grade_map = parse_grade_map(student_row.get("course_grades", ""))

        for course, grade in grade_map.items():
            if grade == "F":
                failed_courses.add(course)

        passed_courses = set(completed_courses)

        for course in failed_courses:
            passed_courses.discard(course)

        for course, grade in grade_map.items():
            if grade != "F" and course in self.kb.valid_codes:
                passed_courses.add(course)

        for course in failed_courses:
            passed_courses.discard(course)

        year = int(student_row.get("year", 1))
        gpa = float(student_row.get("gpa", 0.0))

        career_goal = str(student_row.get("career_goal", "")).strip()

        career_track = infer_career_track(
            career_goal,
            student_row.get("career_track", None)
        )

        completed_credits = self.kb.calculate_credits(passed_courses)
        failed_count = len(failed_courses)

        return {
            "student_id": str(student_row.get("student_id", "")),
            "major": str(student_row.get("major", "")),
            "year": year,
            "current_semester": int(student_row.get("current_semester", year * 2 - 1)),
            "gpa": gpa,
            "career_goal": career_goal,
            "career_track": career_track,
            "completed_courses": sorted(completed_courses),
            "passed_courses": sorted(passed_courses),
            "failed_courses": sorted(failed_courses),
            "grade_map": grade_map,
            "completed_credits": completed_credits,
            "remaining_credits": max(0, 150 - completed_credits),
            "failed_count": failed_count,
            "credit_limit": get_credit_limit(gpa),
            "study_hours": get_study_hours(gpa),
            "risk_level": get_risk_level(gpa, failed_count),
        }

    def evaluate_course(self, course_code, state):
        passed = set(state["passed_courses"])
        failed = set(state["failed_courses"])

        year = state["year"]
        gpa = state["gpa"]
        credits = state["completed_credits"]
        career_track = state["career_track"]

        course_type = self.kb.course_type(course_code)

        blocked_reasons = []
        eligible_reasons = []
        priority = 0

        if course_code in passed:
            return {
                "eligible": False,
                "blocked_reason": "Môn đã hoàn thành",
                "priority": 0
            }

        # Rule 1: tiên quyết
        missing = self.kb.missing_prerequisites(course_code, passed)

        if missing and course_code not in failed:
            blocked_reasons.append(
                "Thiếu tiên quyết: " + ";".join(missing)
            )
        else:
            eligible_reasons.append("Đủ điều kiện tiên quyết")

        # Rule 2: định hướng nghề nghiệp
        if course_type == "smart_robot_track" and career_track != "Robot thông minh":
            blocked_reasons.append(
                "Không thuộc định hướng Tự động hóa công nghiệp"
            )

        if course_type == "automation_track" and career_track != "Tự động hóa công nghiệp":
            blocked_reasons.append(
                "Không thuộc định hướng Robot thông minh"
            )

        # Rule 3: theo năm học
        if year == 1:
            allowed_types = {
                "general",
                "field",
                "block",
                "intro",
                "support"
            }

            if course_type not in allowed_types:
                blocked_reasons.append(
                    "Năm 1 chỉ nên học đại cương, nền tảng, nhập môn hoặc bổ trợ"
                )

        elif year == 2:
            allowed_types = {
                "general",
                "field",
                "block",
                "group",
                "intro",
                "support",
                "mandatory_major"
            }

            if course_type not in allowed_types:
                blocked_reasons.append(
                    "Năm 2 chưa nên học định hướng, thực tập hoặc tốt nghiệp"
                )

            if course_type == "mandatory_major" and gpa < 3.2:
                blocked_reasons.append(
                    "Môn ngành bắt buộc chỉ nên học sớm ở năm 2 khi GPA >= 3.2"
                )

        elif year == 3:
            if course_type in {"graduation_thesis", "replacement_project"}:
                blocked_reasons.append(
                    "Năm 3 chưa nên học học phần tốt nghiệp hoặc thay thế tốt nghiệp"
                )

        # Rule 4: thực tập
        if course_type == "internship" and year < 3:
            blocked_reasons.append(
                "Thực tập ngành chỉ được học từ năm 3"
            )

        # Rule 5: đồ án ngành
        if course_type == "major_project" and credits < 120:
            blocked_reasons.append(
                "Đồ án ngành chỉ được học khi đạt tối thiểu 120 tín chỉ"
            )

        # Rule 6: đồ án tốt nghiệp
        if course_type == "graduation_thesis":
            if year < 4:
                if not (year == 3 and credits >= 140 and gpa >= 3.6):
                    blocked_reasons.append(
                        "Đồ án tốt nghiệp chỉ học năm 4 hoặc trường hợp tốt nghiệp sớm"
                    )

            if credits < 130:
                blocked_reasons.append(
                    "Chưa đủ tiến độ tín chỉ để học Đồ án tốt nghiệp"
                )

            if "RBE4003" in passed:
                blocked_reasons.append(
                    "Đã chọn Dự án ngành thay thế nên không học Đồ án tốt nghiệp"
                )

        # Rule 7: dự án ngành thay thế
        if course_type == "replacement_project":
            if year < 4:
                blocked_reasons.append(
                    "Dự án ngành thay thế chỉ áp dụng cho sinh viên năm 4"
                )

            if credits < 120:
                blocked_reasons.append(
                    "Dự án ngành thay thế yêu cầu tối thiểu 120 tín chỉ"
                )

            if "RBE4001" in passed:
                blocked_reasons.append(
                    "Đã học Đồ án tốt nghiệp nên không học Dự án ngành thay thế"
                )

        if blocked_reasons:
            return {
                "eligible": False,
                "blocked_reason": " | ".join(blocked_reasons),
                "priority": 0,
                "missing_prerequisites": missing
            }

        # Priority scoring
        if course_code in failed:
            priority += 100
            eligible_reasons.append("Môn đã trượt, ưu tiên học lại")

        if year == 1:
            if course_type in {"general", "field", "block"}:
                priority += 80
                eligible_reasons.append("Ưu tiên hoàn thành đại cương trong 2 năm đầu")

            if course_type == "intro":
                priority += 90
                eligible_reasons.append("Môn nhập môn/trải nghiệm nên học sớm")

        elif year == 2:
            if course_type in {"general", "field", "block"}:
                priority += 80
                eligible_reasons.append("Cần hoàn thành đại cương trước năm 3")

            if course_type == "group":
                priority += 70
                eligible_reasons.append("Khối nhóm ngành nên hoàn thành trước năm 4")

            if course_type == "mandatory_major":
                priority += 50
                eligible_reasons.append("GPA cao nên có thể học sớm môn ngành bắt buộc")

        elif year == 3:
            if course_type == "mandatory_major":
                priority += 90
                eligible_reasons.append("Môn ngành bắt buộc ưu tiên học trong năm 3")

            if course_type == "internship":
                priority += 95
                eligible_reasons.append("Thực tập ngành ưu tiên trong năm 3")

            if course_type in {"smart_robot_track", "automation_track"}:
                priority += 75
                eligible_reasons.append("Môn phù hợp định hướng nghề nghiệp")

            if course_type == "support":
                priority += 40
                eligible_reasons.append("Môn bổ trợ hoàn thiện chương trình")

        elif year >= 4:
            if course_type in {"graduation_thesis", "replacement_project"}:
                priority += 100
                eligible_reasons.append("Học phần tốt nghiệp/thay thế tốt nghiệp")

            if course_type == "major_project":
                priority += 90
                eligible_reasons.append("Đủ điều kiện học Đồ án ngành")

            if course_type in {"smart_robot_track", "automation_track"}:
                priority += 80
                eligible_reasons.append("Môn chuyên sâu đúng định hướng")

            if course_type == "mandatory_major":
                priority += 85
                eligible_reasons.append("Hoàn thiện khối ngành bắt buộc")

            if course_type == "support":
                priority += 60
                eligible_reasons.append("Hoàn thiện khối bổ trợ")

        if gpa < 2.0:
            if course_code in failed:
                priority += 30
            else:
                priority -= 10

        elif gpa >= 3.2:
            priority += 10

        return {
            "eligible": True,
            "blocked_reason": "",
            "priority": priority,
            "reason": " | ".join(eligible_reasons),
            "missing_prerequisites": []
        }

    def analyze_student(self, student_row):
        state = self.extract_student_state(student_row)

        eligible_courses = []
        blocked_courses = []

        for course_code in sorted(self.kb.valid_codes):
            result = self.evaluate_course(course_code, state)

            course_json = self.kb.get_course_json(course_code)

            if result["eligible"]:
                eligible_courses.append({
                    **course_json,
                    "priority": int(result["priority"]),
                    "reason": result["reason"],
                    "missing_prerequisites": []
                })

            else:
                reason = result.get("blocked_reason", "")

                if reason != "Môn đã hoàn thành":
                    blocked_courses.append({
                        **course_json,
                        "blocked_reason": reason,
                        "missing_prerequisites": result.get(
                            "missing_prerequisites",
                            []
                        )
                    })

        eligible_courses = sorted(
            eligible_courses,
            key=lambda x: (
                x["priority"],
                x["credits"],
                x["course_code"]
            ),
            reverse=True
        )

        module2_candidates = [
            course for course in eligible_courses
            if course["priority"] > 0
        ]

        output = {
            "module": "Module 1 - Rule-based Knowledge Engine",
            "output_for": "Module 2 - Search and Planning Engine",

            "student_state": {
                "student_id": state["student_id"],
                "major": state["major"],
                "year": state["year"],
                "current_semester": state["current_semester"],
                "gpa": state["gpa"],
                "career_goal": state["career_goal"],
                "career_track": state["career_track"],
                "completed_credits": state["completed_credits"],
                "remaining_credits": state["remaining_credits"],
                "completed_courses": state["completed_courses"],
                "passed_courses": state["passed_courses"],
                "failed_courses": state["failed_courses"],
                "failed_count": state["failed_count"],
                "course_grades": state["grade_map"],
            },

            "constraints": {
                "credit_limit_per_semester": state["credit_limit"],
                "study_hours_per_week": state["study_hours"],
                "risk_level": state["risk_level"],
                "planning_horizon_semesters": 2,
                "must_respect_prerequisites": True,
                "must_follow_career_track": True,
                "total_program_credits": 150,
            },

            "search_space": {
                "eligible_course_count": len(eligible_courses),
                "candidate_course_count": len(module2_candidates),
                "blocked_course_count": len(blocked_courses),
                "eligible_courses": eligible_courses,
                "candidate_courses_for_module2": module2_candidates,
                "blocked_courses": blocked_courses,
            },

            "course_catalog_reference": {
                "total_courses": len(self.kb.valid_codes),
                "course_codes": sorted(list(self.kb.valid_codes)),
            }
        }

        return output


# =========================================================
# LOAD STUDENT
# =========================================================

def load_student(df_students, student_id=None):
    if student_id is None:
        return df_students.iloc[0]

    matched = df_students[
        df_students["student_id"].astype(str) == str(student_id)
    ]

    if matched.empty:
        raise ValueError(f"Không tìm thấy student_id: {student_id}")

    return matched.iloc[0]


# =========================================================
# PRINT RESULT
# =========================================================

def print_json_summary(output, top_n=15):
    state = output["student_state"]
    constraints = output["constraints"]
    search_space = output["search_space"]

    print("=" * 70)
    print("MODULE 1 OUTPUT JSON CREATED")
    print("=" * 70)

    print("Student ID       :", state["student_id"])
    print("Year             :", state["year"])
    print("Semester         :", state["current_semester"])
    print("GPA              :", state["gpa"])
    print("Career goal      :", state["career_goal"])
    print("Career track     :", state["career_track"])
    print("Completed credits:", state["completed_credits"])
    print("Credit limit     :", constraints["credit_limit_per_semester"])
    print("Study hours/week :", constraints["study_hours_per_week"])
    print("Risk level       :", constraints["risk_level"])

    print("\nEligible courses :", search_space["eligible_course_count"])
    print("Candidate courses:", search_space["candidate_course_count"])
    print("Blocked courses  :", search_space["blocked_course_count"])

    print("\nTOP CANDIDATE COURSES FOR MODULE 2")
    print("-" * 70)

    for course in search_space["candidate_courses_for_module2"][:top_n]:
        print(
            f"+ {course['course_code']} - {course['course_name']} "
            f"({course['credits']} TC) | Priority={course['priority']}"
        )
        print(f"  Reason: {course['reason']}")

    print("=" * 70)


# =========================================================
# MAIN
# =========================================================

def main():
    parser = argparse.ArgumentParser(
        description="Module 1 - Rule Engine xuất JSON cho Module 2"
    )

    parser.add_argument(
        "--courses",
        default=DEFAULT_COURSES_FILE,
        help="File courses_uet_robotics_ctdt_official.csv"
    )

    parser.add_argument(
        "--students",
        default=DEFAULT_STUDENTS_FILE,
        help="File student_profiles.csv"
    )

    parser.add_argument(
        "--student",
        default=None,
        help="student_id cần phân tích. Nếu bỏ trống sẽ lấy sinh viên đầu tiên."
    )

    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_JSON,
        help="Tên file JSON đầu ra cho Module 2"
    )

    parser.add_argument(
        "--top",
        type=int,
        default=15,
        help="Số môn candidate hiển thị trên terminal"
    )

    args = parser.parse_args()

    courses_path = Path(args.courses)
    students_path = Path(args.students)

    if not courses_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {courses_path}")

    if not students_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {students_path}")

    df_courses = read_csv_auto(courses_path)
    df_students = read_csv_auto(students_path)

    kb = CourseKnowledgeBase(df_courses)
    engine = Module1RuleEngine(kb)

    student_row = load_student(df_students, args.student)

    output = engine.analyze_student(student_row)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(
            output,
            f,
            ensure_ascii=False,
            indent=4
        )

    print_json_summary(output, top_n=args.top)



if __name__ == "__main__":
    main()