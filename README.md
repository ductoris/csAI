# Bài tập cuối kỳ môn Cơ sở Trí tuệ nhân tạo

## gudluck

# Module 1 - Rule-based Knowledge Engine

Module 1 đọc hồ sơ sinh viên và chương trình đào tạo, sau đó xuất ra file JSON làm đầu vào cho Module 2.

## 1. Cài đặt

```bash
pip install pandas
```
Cấu trúc file cần có: 
```bash
module1_rule_engine.py

courses_uet_robotics_ctdt_official.csv

student_profiles.csv
```
## Chạy module 1:
### Chạy 1 sinh viên đầu tiên:
```bash
python module1_rule_engine.py
```
### Chạy với một sinh viên cụ thể:
```bash
python module1_rule_engine.py --student UET230001
```
### Nếu muốn chạy toàn bộ:
```bash
python module1_rule_engine.py --all
```
### Khi đó sẽ tạo ra 1 folder

# Để chạy toàn bộ ra tổng output cuối cùng với từng sinh viên:
```bash
  python3 run_pipeline.py --student UET230001
```
