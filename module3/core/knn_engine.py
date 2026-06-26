# ============================================================
# MODULE 3 — k-NN ENGINE
# Vector hóa sinh viên → tìm K peers → extract study_hours + skills
# ============================================================

import math
import pandas as pd
from config import K_NEIGHBORS, W_GPA, W_CAREER_MATCH, W_CREDIT_LOAD, W_PROGRESS, GRADE_MAPPING


class KNNEngine:

    def __init__(self, student_profiles_path: str):
        self.df = self._load(student_profiles_path)

    # ----------------------------------------------------------
    # Load & parse student profiles
    # ----------------------------------------------------------
    def _load(self, path: str) -> pd.DataFrame:
        encodings = ['utf-8-sig', 'utf-8', 'cp1258', 'latin1']
        for enc in encodings:
            try:
                return pd.read_csv(path, encoding=enc)
            except Exception:
                pass
        raise ValueError(f"Không đọc được file: {path}")

    # ----------------------------------------------------------
    # Vector hóa 1 sinh viên → [gpa_norm, career_match, credit_load, progress]
    # ----------------------------------------------------------
    def _vectorize(self, record: dict, career_goal: str) -> list:
        """
        Mỗi sinh viên được biểu diễn bằng vector 4 chiều, chuẩn hóa về [0, 1]:
          - gpa_norm       : GPA / 4.0
          - career_match   : 1 nếu cùng career_goal, 0.5 nếu cùng career_track, 0 nếu khác
          - credit_load    : completed_credits / max_credits_per_semester (capped at 1)
          - progress       : completed_credits / 150 (tổng tín chỉ toàn khóa)
        """
        gpa       = float(record.get('gpa', 2.5))
        c_goal    = str(record.get('career_goal', ''))
        c_track   = str(record.get('career_track', ''))
        completed = float(record.get('completed_credits', 0))
        max_cred  = float(record.get('max_credits_per_semester', 18))

        # Career match
        if c_goal == career_goal:
            career_match = 1.0
        elif c_track == record.get('_target_track', ''):
            career_match = 0.5
        else:
            career_match = 0.0

        return [
            gpa / 4.0,                                    # gpa_norm
            career_match,                                  # career_match
            min(completed / max(max_cred * 8, 1), 1.0),  # credit_load (8 kỳ)
            min(completed / 150.0, 1.0),                  # progress
        ]

    def _weighted_distance(self, v1: list, v2: list) -> float:
        """Euclidean distance có trọng số."""
        weights = [W_GPA, W_CAREER_MATCH, W_CREDIT_LOAD, W_PROGRESS]
        return math.sqrt(sum(w * (a - b) ** 2 for w, a, b in zip(weights, v1, v2)))

    # ----------------------------------------------------------
    # Tìm K sinh viên tương tự nhất
    # ----------------------------------------------------------
    def find_neighbors(
        self,
        student_context : dict,
        k               : int = K_NEIGHBORS,
    ) -> list:
        """
        Trả về K sinh viên trong profiles gần nhất với sinh viên hiện tại.
        Loại bỏ chính sinh viên đó nếu có trong dataset.
        """
        career_goal  = student_context['career_goal']
        career_track = student_context['career_track']
        student_id   = student_context['student_id']

        # Vector của sinh viên hiện tại
        target_vec = self._vectorize({
            'gpa'                    : student_context['gpa'],
            'career_goal'            : career_goal,
            'career_track'           : career_track,
            'completed_credits'      : student_context['completed_credits'],
            'max_credits_per_semester': student_context['credit_limit'],
            '_target_track'          : career_track,
        }, career_goal)

        neighbors = []
        for _, row in self.df.iterrows():
            if str(row.get('student_id', '')) == str(student_id):
                continue   # bỏ qua chính sinh viên đó

            row_dict = row.to_dict()
            row_dict['_target_track'] = career_track

            vec  = self._vectorize(row_dict, career_goal)
            dist = self._weighted_distance(target_vec, vec)

            neighbors.append({
                'student_id'          : str(row.get('student_id', '')),
                'gpa'                 : float(row.get('gpa', 2.5)),
                'career_goal'         : str(row.get('career_goal', '')),
                'career_track'        : str(row.get('career_track', '')),
                'study_hours_per_week': int(row.get('study_hours_per_week', 8)),
                'risk_level'          : str(row.get('risk_level', 'MEDIUM')),
                'weak_skills'         : str(row.get('weak_skills', '')),
                'completed_credits'   : int(row.get('completed_credits', 0)),
                'distance'            : round(dist, 4),
            })

        neighbors.sort(key=lambda x: x['distance'])
        return neighbors[:k]

    # ----------------------------------------------------------
    # Tính giờ tự học từ K peers
    # ----------------------------------------------------------
    def recommend_study_hours(self, neighbors: list, credit_load: int, risk_level: str) -> dict:
        """
        Tính giờ tự học theo 2 nguồn:
          1. Trung bình có trọng số từ K peers (gần hơn → trọng số cao hơn)
          2. Công thức: credits × 1.5h/tuần, điều chỉnh theo risk_level

        Kết hợp 2 nguồn → trả về breakdown chi tiết.
        """
        from config import STUDY_HOURS_BASE

        # Nguồn 1: peer average (inverse distance weighting)
        if neighbors:
            total_weight = sum(1 / (n['distance'] + 1e-6) for n in neighbors)
            peer_hours   = sum(
                n['study_hours_per_week'] / (n['distance'] + 1e-6)
                for n in neighbors
            ) / total_weight
        else:
            peer_hours = STUDY_HOURS_BASE.get(risk_level, 9)

        # Nguồn 2: công thức credits
        formula_hours = credit_load * 1.5

        # Kết hợp: 60% peer + 40% formula
        total = round(0.6 * peer_hours + 0.4 * formula_hours)

        # Breakdown gợi ý
        return {
            'total_per_week' : total,
            'breakdown': {
                'ly_thuyet'  : round(total * 0.35),
                'thuc_hanh'  : round(total * 0.45),
                'project'    : round(total * 0.20),
            },
            'peer_average'   : round(peer_hours, 1),
            'formula_hours'  : round(formula_hours, 1),
        }

    # ----------------------------------------------------------
    # Gợi ý kỹ năng bổ sung từ K peers + missing_skills Module 2
    # ----------------------------------------------------------
    def recommend_skills(
        self,
        neighbors      : list,
        missing_skills : list,
        career_goal    : str,
    ) -> list:
        """
        Kết hợp 2 nguồn:
          1. missing_skills từ Module 2 (career-oriented)
          2. weak_skills phổ biến nhất trong K peers (peer-based)

        Trả về list kỹ năng có độ ưu tiên (cao/trung bình/thấp).
        """
        from collections import Counter

        # Đếm weak_skills từ peers
        peer_skill_counts = Counter()
        for n in neighbors:
            raw = n.get('weak_skills', '')
            if raw and raw.lower() not in ('nan', '', 'none'):
                for s in raw.split(';'):
                    s = s.strip()
                    if s:
                        peer_skill_counts[s] += 1

        # Xây dựng danh sách kỹ năng với độ ưu tiên
        skill_list = []

        # Module 2 missing_skills → ưu tiên cao (định hướng career)
        for skill in missing_skills:
            skill_list.append({
                'skill'   : skill,
                'source'  : 'career_oriented',
                'priority': 'cao',
            })

        # Peer weak_skills → ưu tiên theo tần suất
        for skill, count in peer_skill_counts.most_common(5):
            # Không trùng với missing_skills đã có
            if not any(s['skill'] == skill for s in skill_list):
                priority = 'cao' if count >= 3 else 'trung bình' if count >= 2 else 'thấp'
                skill_list.append({
                    'skill'   : skill,
                    'source'  : 'peer_pattern',
                    'priority': priority,
                })

        return skill_list