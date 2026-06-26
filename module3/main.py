# ============================================================
# MODULE 3 — MAIN PIPELINE
# Input : module2_output.json + student_profiles.csv
# Output: top_3 recommendations cá nhân hóa hoàn chỉnh
# ============================================================

import json
import argparse
import csv
from pathlib import Path

from core.knn_engine import KNNEngine
from core.reranker   import PlanReranker
from config          import K_NEIGHBORS


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
MODULE2_DIR = PROJECT_DIR / 'module2'
DEFAULT_MODULE2_OUTPUT = MODULE2_DIR / 'module2_output.json'
DEFAULT_PROFILES = MODULE2_DIR / 'data' / 'student_profiles.csv'
DEFAULT_COURSES = MODULE2_DIR / 'data' / 'courses.csv'
DEFAULT_OUTPUT = BASE_DIR / 'module3_output.json'


def _load_student_profile(student_id: str, profiles_path: str) -> dict:
    """Tìm profile của sinh viên trong CSV để bổ sung context cho Module 3."""
    try:
        with open(profiles_path, encoding='utf-8-sig', newline='') as f:
            for row in csv.DictReader(f):
                if str(row.get('student_id', '')) == str(student_id):
                    return row
    except FileNotFoundError:
        return {}
    return {}


def _load_course_credits(courses_path: str) -> dict:
    try:
        with open(courses_path, encoding='utf-8-sig', newline='') as f:
            return {
                row['course_code']: _to_int(row.get('credits'), 0)
                for row in csv.DictReader(f)
                if row.get('course_code')
            }
    except FileNotFoundError:
        return {}


def _load_course_catalog(courses_path: str) -> dict:
    try:
        with open(courses_path, encoding='utf-8-sig', newline='') as f:
            return {
                row['course_code']: {
                    'course_name': row.get('course_name', ''),
                    'credits': _to_int(row.get('credits'), 0),
                    'category': row.get('category', ''),
                }
                for row in csv.DictReader(f)
                if row.get('course_code')
            }
    except FileNotFoundError:
        return {}


def _to_float(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value, default: int) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _build_student_context(m2: dict, profiles_path: str) -> dict:
    if 'student_context' in m2:
        return m2['student_context']

    student_id = m2.get('student_id', '')
    profile = _load_student_profile(student_id, profiles_path)
    constraints = m2.get('constraints_used', {})

    credit_limit = (
        constraints.get('max_credits_per_semester')
        or profile.get('max_credits_per_semester')
        or 18
    )

    return {
        'student_id': student_id,
        'career_goal': m2.get('career_goal') or profile.get('career_goal', ''),
        'career_track': profile.get('career_track', ''),
        'current_semester': _to_int(m2.get('current_semester') or profile.get('current_semester'), 1),
        'gpa': _to_float(profile.get('gpa'), 2.5),
        'completed_credits': _to_int(profile.get('completed_credits'), 0),
        'credit_limit': _to_int(credit_limit, 18),
        'risk_level': profile.get('risk_level', 'MEDIUM') or 'MEDIUM',
    }


def _normalize_semesters(plan: dict, course_credits: dict) -> list:
    def semester_credits(courses: list) -> int:
        return sum(course_credits.get(course, 0) for course in courses)

    semesters = plan.get('semesters')
    if semesters and isinstance(semesters, list):
        normalized = []
        for i, sem in enumerate(semesters):
            courses = sem.get('courses', []) if isinstance(sem, dict) else sem
            total_credits = sem.get('total_credits') if isinstance(sem, dict) else None
            normalized.append({
                'semester_offset': i + 1,
                'courses': courses,
                'total_credits': total_credits if total_credits is not None else semester_credits(courses),
            })
        return normalized

    micro_plan = plan.get('micro_plan', {})
    normalized = []
    for i, (_, sem) in enumerate(micro_plan.items()):
        courses = sem.get('courses', []) if isinstance(sem, dict) else []
        normalized.append({
            'semester_offset': i + 1,
            'courses': courses,
            'total_credits': sem.get('total_credits', semester_credits(courses)) if isinstance(sem, dict) else 0,
        })
    return normalized


def _normalize_plans(plans: list, course_credits: dict) -> list:
    normalized = []
    for plan in plans:
        semesters = _normalize_semesters(plan, course_credits)
        total_credits = (
            plan.get('total_credits_2sem')
            or plan.get('total_credits')
            or sum(
                sem.get('total_credits', 0)
                for sem in semesters
                if isinstance(sem.get('total_credits'), (int, float))
            )
        )

        normalized.append({
            **plan,
            'semesters': semesters,
            'total_credits_2sem': _to_int(total_credits, 0),
        })
    return normalized


def _is_foundation_or_major_course(category: str) -> bool:
    normalized = category.lower()
    return (
        'lĩnh vực' in normalized
        or 'khối ngành' in normalized
        or 'nhóm ngành' in normalized
        or 'ngành bắt buộc' in normalized
        or 'ngành lựa chọn' in normalized
    )


def _attach_plan_metrics(plan: dict, course_catalog: dict) -> dict:
    semester_credits = [sem.get('total_credits', 0) for sem in plan.get('semesters', [])]
    total_credits = sum(c for c in semester_credits if isinstance(c, (int, float)))
    foundation_credits = 0
    first_sem_foundation_credits = 0

    for sem_index, sem in enumerate(plan.get('semesters', [])):
        for course in sem.get('courses', []):
            info = course_catalog.get(course, {})
            if _is_foundation_or_major_course(info.get('category', '')):
                foundation_credits += info.get('credits', 0)
                if sem_index == 0:
                    first_sem_foundation_credits += info.get('credits', 0)

    overall_foundation_score = foundation_credits / total_credits if total_credits else 0.0
    first_sem_total = semester_credits[0] if semester_credits else 0
    early_foundation_score = (
        first_sem_foundation_credits / first_sem_total
        if first_sem_total
        else 0.0
    )
    foundation_score = 0.7 * overall_foundation_score + 0.3 * early_foundation_score

    if len(semester_credits) >= 2 and total_credits:
        avg = total_credits / len(semester_credits)
        max_diff = max(abs(c - avg) for c in semester_credits)
        balance_score = max(0.0, 1.0 - max_diff / max(avg, 1))
    else:
        balance_score = 0.5

    return {
        **plan,
        'plan_metrics': {
            'semester_credits': semester_credits,
            'foundation_credits': foundation_credits,
            'first_sem_foundation_credits': first_sem_foundation_credits,
            'overall_foundation_score': round(overall_foundation_score, 3),
            'early_foundation_score': round(early_foundation_score, 3),
            'foundation_score': round(foundation_score, 3),
            'balance_score': round(balance_score, 3),
        },
    }


def run_module3(
    module2_json_path    : str,
    student_profiles_path: str,
    output_path          : str = None,
    courses_path         : str = DEFAULT_COURSES,
    k                    : int = K_NEIGHBORS,
    verbose              : bool = True,
) -> dict:
    """
    Pipeline chính Module 3.

    1. Đọc output Module 2
    2. k-NN: tìm K sinh viên tương tự từ student_profiles.csv
    3. Re-rank Top-K plans theo peer insights
    4. Recommend study_hours từ peer average
    5. Recommend skills từ missing_skills + peer weak_skills
    6. Format output cuối
    """

    # ── 1. Load Module 2 output ───────────────────────────────
    with open(module2_json_path, encoding='utf-8') as f:
        m2 = json.load(f)

    ctx            = _build_student_context(m2, student_profiles_path)
    course_catalog = _load_course_catalog(courses_path)
    course_credits = {
        code: info['credits']
        for code, info in course_catalog.items()
    }
    plans          = [
        _attach_plan_metrics(plan, course_catalog)
        for plan in _normalize_plans(m2['top_k_recommendations'], course_credits)
    ]

    # ── 2. k-NN: tìm K peers ─────────────────────────────────
    knn       = KNNEngine(student_profiles_path)
    neighbors = knn.find_neighbors(ctx, k=k)

    # ── 3. Re-rank plans ──────────────────────────────────────
    reranker      = PlanReranker()
    reranked_plans = reranker.rerank(plans, neighbors, ctx['credit_limit'], ctx)

    # ── 4. Study hours ────────────────────────────────────────
    # Lấy tổng credits từ plan rank 1 (sau khi re-rank)
    best_plan    = reranked_plans[0] if reranked_plans else plans[0]
    study_hours  = knn.recommend_study_hours(
        neighbors    = neighbors,
        credit_load  = best_plan['total_credits_2sem'] // 2,
        risk_level   = ctx['risk_level'],
    )

    # ── 5. Skills ─────────────────────────────────────────────
    # Lấy missing_skills từ plan rank 1
    missing = best_plan.get('missing_skills', [])
    skills  = knn.recommend_skills(neighbors, missing, ctx['career_goal'])

    # ── 6. Format output ──────────────────────────────────────
    output = {
        'module'    : 'Module 3 - k-NN Re-ranking & Recommendation Engine',
        'output_for': 'Final Student Interface',

        'student_context': ctx,

        'knn_metadata': {
            'k'          : k,
            'neighbors_found': len(neighbors),
            'neighbors'  : [
                {
                    'student_id'          : n['student_id'],
                    'gpa'                 : n['gpa'],
                    'career_goal'         : n['career_goal'],
                    'distance'            : n['distance'],
                    'study_hours_per_week': n['study_hours_per_week'],
                }
                for n in neighbors
            ],
        },

        # ── OUTPUT CHÍNH ──
        'final_output': {

            # Output 1: Lộ trình 2 kỳ (re-ranked)
            'roadmap': [
                {
                    'rank'         : p['rank'],
                    'final_score'  : p['final_score'],
                    'score_breakdown': p['score_breakdown'],
                    'plan_metrics': p.get('plan_metrics', {}),
                    'semesters'    : p['semesters'],
                    'total_credits': p['total_credits_2sem'],
                    'covered_skills': p.get('covered_skills', []),
                }
                for p in reranked_plans
            ],

            # Output 2: Kỹ năng nên bổ sung
            'skills_to_improve': skills,

            # Output 3: Giờ tự học mỗi tuần
            'study_hours_per_week': study_hours,
        },
    }

    # ── 7. Lưu JSON ───────────────────────────────────────────
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=4)

    if verbose:
        _print_summary(output)

    return output


# ----------------------------------------------------------
# Print summary
# ----------------------------------------------------------
def _print_summary(output: dict):
    ctx    = output['student_context']
    final  = output['final_output']
    knn    = output['knn_metadata']

    print('=' * 65)
    print('MODULE 3 OUTPUT — KẾT QUẢ CUỐI CHO SINH VIÊN')
    print('=' * 65)
    print(f"Student  : {ctx['student_id']}")
    print(f"GPA      : {ctx['gpa']}  |  Risk: {ctx['risk_level']}")
    print(f"Career   : {ctx['career_goal']}")
    print(f"k-NN     : tìm được {knn['neighbors_found']} peers")

    print('\n── PEERS GẦN NHẤT ──')
    for n in knn['neighbors'][:3]:
        print(f"  {n['student_id']} | GPA {n['gpa']} | {n['career_goal']} | dist={n['distance']}")

    print('\n── LỘ TRÌNH 2 KỲ (re-ranked) ──')
    for p in final['roadmap']:
        print(f"\n  [Rank {p['rank']}]  score={p['final_score']}"
              f"  (career={p['score_breakdown']['career_score']}"
              f", peer={p['score_breakdown']['peer_score']}"
              f", load={p['score_breakdown']['load_score']}"
              f", foundation={p['score_breakdown']['foundation_score']}"
              f", balance={p['score_breakdown']['balance_score']})")
        for sem in p['semesters']:
            print(f"    Kỳ +{sem['semester_offset']}: {sem['courses']}  ({sem['total_credits']} TC)")

    print('\n── KỸ NĂNG NÊN BỔ SUNG ──')
    for s in final['skills_to_improve']:
        print(f"  [{s['priority'].upper()}] {s['skill']}  ({s['source']})")

    print('\n── GIỜ TỰ HỌC MỖI TUẦN ──')
    sh = final['study_hours_per_week']
    print(f"  Tổng     : {sh['total_per_week']} giờ/tuần")
    print(f"  Lý thuyết: {sh['breakdown']['ly_thuyet']} giờ")
    print(f"  Thực hành: {sh['breakdown']['thuc_hanh']} giờ")
    print(f"  Project  : {sh['breakdown']['project']} giờ")
    print(f"  (Peer avg: {sh['peer_average']}h | Formula: {sh['formula_hours']}h)")
    print('=' * 65)


# ----------------------------------------------------------
# CLI
# ----------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description='Module 3 - k-NN Recommendation Engine')
    parser.add_argument('--module2',  default=DEFAULT_MODULE2_OUTPUT, help='module2_output.json')
    parser.add_argument('--profiles', default=DEFAULT_PROFILES, help='student_profiles.csv')
    parser.add_argument('--courses',  default=DEFAULT_COURSES, help='courses.csv')
    parser.add_argument('--output',   default=DEFAULT_OUTPUT)
    parser.add_argument('--k',        type=int, default=K_NEIGHBORS)
    parser.add_argument('--no-verbose', action='store_true')
    args = parser.parse_args()

    run_module3(
        module2_json_path     = args.module2,
        student_profiles_path = args.profiles,
        output_path           = args.output,
        courses_path          = args.courses,
        k                     = args.k,
        verbose               = not args.no_verbose,
    )


if __name__ == '__main__':
    main()
