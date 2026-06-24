import pandas as pd
import json
from collections import defaultdict

class AcademicRuleEngine:
    def __init__(self, courses_df):
        self.courses_df = courses_df
        self.courses_df['course_code'] = self.courses_df['course_code'].astype(str).str.strip()
        self.graph, self.prerequisites = self._build_prerequisite_graph()
        self.course_credits = dict(zip(self.courses_df['course_code'], pd.to_numeric(self.courses_df['credits'], errors='coerce').fillna(3)))
        self.TOTAL_CREDITS_REQUIRED = 150

    def _build_prerequisite_graph(self):
        graph = defaultdict(list)
        prerequisites = {}

        for _, row in self.courses_df.iterrows():
            course = str(row["course_code"]).strip()
            if course.lower() == 'nan' or not course: 
                continue

            prereq = row["prerequisite_code"]
            if pd.isna(prereq) or str(prereq).strip() == '':
                prerequisites[course] = []
                continue

            prereq_list = [x.strip() for x in str(prereq).replace(",", ";").split(";") if x.strip()]
            prerequisites[course] = prereq_list

            for p in prereq_list:
                graph[p].append(course)

        return graph, prerequisites

    def _get_career_track(self, career_goal):
        smart_robot = [
            "Computer Vision Engineer", "AI Robotics Engineer", 
            "Navigation Algorithm Engineer", "Machine Learning Engineer (Robotics)",
            "Cloud Robotics Developer", "Autonomous Mobile Robot (AMR) Engineer"
        ]
        if career_goal in smart_robot:
            return "Robot thông minh"
        return "Tự động hóa công nghiệp"

    def _get_credit_limit(self, gpa):
        if gpa < 2.0: return 14, 12
        elif gpa < 3.2: return 18, 8
        else: return 22, 6

    def analyze_student(self, student):
        completed = [c.strip() for c in student["completed_courses"]]
        year = student["year"]
        gpa = student["gpa"]
        
        completed_credits = sum(self.course_credits.get(c, 3) for c in completed)
        remaining_credits = max(0, self.TOTAL_CREDITS_REQUIRED - completed_credits)
        
        track = self._get_career_track(student["career_goal"])
        max_credits, study_hours = self._get_credit_limit(gpa)

        eligible = []
        blocked = []

        for course, required_prereqs in self.prerequisites.items():
            if pd.isna(course) or str(course).lower() == 'nan' or not str(course).strip():
                continue

            if course in completed:
                continue

            has_prereq = all(p in completed for p in required_prereqs)
            if not has_prereq:
                continue 

            is_blocked = False
            
            if course == "RBE4004" and year < 3:
                blocked.append(course)
                is_blocked = True
            elif course == "RBE4003" and completed_credits < 120:
                blocked.append(course)
                is_blocked = True
            elif course == "RBE4001" and year < 4:
                blocked.append(course)
                is_blocked = True
            
            if not is_blocked:
                eligible.append(course)

        return {
            "student_id": student["student_id"],
            "eligible_courses": eligible,
            "blocked_courses": blocked,
            "completed_credits": int(completed_credits),
            "remaining_credits": int(remaining_credits),
            "career_track": track,
            "max_credits_per_semester": max_credits,
            "recommended_study_hours": study_hours
        }

if __name__ == "__main__":
    try:
        df_courses = pd.read_csv("courses_uet_robotics_ctdt_official.csv")
        df_students = pd.read_csv("student_profiles_v2.csv")
    except FileNotFoundError as e:
        print(f"Lỗi: Không tìm thấy file. {e}")
        exit()

    engine = AcademicRuleEngine(df_courses)
    all_results = []

    for index, row in df_students.iterrows():
        completed_str = str(row["completed_courses"])
        if pd.isna(completed_str) or completed_str.strip() == 'nan':
            completed_list = []
        else:
            completed_list = [c.strip() for c in completed_str.split(";") if c.strip()]

        student_data = {
            "student_id": row["student_id"],
            "year": int(row["year"]),
            "gpa": float(row["gpa"]),
            "career_goal": str(row["career_goal"]),
            "completed_courses": completed_list
        }

        analysis = engine.analyze_student(student_data)
        all_results.append(analysis)

    output_filename = "module1_results.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=4)
        
    print("Xong Module 1.")