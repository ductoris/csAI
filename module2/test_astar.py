# module2_astar/test_astar.py

import unittest
from core.utility import AcademicUtility
from core.astar import AcademicAStar

class TestGradeAwareAStar(unittest.TestCase):
    
    def setUp(self):
        self.course_db = {
            'MAT1101': {'credits': 4}, 'MAT1102': {'credits': 4},
            'INT1008': {'credits': 3}, 'ROB3001': {'credits': 3},
            'ROB3002': {'credits': 3}, 'INT3405': {'credits': 3}
        }
        self.priority_courses = ['ROB3001', 'ROB3002', 'INT3405']
        self.planner = AcademicAStar(self.course_db, self.priority_courses)

    def test_calculate_gpa_from_grades(self):
        """CA KIỂM THỬ 1: Đảm bảo bộ lọc quy đổi điểm chữ sang hệ 4 tính toán GPA chính xác."""
        sample_grades = {"MAT1101": "C+", "INT1008": "A"} # C+(2.5) + A(4.0) = 6.5 / 2 = 3.25
        gpa = AcademicUtility.calculate_current_gpa(sample_grades)
        self.assertEqual(gpa, 3.25)

    def test_g_cost_adaptive_with_low_gpa(self):
        """CA KIỂM THỬ 2: Kiểm tra luật phạt thích ứng. Sinh viên GPA yếu mà nhồi nhiều tín chỉ g(n) phải bị phạt nặng."""
        low_gpa_grades = {"MAT1101": "D", "INT1008": "D"} # GPA = 1.0 (Yếu)
        current_semester = ['MAT1102', 'ROB3001', 'ROB3002', 'INT3405', 'INT1008'] # 16 tín chỉ, gom 3 môn nặng
        
        cost = AcademicUtility.calculate_g_cost(current_semester, low_gpa_grades, self.course_db)
        # 16 TC * 1.0 + (3 môn nặng - 2) * 10.0 (W_HARD_COURSE) = 16 + 10 = 26.0 (Do chưa vượt quá 18 tín chỉ nên không bị cộng 50 điểm phạt gpa nặng)
        self.assertEqual(cost, 26.0)

if __name__ == '__main__':
    unittest.main()