from pathlib import Path
import pandas as pd

p = Path(r'C:\Users\ChamithSe\OneDrive - MAS Holdings (Pvt) Ltd\THRED DB\OneDrive_2026-07-27 (1)\THREAD DB FOR FORECAST\FA26\FA26 THREAD DB.xlsx')
out = Path(r'C:\Users\ChamithSe\OneDrive - MAS Holdings (Pvt) Ltd\THRED DB\OneDrive_2026-07-27 (1)\sheet_check_result.txt')
with out.open('w', encoding='utf-8') as fh:
    fh.write('exists=' + str(p.exists()) + '\n')
    if p.exists():
        try:
            xl = pd.ExcelFile(p)
            fh.write('sheets=' + str(xl.sheet_names) + '\n')
            if 'Thread_DB' in xl.sheet_names:
                df = pd.read_excel(p, sheet_name='Thread_DB', header=None, dtype=str)
                fh.write('shape=' + str(df.shape) + '\n')
                fh.write(df.head(10).to_string(index=False, header=False) + '\n')
            else:
                fh.write('thread_db_missing\n')
        except Exception as exc:
            fh.write('error=' + repr(exc) + '\n')
