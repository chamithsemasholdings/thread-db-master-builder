import pandas as pd
from pathlib import Path
root = Path.cwd() / 'THREAD DB FOR FORECAST'
for folder_name in ['FA26', 'HO26', 'SP27', 'SU27']:
    folder = root / folder_name
    files = sorted(folder.glob('*.xlsx'))
    for path in files[:3]:
        print('FILE', path.name)
        xl = pd.ExcelFile(path)
        print('SHEETS', xl.sheet_names)
        for sheet in xl.sheet_names[:3]:
            try:
                df = pd.read_excel(path, sheet_name=sheet)
            except Exception as e:
                print('ERROR reading', sheet, e)
                continue
            print('SHEET', sheet, 'ROWS', len(df), 'COLS', list(df.columns[:10]))
            print(df.head(2).to_string())
            print('---')
        print('====')
