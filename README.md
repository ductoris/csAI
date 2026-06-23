# Bài tập cuối kỳ môn Cơ sở Trí tuệ nhân tạo

## gudluck

## Module 1: Curriculum Knowledge Base

Module 1 xây dựng cơ sở tri thức từ chương trình đào tạo ngành Kỹ thuật Robot dưới dạng JSON và đồ thị học phần (Course Graph).

### Chức năng

* Đọc dữ liệu chương trình đào tạo từ `ctdt_ky_thuat_robot.json`
* Quản lý thông tin học phần và điều kiện tiên quyết
* Xây dựng đồ thị học phần bằng NetworkX
* Xác định các môn học đủ điều kiện đăng ký (Eligible Courses)
* Xác định các môn học còn thiếu điều kiện tiên quyết (Blocked Courses)

### Đầu vào

* Chương trình đào tạo ngành Kỹ thuật Robot (JSON)

### Đầu ra

* Course Knowledge Base
* Curriculum Graph
* Eligible Courses
* Blocked Courses

### Chạy file: test_module1.py
Tìm và sửa đoạn sau thành những môn đã học
```bash
passed_courses = [
    "MAT1041",
    "INT1008",
    "EPN1095"
]
```
