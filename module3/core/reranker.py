# ============================================================
# MODULE 3 — PLAN RE-RANKER
# Re-rank Top-K plans từ Module 2 dựa trên peer similarity
# ============================================================

from config import (
    W_PLAN_CAREER,
    W_PLAN_PEER_SCORE,
    W_PLAN_LOAD,
    W_PLAN_FOUNDATION,
    W_PLAN_BALANCE,
)


class PlanReranker:

    def rerank(
        self,
        plans           : list,
        neighbors       : list,
        credit_limit    : int,
        student_context : dict,
    ) -> list:
        """
        Tính score mới cho mỗi plan dựa trên 3 tiêu chí:
          1. career_match_ratio  từ Module 2        (W_PLAN_CAREER)
          2. peer_score          từ K-NN neighbors  (W_PLAN_PEER_SCORE)
          3. load_score          tải tín chỉ hợp lý (W_PLAN_LOAD)
          4. foundation_score    tỷ lệ môn nền tảng/ngành (W_PLAN_FOUNDATION)
          5. balance_score       độ cân bằng tín chỉ giữa kỳ (W_PLAN_BALANCE)

        Sau đó sắp xếp lại theo final_score giảm dần.
        """
        gpa         = student_context['gpa']
        risk_level  = student_context['risk_level']

        scored_plans = []
        for plan in plans:
            career_score = plan.get('career_match_ratio', 0.0)
            peer_score   = self._calc_peer_score(plan, neighbors)
            load_score   = self._calc_load_score(
                plan['total_credits_2sem'], credit_limit, gpa, risk_level
            )
            foundation_score = plan.get('plan_metrics', {}).get('foundation_score', 0.5)
            balance_score    = plan.get('plan_metrics', {}).get('balance_score', 0.5)

            final_score = (
                W_PLAN_CAREER     * career_score     +
                W_PLAN_PEER_SCORE * peer_score       +
                W_PLAN_LOAD       * load_score       +
                W_PLAN_FOUNDATION * foundation_score +
                W_PLAN_BALANCE    * balance_score
            )

            scored_plans.append({
                **plan,
                'score_breakdown': {
                    'career_score': round(career_score, 3),
                    'peer_score'  : round(peer_score,   3),
                    'load_score'  : round(load_score,   3),
                    'foundation_score': round(foundation_score, 3),
                    'balance_score'   : round(balance_score, 3),
                },
                'final_score': round(final_score, 4),
            })

        # Sắp xếp lại theo final_score
        scored_plans.sort(key=lambda x: x['final_score'], reverse=True)

        # Cập nhật rank
        for i, p in enumerate(scored_plans):
            p['rank'] = i + 1

        return scored_plans

    # ----------------------------------------------------------
    # peer_score: plan có nhiều môn mà peers cùng career cũng học → score cao
    # ----------------------------------------------------------
    def _calc_peer_score(self, plan: dict, neighbors: list) -> float:
        """
        Đếm xem có bao nhiêu peer cùng career_track → normalize về [0, 1].
        Peers gần hơn (distance nhỏ) được đếm nhiều hơn.
        """
        if not neighbors:
            return 0.5   # không có peer → neutral

        same_track_peers = [
            n for n in neighbors
            if n.get('career_track') == neighbors[0].get('career_track')
        ]

        if not neighbors:
            return 0.5

        ratio = len(same_track_peers) / len(neighbors)

        # Boost nếu peers gần (distance nhỏ) cùng track
        avg_distance = sum(n['distance'] for n in same_track_peers) / max(len(same_track_peers), 1)
        closeness    = 1 / (1 + avg_distance)   # [0, 1], distance càng nhỏ càng gần 1

        return round(ratio * 0.6 + closeness * 0.4, 3)

    # ----------------------------------------------------------
    # load_score: tín chỉ phù hợp → score cao
    # ----------------------------------------------------------
    def _calc_load_score(
        self,
        total_credits_2sem : int,
        credit_limit       : int,
        gpa                : float,
        risk_level         : str,
    ) -> float:
        """
        Tín chỉ trung bình/kỳ nằm trong vùng tối ưu → score cao.
        Vùng tối ưu dựa trên GPA và risk_level:
          - GPA >= 3.2 (LOW)   : 16–credit_limit
          - GPA 2.5–3.2 (MED) : 12–16
          - GPA < 2.5 (HIGH)  : 10–14
        """
        avg_per_sem = total_credits_2sem / 2

        OPTIMAL = {
            'LOW'   : (16, credit_limit),
            'MEDIUM': (12, 16),
            'HIGH'  : (10, 14),
        }
        lo, hi = OPTIMAL.get(risk_level, (12, 16))

        if lo <= avg_per_sem <= hi:
            return 1.0
        elif avg_per_sem < lo:
            return max(0.0, 1.0 - (lo - avg_per_sem) / lo)
        else:
            return max(0.0, 1.0 - (avg_per_sem - hi) / hi)
