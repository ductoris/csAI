import pandas as pd
import random
import re
from pathlib import Path

# =========================================================
# CONFIG
# =========================================================

RANDOM_SEED = 2026
NUM_STUDENTS = 150

COURSES_FILE = "courses_uet_robotics_ctdt_official.csv"
OUTPUT_FILE = "student_profiles.csv"

MAJOR_NAME = "Kỹ thuật Robot"

GRADE_TO_GPA = {
    "A+": 4.0,
    "A": 3.7,
    "B+": 3.5,
    "B": 3.0,
    "C+": 2.5,
    "C": 2.0,
    "D+": 1.5,
    "D": 1.0,
    "F": 0.0,
}

CAREER_PATHS = [
    ("Computer Vision Engineer", "Robot thông minh"),
    ("Navigation Algorithm Engineer", "Robot thông minh"),
    ("IoT Robotics Engineer", "Tự động hóa công nghiệp"),
    ("Microcontroller Programmer", "Tự động hóa công nghiệp"),
    ("Embedded Robotics Engineer", "Tự động hóa công nghiệp"),
    ("Industrial Automation Engineer", "Tự động hóa công nghiệp"),
    ("AI Robotics Engineer", "Robot thông minh"),
    ("Motion Planning Engineer", "Robot thông minh"),
    ("Kinematics & Dynamics Specialist", "Robot thông minh"),
    ("Smart Home Robotics Specialist", "Tự động hóa công nghiệp"),
    ("Autonomous Mobile Robot (AMR) Engineer", "Robot thông minh"),
    ("Automation PLC Engineer", "Tự động hóa công nghiệp"),
    ("Mobile Robotics Developer", "Robot thông minh"),
    ("SCADA Systems Engineer", "Tự động hóa công nghiệp"),
    ("Cloud Robotics Developer", "Robot thông minh"),
    ("Embedded Systems Developer", "Tự động hóa công nghiệp"),
    ("Machine Learning Engineer (Robotics)", "Robot thông minh"),
    ("PLC Programmer", "Tự động hóa công nghiệp"),
    ("Firmware Engineer", "Tự động hóa công nghiệp"),
    ("Vision-based Robotics Engineer", "Robot thông minh"),
]

SMART_KEYWORDS = [
    "AI", "Machine Learning", "Vision", "Navigation",
    "Mobile", "AMR", "Cloud", "Motion", "Kinematics"
]

AUTOMATION_KEYWORDS = [
    "PLC", "SCADA", "Automation", "Industrial",
    "Embedded", "Firmware", "IoT", "Microcontroller", "Smart Home"
]


# =========================================================
# LOAD DATA
# =========================================================

def read_csv_auto(path):
    for enc in ["utf-8-sig", "utf-8", "cp1258", "latin1"]:
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            pass
    raise ValueError(f"Không đọc được file: {path}")


def clean_courses(df):
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
            raise ValueError(f"Thiếu cột bắt buộc trong courses.csv: {col}")

    df = df.copy()

    df["course_code"] = df["course_code"].astype(str).str.strip()
    df = df[
        (df["course_code"] != "") &
        (df["course_code"].str.lower() != "nan")
    ]

    df["course_name"] = df["course_name"].astype(str).str.strip()
    df["category"] = df["category"].astype(str).str.strip()
    df["credits"] = pd.to_numeric(df["credits"], errors="coerce").fillna(0).astype(int)

    return df


# =========================================================
# COURSE HELPERS
# =========================================================

def parse_prerequisites(value):
    if pd.isna(value):
        return []

    text = str(value).strip()

    if text == "" or text.lower() in ["nan", "none", "không", "khong", "-"]:
        return []

    text = text.replace(",", ";").replace("/", ";")
    parts = [x.strip() for x in text.split(";") if x.strip()]

    return parts


def build_course_maps(df_courses):
    course_info = {}
    prerequisites = {}

    for _, row in df_courses.iterrows():
        code = row["course_code"]

        course_info[code] = {
            "name": row["course_name"],
            "credits": int(row["credits"]),
            "semester": row["semester"],
            "category": row["category"],
        }

        prerequisites[code] = parse_prerequisites(row["prerequisite_code"])

    return course_info, prerequisites


def get_ancestors(course_code, prerequisites, valid_codes, visited=None):
    if visited is None:
        visited = set()

    if course_code in visited:
        return set()

    visited.add(course_code)

    result = set()

    for p in prerequisites.get(course_code, []):
        if p in valid_codes:
            result.add(p)
            result |= get_ancestors(p, prerequisites, valid_codes, visited)

    return result


def add_course_with_prereqs(course_set, course_code, prerequisites, valid_codes):
    if course_code not in valid_codes:
        return

    ancestors = get_ancestors(course_code, prerequisites, valid_codes)

    for p in ancestors:
        course_set.add(p)

    course_set.add(course_code)


def total_credits(course_set, course_info):
    return sum(course_info[c]["credits"] for c in course_set if c in course_info)


def filter_by_category(df_courses, patterns):
    pattern = "|".join(patterns)
    return df_courses[
        df_courses["category"].str.contains(pattern, case=False, na=False)
    ]["course_code"].tolist()


def filter_by_name(df_courses, patterns):
    pattern = "|".join(patterns)
    return df_courses[
        df_courses["course_name"].str.contains(pattern, case=False, na=False)
    ]["course_code"].tolist()


# =========================================================
# GPA AND GRADES
# =========================================================

def choose_performance_level(year):
    r = random.random()

    if r < 0.10:
        return "weak"
    elif r < 0.45:
        return "average"
    elif r < 0.85:
        return "good"
    else:
        return "excellent"


def random_grade(level):
    if level == "excellent":
        return random.choices(
            ["A+", "A", "B+", "B"],
            weights=[0.25, 0.35, 0.30, 0.10]
        )[0]

    if level == "good":
        return random.choices(
            ["A", "B+", "B", "C+"],
            weights=[0.15, 0.35, 0.35, 0.15]
        )[0]

    if level == "average":
        return random.choices(
            ["B", "C+", "C", "D+"],
            weights=[0.25, 0.35, 0.30, 0.10]
        )[0]

    return random.choices(
        ["C", "D+", "D", "F"],
        weights=[0.35, 0.25, 0.25, 0.15]
    )[0]


def calculate_gpa(course_grades, course_info):
    total_points = 0
    total_credits = 0

    for code, grade in course_grades.items():
        if code not in course_info:
            continue

        credits = course_info[code]["credits"]
        total_points += GRADE_TO_GPA[grade] * credits
        total_credits += credits

    if total_credits == 0:
        return 0.0

    return round(total_points / total_credits, 2)


def generate_failed_courses(eligible_pool, completed_set, level, year):
    failed = []

    if level == "weak":
        k = random.choice([1, 2, 2, 3])
    elif level == "average" and random.random() < 0.25:
        k = 1
    else:
        k = 0

    candidates = [c for c in eligible_pool if c not in completed_set]

    if not candidates:
        return []

    failed = random.sample(candidates, min(k, len(candidates)))

    return failed


# =========================================================
# ADVISOR OUTPUT FIELDS
# =========================================================

def recommend_credits(gpa, failed_count, year):
    if gpa < 2.0:
        return 14

    if gpa < 2.5:
        return 16

    if gpa < 3.2:
        return 18

    if year <= 2:
        return 20

    return random.choice([20, 22])


def study_hours(gpa, failed_count):
    if gpa < 2.0:
        return random.choice([12, 13, 14, 15])

    if gpa < 2.5:
        return random.choice([10, 11, 12])

    if gpa < 3.2:
        return random.choice([8, 9, 10])

    return random.choice([6, 7, 8])


def risk_level(gpa, failed_count):
    if gpa < 2.0 or failed_count >= 2:
        return "HIGH"

    if gpa < 3.0 or failed_count == 1:
        return "MEDIUM"

    return "LOW"


def infer_weak_skills(career_goal, course_grades):
    weak = []

    low_grades = {"C", "D+", "D", "F"}

    math_codes = ["MAT1041", "MAT1042", "MAT1093"]
    programming_codes = ["INT1008", "ELT3240"]
    electronics_codes = ["ELT2201", "ELT3290", "ELT3292"]
    control_codes = ["RBE3012", "RBE3042"]
    ai_codes = ["AIT2004", "RBE3047", "RBE3043", "RBE3046"]
    vision_codes = ["RBE3015"]

    def has_low(codes):
        return any(course_grades.get(c) in low_grades for c in codes)

    if has_low(math_codes):
        weak.append("Toán nền tảng")

    if has_low(programming_codes):
        weak.append("Lập trình")

    if has_low(electronics_codes):
        weak.append("Điện tử - vi điều khiển")

    if has_low(control_codes):
        weak.append("Điều khiển")

    if has_low(ai_codes):
        weak.append("AI - Machine Learning")

    if has_low(vision_codes):
        weak.append("Xử lý ảnh - thị giác máy tính")

    if "Vision" in career_goal or "Computer Vision" in career_goal:
        weak.append("OpenCV")

    if "AI" in career_goal or "Machine Learning" in career_goal:
        weak.append("Python")

    if "PLC" in career_goal or "SCADA" in career_goal:
        weak.append("PLC/SCADA")

    if "Embedded" in career_goal or "Firmware" in career_goal or "Microcontroller" in career_goal:
        weak.append("Embedded C/C++")

    return ";".join(sorted(set(weak)))


# =========================================================
# STUDENT GENERATION
# =========================================================

def build_student_courses(
    year,
    career_track,
    level,
    df_courses,
    course_info,
    prerequisites,
    special_project=False
):
    valid_codes = set(course_info.keys())
    completed = set()

    common = filter_by_category(df_courses, ["Khối kiến thức chung"])
    field = filter_by_category(df_courses, ["Khối kiến thức theo lĩnh vực"])
    block = filter_by_category(df_courses, ["Khối kiến thức theo khối ngành"])
    group = filter_by_category(df_courses, ["Khối kiến thức theo nhóm ngành"])
    mandatory = filter_by_category(df_courses, ["Khối kiến thức ngành bắt buộc"])
    support = filter_by_category(df_courses, ["Khối kiến thức bổ trợ"])
    smart = filter_by_category(df_courses, ["Robot thông minh"])
    automation = filter_by_category(df_courses, ["Tự động hóa"])

    intro_courses = filter_by_name(df_courses, ["Nhập môn", "Trải nghiệm", "khám phá"])

    graduation_courses = filter_by_category(df_courses, ["Thực tập và tốt nghiệp"])
    replacement_courses = filter_by_category(df_courses, ["Thay thế Đồ án tốt nghiệp"])

    target_credit_ranges = {
        1: (18, 42),
        2: (45, 82),
        3: (85, 122),
        4: (120, 150),
    }

    target_min, target_max = target_credit_ranges[year]
    target_credits = random.randint(target_min, target_max)

    def add_from_pool(pool, max_courses=None):
        pool = [c for c in pool if c in valid_codes]
        random.shuffle(pool)

        count = 0

        for c in pool:
            if total_credits(completed, course_info) >= target_credits:
                break

            add_course_with_prereqs(completed, c, prerequisites, valid_codes)
            count += 1

            if max_courses is not None and count >= max_courses:
                break

    # -------------------------------
    # YEAR 1
    # -------------------------------
    if year == 1:
        add_from_pool(intro_courses, max_courses=3)
        add_from_pool(common + field + block)

        if level in ["good", "excellent"]:
            add_from_pool(group, max_courses=2)

    # -------------------------------
    # YEAR 2
    # -------------------------------
    elif year == 2:
        for c in common + field + block:
            add_course_with_prereqs(completed, c, prerequisites, valid_codes)

        add_from_pool(group)

        if level in ["good", "excellent"]:
            add_from_pool(mandatory, max_courses=random.choice([2, 3]))

    # -------------------------------
    # YEAR 3
    # -------------------------------
    elif year == 3:
        for c in common + field + block + group:
            add_course_with_prereqs(completed, c, prerequisites, valid_codes)

        major_count = random.randint(
            max(6, len(mandatory) // 2),
            min(len(mandatory), max(8, len(mandatory)))
        )

        add_from_pool(mandatory, max_courses=major_count)

        # Thực tập ngành ưu tiên năm 3
        if "RBE4004" in valid_codes:
            add_course_with_prereqs(completed, "RBE4004", prerequisites, valid_codes)

        track_pool = smart if career_track == "Robot thông minh" else automation
        add_from_pool(track_pool, max_courses=random.choice([2, 3, 4]))

        add_from_pool(support, max_courses=random.choice([1, 2]))

    # -------------------------------
    # YEAR 4
    # -------------------------------
    else:
        for c in common + field + block + group + mandatory:
            add_course_with_prereqs(completed, c, prerequisites, valid_codes)

        if "RBE4004" in valid_codes:
            add_course_with_prereqs(completed, "RBE4004", prerequisites, valid_codes)

        track_pool = smart if career_track == "Robot thông minh" else automation

        # Chuyên sâu: 12-15 tín chỉ
        selected_track = []
        track_credits = 0
        shuffled_track = [c for c in track_pool if c in valid_codes]
        random.shuffle(shuffled_track)

        for c in shuffled_track:
            if track_credits >= random.choice([12, 13, 14, 15]):
                break

            selected_track.append(c)
            track_credits += course_info[c]["credits"]

        for c in selected_track:
            add_course_with_prereqs(completed, c, prerequisites, valid_codes)

        # Bổ trợ: 6-9 tín chỉ
        selected_support = []
        support_credits = 0
        shuffled_support = [c for c in support if c in valid_codes]
        random.shuffle(shuffled_support)

        for c in shuffled_support:
            if support_credits >= random.choice([6, 7, 8, 9]):
                break

            selected_support.append(c)
            support_credits += course_info[c]["credits"]

        for c in selected_support:
            add_course_with_prereqs(completed, c, prerequisites, valid_codes)

        # Đồ án ngành nếu đã đạt khoảng 120 tín
        if "RBE3052" in valid_codes and total_credits(completed, course_info) >= 115:
            add_course_with_prereqs(completed, "RBE3052", prerequisites, valid_codes)

        # Dự án ngành thay ĐATN cho một nhóm nhỏ
        if special_project:
            if "RBE4003" in valid_codes:
                add_course_with_prereqs(completed, "RBE4003", prerequisites, valid_codes)

            if "RBE4001" in completed:
                completed.remove("RBE4001")

            # Học thêm 6 tín tự chọn định hướng
            add_from_pool(track_pool, max_courses=2)

        else:
            if "RBE4001" in valid_codes and total_credits(completed, course_info) >= 130:
                add_course_with_prereqs(completed, "RBE4001", prerequisites, valid_codes)

    return completed


def generate_students(df_courses):
    random.seed(RANDOM_SEED)

    course_info, prerequisites = build_course_maps(df_courses)

    year_distribution = {
        1: 38,
        2: 37,
        3: 37,
        4: 38,
    }

    rows = []
    student_counter = 1

    # 3 sinh viên năm 4 học Dự án ngành thay ĐATN
    year4_project_indices = set(random.sample(range(38), 3))

    for year, count in year_distribution.items():
        for i in range(count):
            student_id = f"UET{230000 + student_counter:06d}"
            current_semester = random.choice([year * 2 - 1, year * 2])

            career_goal, career_track = random.choice(CAREER_PATHS)
            level = choose_performance_level(year)

            special_project = year == 4 and i in year4_project_indices

            completed_set = build_student_courses(
                year=year,
                career_track=career_track,
                level=level,
                df_courses=df_courses,
                course_info=course_info,
                prerequisites=prerequisites,
                special_project=special_project
            )

            # Các môn có thể trượt: chọn từ các môn chưa hoàn thành nhưng cùng vùng năm học
            eligible_failed_pool = list(course_info.keys())
            failed_courses = generate_failed_courses(
                eligible_failed_pool,
                completed_set,
                level,
                year
            )

            course_grades = {}

            for c in sorted(completed_set):
                grade = random_grade(level)

                # Completed courses không được F
                if grade == "F":
                    grade = "D"

                course_grades[c] = grade

            for c in failed_courses:
                course_grades[c] = "F"

            gpa = calculate_gpa(course_grades, course_info)

            completed_credits = total_credits(completed_set, course_info)
            failed_count = len(failed_courses)

            rec_credits = recommend_credits(gpa, failed_count, year)
            max_credits = min(22, rec_credits + 2)
            hours = study_hours(gpa, failed_count)
            risk = risk_level(gpa, failed_count)
            weak_skills = infer_weak_skills(career_goal, course_grades)

            completed_courses_str = ";".join(sorted(completed_set))
            failed_courses_str = ";".join(sorted(failed_courses))

            course_grades_str = ";".join(
                [f"{code}:{grade}" for code, grade in sorted(course_grades.items())]
            )

            rows.append({
                "student_id": student_id,
                "major": MAJOR_NAME,
                "year": year,
                "current_semester": current_semester,
                "gpa": gpa,
                "completed_credits": completed_credits,
                "completed_courses": completed_courses_str,
                "course_grades": course_grades_str,
                "failed_courses": failed_courses_str,
                "career_goal": career_goal,
                "career_track": career_track,
                "max_credits_per_semester": max_credits,
                "study_hours_per_week": hours,
                "risk_level": risk,
                "recommended_credits": rec_credits,
                "weak_skills": weak_skills,
            })

            student_counter += 1

    return pd.DataFrame(rows)


# =========================================================
# VALIDATION
# =========================================================

def validate_students(df_students):
    assert len(df_students) == NUM_STUDENTS, "Sai số lượng sinh viên"

    assert df_students["student_id"].is_unique, "student_id bị trùng"

    assert df_students["completed_courses"].notna().all(), "Có completed_courses bị rỗng"

    assert df_students["gpa"].between(0, 4).all(), "GPA nằm ngoài hệ 4"

    assert df_students["recommended_credits"].between(10, 24).all(), "recommended_credits bất thường"

    assert df_students["study_hours_per_week"].between(4, 20).all(), "study_hours_per_week bất thường"


# =========================================================
# MAIN
# =========================================================

def main():
    courses_path = Path(COURSES_FILE)

    if not courses_path.exists():
        raise FileNotFoundError(
            f"Không tìm thấy {COURSES_FILE}. "
            f"Hãy đặt file này cùng thư mục với script."
        )

    df_courses_raw = read_csv_auto(courses_path)
    df_courses = clean_courses(df_courses_raw)

    df_students = generate_students(df_courses)

    validate_students(df_students)

    df_students.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    print("Đã tạo xong file:", OUTPUT_FILE)
    print("Số sinh viên:", len(df_students))
    print()
    print("Phân bố năm học:")
    print(df_students["year"].value_counts().sort_index())
    print()
    print("Phân bố risk_level:")
    print(df_students["risk_level"].value_counts())
    print()
    print("GPA trung bình:", round(df_students["gpa"].mean(), 2))


if __name__ == "__main__":
    main()