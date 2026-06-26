# ============================================================
# MODULE 2 — UTILITY
# Tính g(n), h(n), GPA và enrich skills cho output
# ============================================================

from config import (
    W_CREDITS,
    W_HARD_COURSE,
    W_CAREER,
    W_GENERAL_COURSE_PENALTY,
    W_FOUNDATION_COURSE_BONUS,
    GRADE_MAPPING,
    GPA_LOW,
)


class AcademicUtility:

    # ----------------------------------------------------------
    # GPA
    # ----------------------------------------------------------
    @staticmethod
    def calculate_current_gpa(passed_courses_with_grades: dict) -> float:
        """
        Tính GPA tích lũy từ dict {"MÃ_MÔN": "ĐIỂM_CHỮ"}.
        Trả về 2.5 nếu chưa học môn nào.
        """
        if not passed_courses_with_grades:
            return 2.5

        total, count = 0.0, 0
        for grade in passed_courses_with_grades.values():
            if grade in GRADE_MAPPING:
                total += GRADE_MAPPING[grade]
                count += 1

        return round(total / count, 2) if count > 0 else 2.5

    # ----------------------------------------------------------
    # g(n) — chi phí thực tế
    # ----------------------------------------------------------
    @staticmethod
    def calculate_g_cost(
        current_semester_courses: list,
        original_passed_with_grades: dict,   # luôn dùng GPA gốc, không dùng dict tương lai
        course_db: dict,
        max_credits: int = 21
    ) -> float:
        """
        Chi phí g(n) đo áp lực học kỳ:
          - Chi phí nền = tổng tín chỉ × W_CREDITS
          - Phạt nặng nếu GPA thấp mà đăng ký > max_credits
          - Phạt dồn môn chuyên ngành (level 3/4 hoặc ROB)
        """
        total_credits   = 0
        hard_course_cnt = 0
        general_course_cnt = 0
        foundation_course_cnt = 0

        # Dùng GPA gốc để giữ đặc trưng học lực thực của sinh viên
        student_gpa = AcademicUtility.calculate_current_gpa(original_passed_with_grades)

        for cid in current_semester_courses:
            info = course_db.get(cid, {'credits': 3, 'category': ''})
            total_credits += info.get('credits', 3)
            category = info.get('category', '').lower()

            # Môn chuyên ngành nặng: cấp 3/4 hoặc thuộc khối Robot
            if '3' in cid or '4' in cid or 'ROB' in cid.upper():
                hard_course_cnt += 1
            if 'kiến thức chung' in category or 'bổ trợ' in category:
                general_course_cnt += 1
            elif (
                'lĩnh vực' in category
                or 'khối ngành' in category
                or 'nhóm ngành' in category
                or 'ngành bắt buộc' in category
                or 'ngành lựa chọn' in category
            ):
                foundation_course_cnt += 1

        cost = total_credits * W_CREDITS
        cost += general_course_cnt * W_GENERAL_COURSE_PENALTY
        cost -= foundation_course_cnt * W_FOUNDATION_COURSE_BONUS

        # Phạt thích ứng: GPA thấp + quá tải tín chỉ
        if student_gpa < GPA_LOW and total_credits > max_credits:
            cost += 50.0

        # Phạt dồn môn khó
        if hard_course_cnt > 2:
            cost += (hard_course_cnt - 2) * W_HARD_COURSE

        return cost

    # ----------------------------------------------------------
    # h(n) — heuristic (admissible)
    # ----------------------------------------------------------
    @staticmethod
    def calculate_h_heuristic(
        remaining_priority_courses: set,
        course_db: dict
    ) -> float:
        """
        h(n) = tổng tín chỉ tối thiểu của các môn priority còn thiếu
               chia cho MAX_CREDITS_PER_SEM để scale về số kỳ.

        Admissible vì không overestimate: mỗi môn cần ít nhất 1 kỳ,
        và ta tính theo tín chỉ thực tế nhỏ nhất.
        """
        if not remaining_priority_courses:
            return 0.0

        total_min_credits = sum(
            course_db.get(c, {}).get('credits', 3) * W_CREDITS
            for c in remaining_priority_courses
        )
        # Chia cho tín chỉ tối đa/kỳ để quy về đơn vị "số kỳ còn lại"
        MAX_CREDITS_PER_SEM = 21
        return total_min_credits / MAX_CREDITS_PER_SEM

    # ----------------------------------------------------------
    # Enrich skills cho output
    # ----------------------------------------------------------
    @staticmethod
    def get_covered_skills(
        courses_in_plan: list,
        career_goal: str,
        career_paths_df
    ) -> list:
        """
        Map môn học trong plan → kỹ năng tương ứng theo career_paths.csv.
        """
        rows = career_paths_df[career_paths_df['career_goal'] == career_goal]
        if rows.empty:
            return []

        row = rows.iloc[0]
        priority_list = row['priority_courses'].split(';')
        skill_list    = row['required_skills'].split(';')

        # Zip môn → skill (theo thứ tự trong file)
        skill_map = dict(zip(priority_list, skill_list))

        covered = set(courses_in_plan) & set(priority_list)
        return [skill_map[c] for c in covered if c in skill_map]

    @staticmethod
    def get_missing_skills(
        career_goal: str,
        covered_skills: list,
        career_paths_df
    ) -> list:
        """
        Trả về danh sách kỹ năng còn thiếu so với yêu cầu career goal.
        """
        rows = career_paths_df[career_paths_df['career_goal'] == career_goal]
        if rows.empty:
            return []

        row = rows.iloc[0]
        all_skills = set(row['required_skills'].split(';'))
        return list(all_skills - set(covered_skills))
