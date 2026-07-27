from pathlib import Path
import pandas as pd

root = Path(r'C:\Users\ChamithSe\OneDrive - MAS Holdings (Pvt) Ltd\THRED DB\OneDrive_2026-07-27 (1)\THREAD DB FOR FORECAST')
files = sorted([p for p in root.rglob('*.xlsx') if p.is_file()])
out = Path(r'C:\Users\ChamithSe\OneDrive - MAS Holdings (Pvt) Ltd\THRED DB\OneDrive_2026-07-27 (1)\sample_workbook_inspect.txt')
with out.open('w', encoding='utf-8') as fh:
    fh.write('files=' + str(len(files)) + '\n')
    for p in files[:8]:
        fh.write('FILE=' + str(p) + '\n')
        try:
            xl = pd.ExcelFile(p)
            fh.write('sheets=' + str(xl.sheet_names) + '\n')
            for sheet in xl.sheet_names[:5]:
                try:
                    df = pd.read_excel(p, sheet_name=sheet, header=None, dtype=str)
                    fh.write('sheet=' + sheet + ' shape=' + str(df.shape) + '\n')
                    fh.write(df.head(10).to_string(index=False, header=False) + '\n')
                    fh.write('---\n')
                except Exception as e:
                    fh.write('sheet=' + sheet + ' ERR=' + repr(e) + '\n')
        except Exception as e:
            fh.write('ERR=' + repr(e) + '\n')
        fh.write('====\n')
print(out)
