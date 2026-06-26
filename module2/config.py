# ============================================================
# MODULE 2 — CONFIG
# ============================================================

# --- Trọng số hàm g(n) ---
W_CREDITS     = 1.0   # Chi phí cơ bản mỗi tín chỉ
W_HARD_COURSE = 8.0   # Phạt mỗi môn chuyên ngành nặng dư thừa
W_CAREER      = 3.0   # Trọng số heuristic h(n) mỗi môn priority còn thiếu
                      # W_CAREER = W_CREDITS * min_credits (3) → admissible
W_GENERAL_COURSE_PENALTY = 0.25  # Phạt nhẹ nếu plan dồn nhiều môn đại cương/bổ trợ
W_FOUNDATION_COURSE_BONUS = 0.15 # Ưu tiên nhẹ môn nền tảng/ngành
W_EARLY_FOUNDATION_BONUS = 0.05 # Phá hòa: ưu tiên môn nền tảng ở kỳ gần nhất
W_EARLY_GENERAL_PENALTY = 0.05  # Phá hòa: hạn chế dồn đại cương ở kỳ gần nhất

# --- Giới hạn học kỳ ---
MAX_SEMESTERS = 2     # Lập kế hoạch tối đa 2 kỳ tiếp theo
BEAM_WIDTH    = 3     # Số plan tốt nhất cần trả về

# --- Mapping điểm chữ → điểm số (thang 4.0) ---
GRADE_MAPPING = {
    'A+': 4.0,
    'A' : 4.0,
    'B+': 3.5,
    'B' : 3.0,
    'C+': 2.5,
    'C' : 2.0,
    'D+': 1.5,
    'D' : 1.0,
    'F' : 0.0,
}

# --- Ngưỡng GPA ---
GPA_LOW    = 2.5   # Dưới ngưỡng này bị phạt nặng nếu đăng ký quá tải
GPA_MEDIUM = 3.0

# --- Tín chỉ tối đa/tối thiểu mỗi kỳ ---
MAX_CREDITS_DEFAULT = 21
MIN_CREDITS_DEFAULT = 15
