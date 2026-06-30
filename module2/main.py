# ============================================================
# MODULE 2 — MAIN PIPELINE
# Kết nối trực tiếp với output JSON của Module 1
# ============================================================

import json
import argparse
import sys
import pandas as pd
import unicodedata
from pathlib import Path
from itertools import combinations

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from core.astar    import AcademicAStar
from core.enricher import PlanEnricher
from config        import MIN_CREDITS_DEFAULT


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / 'data'


def read_csv_auto(file_path):
    encodings = ['utf-8-sig', 'utf-8', 'cp1258', 'latin1']
    last_error = None
    for enc in encodings:
        try:
            return pd.read_csv(file_path, encoding=enc)
        except Exception as exc:
            last_error = exc
    raise ValueError(f'Cannot read CSV file: {file_path}') from last_error


def normalize_text(text):
    text = '' if pd.isna(text) else str(text).lower().strip()
    text = unicodedata.normalize('NFD', text)
    return ''.join(ch for ch in text if unicodedata.category(ch) != 'Mn')


def split_semicolon(value):
    if pd.isna(value):
        return []
    return [item.strip() for item in str(value).split(';') if item.strip()]


def resolve_course_tokens(course_tokens, course_db):
    name_to_code = {
        normalize_text(info.get('course_name', '')): code
        for code, info in course_db.items()
        if info.get('course_name')
    }

    resolved = []
    for token in course_tokens:
        if token in course_db:
            code = token
        else:
            code = name_to_code.get(normalize_text(token))

        if code and code not in resolved:
            resolved.append(code)

    return resolved


# ── 1. Đọc output JSON từ Module 1 ───────────────────────────
def load_module1_output(json_path: str) -> dict:
    with open(json_path, encoding='utf-8') as f:
        return json.load(f)


def extract_from_module1(m1: dict) -> dict:
    """
    Trích xuất đúng các field Module 2 cần từ JSON của Module 1.

    Trả về dict gồm:
      student_id, career_goal, passed_with_grades,
      max_credits, eligible_courses (list course_code),
      course_db (dict code → {credits, category, semester})
    """
    state       = m1['student_state']
    constraints = m1['constraints']
    search      = m1['search_space']

    # passed_with_grades: {"MÃ_MÔN": "ĐIỂM_CHỮ"}
    grade_map = state.get('course_grades', {})
    passed    = state.get('passed_courses', [])

    # Với môn passed nhưng không có điểm trong grade_map → gán 'B' mặc định
    passed_with_grades = {
        c: grade_map.get(c, 'B')
        for c in passed
    }

    # course_db từ eligible_courses của Module 1
    course_db = {}
    for c in search.get('eligible_courses', []):
        course_db[c['course_code']] = {
            'credits' : c['credits'],
            'category': c['category'],
            'semester': c.get('semester', 1),
            'course_name': c.get('course_name', ''),
        }

    # Danh sách môn hợp lệ (đã lọc tiên quyết, quy chế bởi Module 1)
    eligible_codes = [
        c['course_code']
        for c in search.get('candidate_courses_for_module2', [])
    ]

    return {
        'student_id'        : state['student_id'],
        'career_goal'       : state['career_goal'],
        'current_semester'  : state['current_semester'],
        'passed_with_grades': passed_with_grades,
        'max_credits'       : constraints['credit_limit_per_semester'],
        'eligible_codes'    : eligible_codes,
        'course_db'         : course_db,
    }


# ── 2. Connector Module 1 → Module 2 ─────────────────────────
def make_combo_func(
    eligible_codes: list,
    course_db: dict,
    max_credits: int,
    min_credits: int = MIN_CREDITS_DEFAULT,
):
    """
    Sinh tổ hợp môn hợp lệ từ danh sách C_eligible của Module 1.
    Module 1 đã lọc tiên quyết → Module 2 chỉ cần lọc thêm tổng tín chỉ.

    Chiến lược:
      - Ưu tiên combo 7-6-5-4-3 môn để đạt ngưỡng tín chỉ tối thiểu
      - Chỉ nhận combo có min_credits <= tổng tín chỉ <= max_credits
      - Giới hạn 30 combo để tránh bùng nổ
    """
    def get_valid_combinations(passed_courses: list) -> list:
        # Lọc ra môn chưa học trong passed_courses hiện tại
        available = [c for c in eligible_codes if c not in passed_courses]

        # Nếu có quá nhiều môn, chỉ dùng top 20 để tránh khai thác tổ hợp quá lớn.
        if len(available) > 20:
            available = available[:20]

        valid = []
        for size in [7, 6, 5, 4, 3]:
            for combo in combinations(available, min(size, len(available))):
                total = sum(course_db.get(c, {}).get('credits', 3) for c in combo)
                if min_credits <= total <= max_credits:
                    valid.append(list(combo))
                if len(valid) >= 30:
                    return valid
        return valid

    return get_valid_combinations


# ── 3. Load career_paths.csv ──────────────────────────────────
def get_priority_courses(career_goal: str, career_paths_path: str, course_db: dict) -> list:
    try:
        df = read_csv_auto(career_paths_path)
        rows = df[df['career_goal'] == career_goal]
        if rows.empty:
            return []
        priority_tokens = []
        for _, row in rows.iterrows():
            priority_tokens.extend(split_semicolon(row.get('priority_courses', '')))
        return resolve_course_tokens(priority_tokens, course_db)
    except Exception:
        return []


# ── 4. Pipeline chính ─────────────────────────────────────────
def run_module2(
    module1_json_path  : str,
    career_paths_path  : str = DATA_DIR / 'career_paths.csv',
) -> dict:
    """
    Nhận path tới module1_output.json → chạy A* → enrich → trả về dict.
    """
    m1   = load_module1_output(module1_json_path)
    info = extract_from_module1(m1)

    career_goal        = info['career_goal']
    passed_with_grades = info['passed_with_grades']
    course_db          = info['course_db']
    max_credits        = info['max_credits']
    eligible_codes     = info['eligible_codes']

    # Priority courses từ career_paths.csv
    priority_courses = get_priority_courses(career_goal, career_paths_path, course_db)

    # Nếu không có trong career_paths.csv, fallback: dùng eligible codes có priority cao
    if not priority_courses:
        top_candidates = [
            c['course_code']
            for c in m1['search_space']['candidate_courses_for_module2'][:10]
        ]
        priority_courses = top_candidates

    # Combo function từ C_eligible của Module 1
    get_valid_combos = make_combo_func(
        eligible_codes = eligible_codes,
        course_db      = course_db,
        max_credits    = max_credits,
        min_credits    = MIN_CREDITS_DEFAULT,
    )

    # Chạy A*
    astar = AcademicAStar(
        course_db        = course_db,
        priority_courses = priority_courses,
    )
    top_k_plans = astar.search_path(
        initial_passed_with_grades  = passed_with_grades,
        get_valid_combinations_func = get_valid_combos,
        max_credits                 = max_credits,
    )

    # Enrich skills (nếu có career_paths.csv)
    try:
        career_paths_df = read_csv_auto(career_paths_path)
        enricher        = PlanEnricher(career_goal, career_paths_df, course_db)
        enriched        = enricher.enrich(top_k_plans)
    except Exception:
        enriched = top_k_plans   # fallback nếu không có file career_paths

    return {
        'module'            : 'Module 2 - A* Search & Planning Engine',
        'output_for'        : 'Module 3 - Re-ranking & Recommendation Engine',
        'student_id'        : info['student_id'],
        'career_goal'       : career_goal,
        'current_semester'  : info['current_semester'],
        'constraints_used'  : {
            'max_credits_per_semester': max_credits,
            'min_credits_per_semester': MIN_CREDITS_DEFAULT,
            'planning_horizon'        : '2 kỳ',
        },
        'top_k_recommendations': enriched,
    }


# ── 5. Entry point CLI ────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description='Module 2 - A* Planning, nhận output JSON từ Module 1'
    )
    parser.add_argument(
        '--module1_output',
        default=DATA_DIR / 'module1_output.json',
        help='Path tới file JSON output của Module 1'
    )
    parser.add_argument(
        '--career_paths',
        default=DATA_DIR / 'career_paths.csv',
        help='Path tới career_paths.csv'
    )
    parser.add_argument(
        '--output',
        default=BASE_DIR / 'module2_output.json',
        help='Path file JSON output của Module 2 (cho Module 3)'
    )
    args = parser.parse_args()

    if not Path(args.module1_output).exists():
        raise FileNotFoundError(f'Không tìm thấy: {args.module1_output}')

    result = run_module2(
        module1_json_path = args.module1_output,
        career_paths_path = args.career_paths,
    )

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # In summary ra terminal
    print('=' * 60)
    print('MODULE 2 OUTPUT')
    print('=' * 60)
    print(f"Student   : {result['student_id']}")
    print(f"Career    : {result['career_goal']}")
    print(f"Semester  : {result['current_semester']}")
    print(f"Plans found: {len(result['top_k_recommendations'])}")
    print()
    for plan in result['top_k_recommendations']:
        print(f"  Rank {plan['rank']} | f={plan['f_score']}")
        for i, sem in enumerate(plan['semesters'], 1):
            print(f"    Kỳ +{i}: {sem}")
        print(f"    Skills covered : {plan.get('covered_skills', [])}")
        print(f"    Skills missing : {plan.get('missing_skills', [])}")
        print(f"    Career match   : {plan.get('career_match_ratio', 'N/A')}")
        print()
    print(f"Output saved: {args.output}")
    print('=' * 60)


if __name__ == '__main__':
    main()
