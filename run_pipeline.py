#!/usr/bin/env python3
"""Run Module 1 -> Module 2 -> Module 3 pipeline for one or more students.

Example:
  python run_pipeline.py --student UET230001
  python run_pipeline.py --students-file module2/data/student_profiles.csv
"""

import argparse
import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODULE1_SCRIPT = ROOT / 'module1' / 'module1_rule_engine.py'
MODULE2_SCRIPT = ROOT / 'module2' / 'main.py'
MODULE3_SCRIPT = ROOT / 'module3' / 'main.py'
DEFAULT_COURSES = ROOT / 'courses_uet_robotics_ctdt_official.csv'
DEFAULT_STUDENTS = ROOT / 'module2' / 'data' / 'student_profiles.csv'
DEFAULT_M1_OUTPUT_DIR = ROOT / 'module2'
DEFAULT_M2_OUTPUT_DIR = ROOT / 'module2'
DEFAULT_M3_OUTPUT_DIR = ROOT / 'module3'


def load_student_ids_from_csv(students_path):
    student_ids = []
    with open(students_path, encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if 'student_id' not in reader.fieldnames:
            raise ValueError(f"students file must contain 'student_id' column: {students_path}")
        for row in reader:
            student_id = str(row.get('student_id', '')).strip()
            if student_id:
                student_ids.append(student_id)
    return student_ids


def run_command(command):
    print('\n' + '=' * 80)
    print('RUNNING:', ' '.join(str(x) for x in command))
    print('=' * 80)
    subprocess.run(command, cwd=ROOT, check=True)


def run_module1(student_id, courses_path, students_path, output_path, top=15):
    command = [
        sys.executable,
        str(MODULE1_SCRIPT),
        '--student', student_id,
        '--courses', str(courses_path),
        '--students', str(students_path),
        '--output', str(output_path),
        '--top', str(top),
    ]
    run_command(command)


def run_module2(module1_output, module2_output, career_paths=None):
    command = [
        sys.executable,
        str(MODULE2_SCRIPT),
        '--module1_output', str(module1_output),
        '--output', str(module2_output),
    ]
    if career_paths:
        command.extend(['--career_paths', str(career_paths)])
    run_command(command)


def run_module3(module2_output, student_profiles, courses_path, module3_output, k=5):
    command = [
        sys.executable,
        str(MODULE3_SCRIPT),
        '--module2', str(module2_output),
        '--profiles', str(student_profiles),
        '--courses', str(courses_path),
        '--output', str(module3_output),
        '--k', str(k),
    ]
    run_command(command)


def main():
    parser = argparse.ArgumentParser(
        description='Run csAI module pipeline: Module 1 -> Module 2 -> Module 3'
    )
    parser.add_argument('--student', action='append', help='Student ID to run the pipeline for. Can be repeated.')
    parser.add_argument('--students-file', help='CSV file with a student_id column to run for multiple students.')
    parser.add_argument('--courses', default=DEFAULT_COURSES, help='Courses CSV for Module 1.')
    parser.add_argument('--students', default=DEFAULT_STUDENTS, help='Students CSV for Module 1.')
    parser.add_argument('--career-paths', default=ROOT / 'module2' / 'data' / 'career_paths.csv', help='career_paths.csv for Module 2.')
    parser.add_argument('--k', type=int, default=5, help='Number of neighbors for Module 3 k-NN.')
    parser.add_argument('--top', type=int, default=15, help='Number of top candidate courses to show for Module 1.')
    args = parser.parse_args()

    student_ids = args.student or []
    if args.students_file:
        student_ids.extend(load_student_ids_from_csv(args.students_file))

    if not student_ids:
        parser.error('Please provide at least one --student or --students-file')

    courses_path = Path(args.courses)
    students_path = Path(args.students)
    career_paths_path = Path(args.career_paths)

    if not courses_path.exists():
        raise FileNotFoundError(f'Courses file not found: {courses_path}')
    if not students_path.exists():
        raise FileNotFoundError(f'Students file not found: {students_path}')
    if not career_paths_path.exists():
        raise FileNotFoundError(f'Career paths file not found: {career_paths_path}')

    for student_id in student_ids:
        student_id = student_id.strip()
        if not student_id:
            continue

        module1_output = DEFAULT_M1_OUTPUT_DIR / f'module1_output_{student_id}.json'
        module2_output = DEFAULT_M2_OUTPUT_DIR / f'module2_output_{student_id}.json'
        module3_output = DEFAULT_M3_OUTPUT_DIR / f'module3_output_{student_id}.json'

        print('\n' + '#' * 80)
        print(f'Running pipeline for student: {student_id}')
        print('#' * 80)

        run_module1(
            student_id=student_id,
            courses_path=courses_path,
            students_path=students_path,
            output_path=module1_output,
            top=args.top,
        )

        run_module2(
            module1_output=module1_output,
            module2_output=module2_output,
            career_paths=career_paths_path,
        )

        run_module3(
            module2_output=module2_output,
            student_profiles=students_path,
            courses_path=courses_path,
            module3_output=module3_output,
            k=args.k,
        )

        print(f'Pipeline completed for {student_id}')
        print(f'  Module 1 JSON: {module1_output}')
        print(f'  Module 2 JSON: {module2_output}')
        print(f'  Module 3 JSON: {module3_output}')

    print('\nAll requested students processed.')


if __name__ == '__main__':
    main()
