import pandas as pd

def convert_excel_to_csv(excel_file_path, output_csv_path, sheet_name=0):
    """
    Chuyển đổi file Excel (.xlsx) sang định dạng CSV.
    """
    try:
        # Đọc file Excel. 
        # sheet_name=0 mặc định sẽ đọc sheet đầu tiên. 
        # Nếu data nằm ở sheet khác, bạn đổi thành tên sheet (ví dụ: sheet_name='courses')
        print(f"Đang đọc file: {excel_file_path}...")
        df = pd.read_excel(excel_file_path, sheet_name=sheet_name)
        
        # Xuất ra file CSV, giữ nguyên chuẩn mã hóa UTF-8 để không bị lỗi font tiếng Việt
        df.to_csv(output_csv_path, index=False, encoding='utf-8')
        print(f"Đã chuyển đổi thành công! File được lưu tại: {output_csv_path}")
        
    except FileNotFoundError:
        print(f"❌ Lỗi: Không tìm thấy file '{excel_file_path}'. Bạn kiểm tra lại đường dẫn nhé.")
    except Exception as e:
        print(f"❌ Có lỗi xảy ra trong quá trình chuyển đổi: {e}")

# --- THỰC THI ---
if __name__ == "__main__":
    # Tên file Excel đầu vào của bạn
    INPUT_EXCEL = r"C:\Users\ADMIN\OneDrive\Documents\Cơ sở AI\courses_uet_robotics_ctdt_official.xlsx"
    
    # Tên file CSV đầu ra bạn muốn tạo
    OUTPUT_CSV = r"C:\Users\ADMIN\OneDrive\Documents\Cơ sở AI\courses_uet_robotics_ctdt_official.csv"
    
    convert_excel_to_csv(INPUT_EXCEL, OUTPUT_CSV)