# ============================================================
# MODULE 2 — A* CORE
# Tìm Top-K lộ trình tối ưu cho 2 kỳ học tiếp theo
# ============================================================

import heapq
from core.utility import AcademicUtility
from config import (
    MAX_SEMESTERS,
    BEAM_WIDTH,
    W_EARLY_FOUNDATION_BONUS,
    W_EARLY_GENERAL_PENALTY,
)


class AcademicAStar:

    def __init__(self, course_db: dict, priority_courses: list, max_semesters: int = MAX_SEMESTERS):
        """
        course_db        : dict {course_id: {'credits': int, 'category': str, ...}}
        priority_courses : list các môn quan trọng theo career goal
        max_semesters    : độ sâu tối đa (mặc định 2 kỳ)
        """
        self.course_db        = course_db
        self.priority_courses = set(priority_courses)
        self.max_semesters    = max_semesters

    # ----------------------------------------------------------
    # Hàm tìm kiếm chính
    # ----------------------------------------------------------
    def search_path(
        self,
        initial_passed_with_grades: dict,
        get_valid_combinations_func,
        max_credits: int = 21
    ) -> list:
        """
        Trả về top-K lộ trình tốt nhất, mỗi lộ trình là list các action (kỳ học).

        initial_passed_with_grades : dict {"MÃ_MÔN": "ĐIỂM_CHỮ"}
        get_valid_combinations_func: callable từ Module 1, nhận list môn đã học
                                     → trả về list các tổ hợp môn hợp lệ

        Cấu trúc open_set: (f, g, passed_set, path_history)
          - path_history: list of actions, mỗi action là frozenset môn 1 kỳ
        """
        start_passed_set = frozenset(initial_passed_with_grades.keys())

        # h ban đầu
        initial_remaining = self.priority_courses - start_passed_set
        initial_h = AcademicUtility.calculate_h_heuristic(initial_remaining, self.course_db)

        # (f, g, passed_set, path)
        open_set = []
        heapq.heappush(open_set, (initial_h, 0.0, start_passed_set, []))

        # closed_set lưu (passed_set, depth) để cho phép cùng state ở depth khác nhau
        closed_set = set()
        top_k_paths = []

        while open_set and len(top_k_paths) < BEAM_WIDTH:
            f, g, passed_set, path = heapq.heappop(open_set)

            state_key = (passed_set, len(path))
            if state_key in closed_set:
                continue
            closed_set.add(state_key)

            # ── GOAL: đã lên kế hoạch đủ max_semesters kỳ ──
            if len(path) >= self.max_semesters:
                top_k_paths.append({
                    'rank'            : len(top_k_paths) + 1,
                    'f_score'         : round(f, 3),
                    'g_score'         : round(g, 3),
                    'semesters'       : [list(action) for action in path],
                    'total_credits'   : self._total_credits(path),
                    'priority_covered': list(self.priority_courses & passed_set),
                    'priority_missing': list(self.priority_courses - passed_set),
                })
                continue

            # ── EXPAND: lấy tổ hợp môn hợp lệ từ Module 1 ──
            valid_actions = get_valid_combinations_func(list(passed_set))

            for action in valid_actions:
                if not action:
                    continue

                action_set   = frozenset(action)
                new_passed   = passed_set | action_set
                new_path     = path + [action_set]
                new_state_key = (new_passed, len(new_path))

                if new_state_key in closed_set:
                    continue

                # g(n): luôn dùng initial_passed_with_grades để giữ GPA gốc
                step_cost = AcademicUtility.calculate_g_cost(
                    list(action_set),
                    initial_passed_with_grades,   # ← GPA gốc, không bị pha loãng
                    self.course_db,
                    max_credits
                )
                if len(path) == 0:
                    step_cost += self._early_semester_adjustment(action_set)
                new_g = g + step_cost

                # h(n): admissible
                new_remaining = self.priority_courses - new_passed
                new_h = AcademicUtility.calculate_h_heuristic(new_remaining, self.course_db)

                new_f = new_g + new_h
                heapq.heappush(open_set, (new_f, new_g, new_passed, new_path))

        return top_k_paths

    # ----------------------------------------------------------
    # Helper
    # ----------------------------------------------------------
    def _total_credits(self, path: list) -> int:
        total = 0
        for action in path:
            for cid in action:
                total += self.course_db.get(cid, {}).get('credits', 3)
        return total

    def _early_semester_adjustment(self, action: list) -> float:
        adjustment = 0.0
        for cid in action:
            category = self.course_db.get(cid, {}).get('category', '').lower()
            if 'kiến thức chung' in category or 'bổ trợ' in category:
                adjustment += W_EARLY_GENERAL_PENALTY
            elif (
                'lĩnh vực' in category
                or 'khối ngành' in category
                or 'nhóm ngành' in category
                or 'ngành bắt buộc' in category
                or 'ngành lựa chọn' in category
            ):
                adjustment -= W_EARLY_FOUNDATION_BONUS
        return adjustment
