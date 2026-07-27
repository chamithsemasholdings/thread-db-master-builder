from pathlib import Path
import pandas as pd
root = Path(r'C:\Users\ChamithSe\OneDrive - MAS Holdings (Pvt) Ltd\THRED DB\OneDrive_2026-07-27 (1)\THREAD DB FOR FORECAST')
files = sorted([p for p in root.rglob('*.xlsx') if p.is_file()])
print('files', len(files))
p = files[0]
print('sample', p)
xl = pd.ExcelFile(p)
print('sheets', xl.sheet_names[:10])
for s in xl.sheet_names[:3]:
    print('--- sheet', s)
    df = pd.read_excel(p, sheet_name=s, header=None, dtype=str)
    print(df.head(15).to_string())
