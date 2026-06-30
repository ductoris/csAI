#!/usr/bin/env python3
"""Run the full csAI pipeline for all students and store outputs in student folders.

Each student gets their own subfolder under the final output directory.
Example:
  output/UET230001/module1_output.json
  output/UET230001/module2_output.json
  output/UET230001/module3_output.json
"""

import argparse
import csv
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent
MODULE1_SCRIPT = ROOT / 'module1' / 'module1_rule_engine.py'
MODULE2_SCRIPT = ROOT / 'module2' / 'main.py'
MODULE3_SCRIPT = ROOT / 'module3' / 'main.py'
DEFAULT_COURSES = ROOT / 'data' / 'courses_uet_robotics_ctdt_official.csv'
DEFAULT_STUDENTS = ROOT / 'module2' / 'data' / 'student_profiles.csv'
DEFAULT_CAREER_PATHS = ROOT / 'module2' / 'data' / 'career_paths.csv'
DEFAULT_OUTPUT_DIR = ROOT / 'output'


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
    print('\n' + '=' * 80, flush=True)
    print('RUNNING:', ' '.join(str(x) for x in command), flush=True)
    print('=' * 80, flush=True)
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
        description='Run csAI pipeline for all students and write outputs into per-student folders.'
    )
    parser.add_argument('--students-file', default=DEFAULT_STUDENTS, help='CSV with a student_id column for the batch run.')
    parser.add_argument('--courses', default=DEFAULT_COURSES, help='Courses CSV for Module 1.')
    parser.add_argument('--career-paths', default=DEFAULT_CAREER_PATHS, help='career_paths.csv for Module 2.')
    parser.add_argument('--output-dir', default=DEFAULT_OUTPUT_DIR, help='Base output directory for all student subfolders.')
    parser.add_argument('--k', type=int, default=5, help='Number of neighbors for Module 3 k-NN.')
    parser.add_argument('--top', type=int, default=15, help='Number of top candidate courses to show for Module 1.')
    parser.add_argument('--force', action='store_true', help='Re-run even if output files already exist.')
    args = parser.parse_args()

    students_path = Path(args.students_file)
    courses_path = Path(args.courses)
    career_paths_path = Path(args.career_paths)
    output_dir = Path(args.output_dir)

    if not students_path.exists():
        raise FileNotFoundError(f'Students file not found: {students_path}')
    if not courses_path.exists():
        raise FileNotFoundError(f'Courses file not found: {courses_path}')
    if not career_paths_path.exists():
        raise FileNotFoundError(f'Career paths file not found: {career_paths_path}')

    student_ids = load_student_ids_from_csv(students_path)
    if not student_ids:
        raise ValueError(f'No student IDs found in {students_path}')

    output_dir.mkdir(parents=True, exist_ok=True)

    for student_id in student_ids:
        student_id = student_id.strip()
        if not student_id:
            continue

        student_dir = output_dir / student_id
        student_dir.mkdir(parents=True, exist_ok=True)

        module1_output = student_dir / 'module1_output.json'
        module2_output = student_dir / 'module2_output.json'
        module3_output = student_dir / 'module3_output.json'

        print('\n' + '#' * 80)
        print(f'Running pipeline for student: {student_id}')
        print(f'Output folder: {student_dir}')
        print('#' * 80)

        if args.force or not module1_output.exists():
            run_module1(
                student_id=student_id,
                courses_path=courses_path,
                students_path=students_path,
                output_path=module1_output,
                top=args.top,
            )
        else:
            print(f'Skipping Module 1 for {student_id}: {module1_output} already exists')

        if args.force or not module2_output.exists():
            run_module2(
                module1_output=module1_output,
                module2_output=module2_output,
                career_paths=career_paths_path,
            )
        else:
            print(f'Skipping Module 2 for {student_id}: {module2_output} already exists')

        if args.force or not module3_output.exists():
            run_module3(
                module2_output=module2_output,
                student_profiles=students_path,
                courses_path=courses_path,
                module3_output=module3_output,
                k=args.k,
            )
        else:
            print(f'Skipping Module 3 for {student_id}: {module3_output} already exists')

        print(f'Pipeline completed for {student_id}')
        print(f'  Module 1 JSON: {module1_output}')
        print(f'  Module 2 JSON: {module2_output}')
        print(f'  Module 3 JSON: {module3_output}')

    print(f'\nBatch run completed: {len(student_ids)} students processed.')


if __name__ == '__main__':
    main()
