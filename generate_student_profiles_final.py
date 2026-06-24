import pandas as pd
import random
import unicodedata
from pathlib import Path


# =========================================================
# CONFIG
# =========================================================

RANDOM_SEED = 2026

COURSES_FILE = "courses_uet_robotics_ctdt_official.csv"
OUTPUT_FILE = "student_profiles.csv"

MAJOR_NAME = "Kỹ thuật Robot"
TOTAL_PROGRAM_CREDITS = 150

# Với dữ liệu train ML, nên để False.
# Vì sinh viên kỳ 1 chưa có GPA thật.
INCLUDE_SEMESTER_1_NEW_STUDENTS = False

NUM_STUDENTS = 150

YEAR_DISTRIBUTION = {
    1: 38,
    2: 37,
    3: 37,
    4: 38,
}

# current_semester = học kỳ sắp bắt đầu
# completed_credits = tín chỉ đã tích lũy trước học kỳ đó
SEMESTER_CREDIT_RANGES = {
    1: (0, 0),
    2: (12, 22),
    3: (28, 45),
    4: (45, 65),
    5: (65, 85),
    6: (85, 105),
    7: (105, 125),
    8: (120, 145),
}

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

    raise ValueError(f"Không đọc được file CSV: {file_path}")


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


# =========================================================
# LOAD COURSE DATA
# =========================================================

def clean_courses(df):
    required_cols = [
        "course_code",
        "course_name",
        "credits",
        "semester",
        "category",
        "prerequisite_code",
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


def build_course_maps(df_courses):
    course_info = {}
    prerequisites = {}

    for _, row in df_courses.iterrows():
        code = str(row["course_code"]).strip()

        course_info[code] = {
            "course_code": code,
            "course_name": row["course_name"],
            "credits": int(row["credits"]),
            "semester": row["semester"],
            "category": row["category"],
        }

        prerequisites[code] = parse_prerequisites(row["prerequisite_code"])

    valid_codes = set(course_info.keys())

    # Loại prerequisite không tồn tại trong CTĐT
    for course in list(prerequisites.keys()):
        prerequisites[course] = [
            p for p in prerequisites[course]
            if p in valid_codes and p != course
        ]

    return course_info, prerequisites


def filter_by_category(df_courses, keywords):
    keywords_norm = [normalize_text(k) for k in keywords]

    result = []

    for _, row in df_courses.iterrows():
        category = normalize_text(row["category"])

        if any(k in category for k in keywords_norm):
            result.append(row["course_code"])

    return result


def filter_by_name(df_courses, keywords):
    keywords_norm = [normalize_text(k) for k in keywords]

    result = []

    for _, row in df_courses.iterrows():
        name = normalize_text(row["course_name"])

        if any(k in name for k in keywords_norm):
            result.append(row["course_code"])

    return result


# =========================================================
# PREREQUISITE HELPERS
# =========================================================

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


def total_credits(course_set, course_info):
    return sum(
        course_info[c]["credits"]
        for c in course_set
        if c in course_info
    )


def add_course_with_prereqs(
    completed,
    course_code,
    course_info,
    prerequisites,
    valid_codes,
    target_max
):
    """
    Thêm môn và toàn bộ tiên quyết của nó.
    Chỉ thêm nếu không làm vượt quá target_max quá nhiều.
    """

    if course_code not in valid_codes:
        return False

    to_add = set()
    to_add.add(course_code)
    to_add |= get_ancestors(course_code, prerequisites, valid_codes)

    new_courses = [c for c in to_add if c not in completed]
    added_credits = sum(course_info[c]["credits"] for c in new_courses)

    current_credits = total_credits(completed, course_info)

    if current_credits + added_credits > target_max + 3:
        return False

    for c in new_courses:
        completed.add(c)

    return True


def add_from_pool(
    completed,
    pool,
    course_info,
    prerequisites,
    valid_codes,
    target_min,
    target_max,
    max_courses=None
):
    pool = [c for c in pool if c in valid_codes and c not in completed]
    random.shuffle(pool)

    count = 0

    for c in pool:
        current_credits = total_credits(completed, course_info)

        if current_credits >= target_min:
            break

        added = add_course_with_prereqs(
            completed,
            c,
            course_info,
            prerequisites,
            valid_codes,
            target_max
        )

        if added:
            count += 1

        if max_courses is not None and count >= max_courses:
            break


# =========================================================
# SEMESTER LOGIC
# =========================================================

def choose_current_semester(year):
    """
    current_semester là học kỳ sắp bắt đầu.
    """

    if year == 1:
        if INCLUDE_SEMESTER_1_NEW_STUDENTS:
            return random.choice([1, 2])
        return 2

    if year == 2:
        return random.choice([3, 4])

    if year == 3:
        return random.choice([5, 6])

    return random.choice([7, 8])


def allowed_pools_by_semester(current_semester, pools, career_track):
    """
    Quy định nhóm môn có thể đã hoàn thành trước current_semester.
    """

    common = pools["common"]
    field = pools["field"]
    block = pools["block"]
    group = pools["group"]
    mandatory = pools["mandatory"]
    support = pools["support"]
    intro = pools["intro"]
    smart = pools["smart"]
    automation = pools["automation"]

    track_pool = smart if career_track == "Robot thông minh" else automation

    if current_semester == 1:
        return []

    if current_semester == 2:
        return intro + common + field

    if current_semester == 3:
        return intro + common + field + block

    if current_semester == 4:
        return intro + common + field + block + group

    if current_semester == 5:
        return common + field + block + group + mandatory[:6] + support[:2]

    if current_semester == 6:
        return common + field + block + group + mandatory + track_pool[:3] + support[:3]

    if current_semester == 7:
        return common + field + block + group + mandatory + track_pool[:5] + support[:4] + ["RBE4004"]

    if current_semester == 8:
        return common + field + block + group + mandatory + track_pool + support + ["RBE4004", "RBE3052"]

    return []


# =========================================================
# GRADES / GPA
# =========================================================

def choose_performance_level():
    r = random.random()

    if r < 0.10:
        return "weak"

    if r < 0.45:
        return "average"

    if r < 0.85:
        return "good"

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
        weights=[0.30, 0.25, 0.25, 0.20]
    )[0]


def calculate_gpa(course_grades, course_info):
    total_points = 0
    total_credits_value = 0

    for course, grade in course_grades.items():
        if course not in course_info:
            continue

        credits = course_info[course]["credits"]
        total_points += GRADE_TO_GPA[grade] * credits
        total_credits_value += credits

    if total_credits_value == 0:
        return 0.0

    return round(total_points / total_credits_value, 2)


def generate_failed_courses(completed_set, possible_pool, level):
    if level == "weak":
        k = random.choice([1, 1, 2, 2, 3])
    elif level == "average" and random.random() < 0.20:
        k = 1
    else:
        k = 0

    candidates = [
        c for c in possible_pool
        if c not in completed_set
    ]

    if not candidates:
        return []

    return random.sample(candidates, min(k, len(candidates)))


# =========================================================
# ADVISOR FIELDS
# =========================================================

def recommend_credits(gpa, failed_count, current_semester):
    if current_semester == 1:
        return 18

    if gpa < 2.0:
        return 14

    if gpa < 2.5:
        return 16

    if gpa < 3.2:
        return 18

    return random.choice([20, 22])


def study_hours(gpa, failed_count, current_semester):
    if current_semester == 1:
        return 8

    if gpa < 2.0:
        return random.choice([12, 13, 14, 15])

    if gpa < 2.5:
        return random.choice([10, 11, 12])

    if gpa < 3.2:
        return random.choice([8, 9, 10])

    return random.choice([6, 7, 8])


def risk_level(gpa, failed_count, current_semester):
    if current_semester == 1:
        return "NEW_STUDENT"

    if gpa < 2.0 or failed_count >= 2:
        return "HIGH"

    if gpa < 3.0 or failed_count == 1:
        return "MEDIUM"

    return "LOW"


def infer_weak_skills(career_goal, course_grades):
    weak = []
    low_grades = {"C", "D+", "D", "F"}

    skill_map = {
        "Toán nền tảng": ["MAT1041", "MAT1042", "MAT1093", "MAT1101"],
        "Lập trình": ["INT1008", "INT2210", "ELT3240"],
        "Điện tử - vi xử lý": ["ELT2201", "ELT3290", "ELT3240"],
        "Điều khiển": ["ELT3051", "RBE3012", "RBE3042"],
        "AI - Machine Learning": ["AIT2004", "RBE3043", "RBE3046", "RBE3056"],
        "Thị giác máy tính": ["RBE3015"],
        "ROS": ["RBE3017"],
    }

    for skill, courses in skill_map.items():
        if any(course_grades.get(c) in low_grades for c in courses):
            weak.append(skill)

    if "Vision" in career_goal or "Computer Vision" in career_goal:
        weak.append("OpenCV")

    if "AI" in career_goal or "Machine Learning" in career_goal:
        weak.append("Python")

    if "PLC" in career_goal or "SCADA" in career_goal:
        weak.append("PLC/SCADA")

    if (
        "Embedded" in career_goal
        or "Firmware" in career_goal
        or "Microcontroller" in career_goal
    ):
        weak.append("Embedded C/C++")

    return ";".join(sorted(set(weak)))


# =========================================================
# BUILD STUDENT PROFILE
# =========================================================

def build_completed_courses_for_student(
    current_semester,
    career_track,
    pools,
    course_info,
    prerequisites
):
    valid_codes = set(course_info.keys())

    completed = set()

    target_min, target_max = SEMESTER_CREDIT_RANGES[current_semester]

    if current_semester == 1:
        return completed

    allowed_pool = allowed_pools_by_semester(
        current_semester,
        pools,
        career_track
    )

    allowed_pool = [c for c in allowed_pool if c in valid_codes]

    # Ưu tiên môn nhập môn và đại cương trước
    ordered_pool = []

    for key in ["intro", "common", "field", "block", "group", "mandatory"]:
        for c in pools[key]:
            if c in allowed_pool and c not in ordered_pool:
                ordered_pool.append(c)

    track_key = "smart" if career_track == "Robot thông minh" else "automation"

    for c in pools[track_key]:
        if c in allowed_pool and c not in ordered_pool:
            ordered_pool.append(c)

    for c in pools["support"]:
        if c in allowed_pool and c not in ordered_pool:
            ordered_pool.append(c)

    random.shuffle(ordered_pool)

    # Với các kỳ đầu, giữ độ random nhưng không nhảy quá xa
    if current_semester <= 3:
        early_pool = []

        for key in ["intro", "common", "field", "block"]:
            for c in pools[key]:
                if c in allowed_pool:
                    early_pool.append(c)

        random.shuffle(early_pool)
        ordered_pool = early_pool

    for course in ordered_pool:
        current_credits = total_credits(completed, course_info)

        if current_credits >= target_min:
            break

        add_course_with_prereqs(
            completed,
            course,
            course_info,
            prerequisites,
            valid_codes,
            target_max
        )

    # Nếu vẫn chưa đủ target_min, cố gắng thêm môn phù hợp bất kỳ trong allowed_pool
    retry_pool = [c for c in allowed_pool if c not in completed]
    random.shuffle(retry_pool)

    for course in retry_pool:
        current_credits = total_credits(completed, course_info)

        if current_credits >= target_min:
            break

        add_course_with_prereqs(
            completed,
            course,
            course_info,
            prerequisites,
            valid_codes,
            target_max
        )

    return completed


def generate_students(df_courses):
    random.seed(RANDOM_SEED)

    course_info, prerequisites = build_course_maps(df_courses)

    pools = {
        "common": filter_by_category(df_courses, ["Khối kiến thức chung"]),
        "field": filter_by_category(df_courses, ["Khối kiến thức theo lĩnh vực"]),
        "block": filter_by_category(df_courses, ["Khối kiến thức theo khối ngành"]),
        "group": filter_by_category(df_courses, ["Khối kiến thức theo nhóm ngành"]),
        "mandatory": filter_by_category(df_courses, ["Khối kiến thức ngành bắt buộc"]),
        "support": filter_by_category(df_courses, ["Khối kiến thức bổ trợ"]),
        "smart": filter_by_category(df_courses, ["Robot thông minh"]),
        "automation": filter_by_category(df_courses, ["Tự động hóa"]),
        "intro": filter_by_name(df_courses, ["Nhập môn", "Trải nghiệm", "khám phá"]),
    }

    rows = []
    student_counter = 1

    for year, count in YEAR_DISTRIBUTION.items():
        for _ in range(count):
            student_id = f"UET{230000 + student_counter:06d}"

            current_semester = choose_current_semester(year)

            career_goal, career_track = random.choice(CAREER_PATHS)
            level = choose_performance_level()

            completed_set = build_completed_courses_for_student(
                current_semester=current_semester,
                career_track=career_track,
                pools=pools,
                course_info=course_info,
                prerequisites=prerequisites
            )

            possible_failed_pool = allowed_pools_by_semester(
                current_semester,
                pools,
                career_track
            )

            failed_courses = generate_failed_courses(
                completed_set=completed_set,
                possible_pool=possible_failed_pool,
                level=level
            )

            course_grades = {}

            # Môn hoàn thành: không cho F
            for c in sorted(completed_set):
                grade = random_grade(level)

                if grade == "F":
                    grade = "D"

                course_grades[c] = grade

            # Môn trượt
            for c in failed_courses:
                course_grades[c] = "F"

            gpa = calculate_gpa(course_grades, course_info)

            completed_credits = total_credits(completed_set, course_info)
            failed_count = len(failed_courses)

            rec_credits = recommend_credits(
                gpa,
                failed_count,
                current_semester
            )

            max_credits = min(22, rec_credits + 2)

            hours = study_hours(
                gpa,
                failed_count,
                current_semester
            )

            risk = risk_level(
                gpa,
                failed_count,
                current_semester
            )

            weak_skills = infer_weak_skills(
                career_goal,
                course_grades
            )

            completed_courses_str = ";".join(sorted(completed_set))

            course_grades_str = ";".join(
                f"{course}:{grade}"
                for course, grade in sorted(course_grades.items())
            )

            failed_courses_str = ";".join(sorted(failed_courses))

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

    assert df_students["gpa"].between(0, 4).all(), "GPA ngoài khoảng 0-4"

    assert (
        df_students["completed_credits"] <= TOTAL_PROGRAM_CREDITS
    ).all(), "completed_credits vượt 150"

    for _, row in df_students.iterrows():
        sem = int(row["current_semester"])
        credits = int(row["completed_credits"])

        min_credit, max_credit = SEMESTER_CREDIT_RANGES[sem]

        if not (min_credit <= credits <= max_credit + 3):
            raise ValueError(
                f"Sinh viên {row['student_id']} có current_semester={sem}, "
                f"completed_credits={credits}, ngoài khoảng hợp lý "
                f"{min_credit}-{max_credit}"
            )

    # Kiểm tra kỳ 1
    sem1 = df_students[df_students["current_semester"] == 1]

    if not sem1.empty:
        assert (
            sem1["completed_credits"] == 0
        ).all(), "Sinh viên kỳ 1 phải có completed_credits = 0"

    # Kiểm tra không có năm 1 kỳ 1 đã học nhiều tín
    bad = df_students[
        (df_students["current_semester"] == 1) &
        (df_students["completed_credits"] > 0)
    ]

    assert bad.empty, "Có sinh viên kỳ 1 đã có tín chỉ hoàn thành"

    # Kiểm tra năm 1 không có đồ án/thực tập/tốt nghiệp
    year1 = df_students[df_students["year"] == 1]

    forbidden = ["RBE4001", "RBE4003", "RBE4004", "RBE3052"]

    for code in forbidden:
        bad_rows = year1[
            year1["completed_courses"].astype(str).str.contains(code, na=False)
        ]

        assert bad_rows.empty, f"Năm 1 không được có {code}"


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

    print("=" * 70)
    print("ĐÃ TẠO XONG student_profiles.csv")
    print("=" * 70)

    print("Số sinh viên:", len(df_students))

    print("\nPhân bố năm học:")
    print(df_students["year"].value_counts().sort_index())

    print("\nPhân bố current_semester:")
    print(df_students["current_semester"].value_counts().sort_index())

    print("\nThống kê completed_credits theo current_semester:")
    print(
        df_students
        .groupby("current_semester")["completed_credits"]
        .agg(["min", "max", "mean"])
        .round(2)
    )

    print("\nPhân bố risk_level:")
    print(df_students["risk_level"].value_counts())

    print("\nGPA trung bình:", round(df_students["gpa"].mean(), 2))

    print("\nFile đầu ra:", OUTPUT_FILE)


if __name__ == "__main__":
    main()