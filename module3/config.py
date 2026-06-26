# ============================================================
# MODULE 3 — CONFIG
# ============================================================

# --- k-NN ---
K_NEIGHBORS = 5          # Số sinh viên tương tự cần tìm

# --- Trọng số vector hóa sinh viên (phải tổng = 1.0) ---
W_GPA             = 0.35   # Học lực quan trọng nhất
W_CAREER_MATCH    = 0.30   # Mức độ khớp career goal
W_CREDIT_LOAD     = 0.20   # Tải học kỳ (credits/max)
W_PROGRESS        = 0.15   # Tiến độ hoàn thành chương trình

# --- Trọng số re-ranking plan ---
W_PLAN_CAREER     = 0.50   # Career match ratio từ Module 2
W_PLAN_PEER_SCORE = 0.20   # Điểm peer similarity
W_PLAN_LOAD       = 0.20   # Tải tín chỉ hợp lý (không quá nặng/nhẹ)
W_PLAN_FOUNDATION = 0.10   # Ưu tiên môn nền tảng/ngành so với đại cương
W_PLAN_BALANCE    = 0.00   # Độ cân bằng tín chỉ giữa 2 kỳ

# --- Mapping risk → giờ tự học base ---
STUDY_HOURS_BASE = {
    'LOW'   : 6,
    'MEDIUM': 9,
    'HIGH'  : 13,
}

# --- Mapping điểm chữ ---
GRADE_MAPPING = {
    'A+': 4.0, 'A': 4.0,
    'B+': 3.5, 'B': 3.0,
    'C+': 2.5, 'C': 2.0,
    'D+': 1.5, 'D': 1.0,
    'F' : 0.0,
}
