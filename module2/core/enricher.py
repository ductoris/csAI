# ============================================================
# MODULE 2 — ENRICHER
# Bổ sung thông tin skills vào Top-K plans từ A*
# Đây là "cầu nối" cung cấp nguyên liệu cho Module 3
# ============================================================

from core.utility import AcademicUtility


class PlanEnricher:

    def __init__(self, career_goal: str, career_paths_df):
        """
        career_goal     : mục tiêu nghề nghiệp của sinh viên
        career_paths_df : DataFrame từ career_paths.csv
        """
        self.career_goal     = career_goal
        self.career_paths_df = career_paths_df

    def enrich(self, top_k_plans: list) -> list:
        """
        Nhận Top-K plans từ A*, bổ sung:
          - covered_skills : kỹ năng đã cover qua các môn trong plan
          - missing_skills : kỹ năng còn thiếu so với career goal
          - career_match_ratio : % kỹ năng đã cover

        Output này được truyền thẳng vào Module 3.
        """
        enriched = []
        for plan in top_k_plans:
            # Gom tất cả môn học trong 2 kỳ
            all_courses = [c for sem in plan['semesters'] for c in sem]

            covered = AcademicUtility.get_covered_skills(
                all_courses, self.career_goal, self.career_paths_df
            )
            missing = AcademicUtility.get_missing_skills(
                self.career_goal, covered, self.career_paths_df
            )

            total_skills = len(covered) + len(missing)
            ratio = round(len(covered) / total_skills, 2) if total_skills > 0 else 0.0

            enriched.append({
                **plan,
                'covered_skills'     : covered,
                'missing_skills'     : missing,
                'career_match_ratio' : ratio,
            })

        return enriched