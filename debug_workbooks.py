from pathlib import Path
import pandas as pd
import sys

root = Path(r'C:\Users\ChamithSe\OneDrive - MAS Holdings (Pvt) Ltd\THRED DB\OneDrive_2026-07-27 (1)\THREAD DB FOR FORECAST')
files = sorted([p for p in root.rglob('*.xlsx') if p.is_file()])
out = Path(r'C:\temp\workbook_debug.txt')
with out.open('w', encoding='utf-8') as fh:
    fh.write('python=' + sys.executable + '\n')
    fh.write('files=' + str(len(files)) + '\n')
    if files:
        p = files[0]
        fh.write('file=' + str(p) + '\n')
        try:
            xl = pd.ExcelFile(p)
            fh.write('sheets=' + str(xl.sheet_names[:10]) + '\n')
            for s in xl.sheet_names[:3]:
                fh.write('---- ' + s + '\n')
                df = pd.read_excel(p, sheet_name=s, header=None, dtype=str)
                fh.write(df.head(8).to_string(index=False) + '\n')
                fh.write('rows=' + str(len(df)) + ' cols=' + str(len(df.columns)) + '\n')
        except Exception as exc:
            fh.write('ERROR=' + repr(exc) + '\n')
