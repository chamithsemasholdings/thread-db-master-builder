from __future__ import annotations

import re
import tempfile
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Callable, List, Union

import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="Thread DB Master Builder",
    page_icon="🧵",
    layout="wide",
    initial_sidebar_state="expanded",
)

ESSENTIAL_COLUMNS = [
    "Season",
    "Style-CW",
    "Thread-Color",
    "SAP Codes",
    "Consumption in CO",
]


def normalize_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_headers(columns: List[object]) -> dict:
    alias_map = {
        "season": "Season",
        "style cw": "Style-CW",
        "style": "Style-CW",
        "thread color": "Thread-Color",
        "threadcolour": "Thread-Color",
        "thread": "Thread-Color",
        "sap code": "SAP Codes",
        "sap codes": "SAP Codes",
        "sap": "SAP Codes",
        "consumption in co": "Consumption in CO",
        "sum of consumption in co": "Consumption in CO",
        "sum consumption in co": "Consumption in CO",
    }

    normalized: dict = {}
    for column in columns:
        raw_name = str(column).strip()
        if not raw_name:
            normalized[column] = ""
            continue
        key = normalize_text(raw_name)
        normalized[column] = alias_map.get(key, raw_name)
    return normalized


def clean_cell(value: object) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (ValueError, TypeError):
        pass
    text = str(value).strip()
    if not text:
        return ""
    upper = text.upper()
    if upper in {"NAN", "(BLANK)", "-", "NULL", "#N/A", "#REF!", "#VALUE!", "#DIV/0!", "#NAME?", "#NULL!", "#NUM!"}:
        return ""
    return text


GRAND_TOTAL_TOKENS = {"grand total", "total", "subtotal"}


def read_sheet_dataframe(file_path: Union[Path, BytesIO], sheet_name: str) -> pd.DataFrame:
    try:
        raw = pd.read_excel(file_path, sheet_name=sheet_name, header=None, dtype=str)
    except Exception:
        return pd.DataFrame()

    if raw.empty:
        return pd.DataFrame()

    cleaned_rows = []
    for row in raw.itertuples(index=False, name=None):
        cleaned_rows.append([clean_cell(v) for v in row])

    if not cleaned_rows:
        return pd.DataFrame()

    def find_header_index(rows: list[list[str]]) -> int:
        for idx, row_values in enumerate(rows):
            non_empty = [value for value in row_values if value]
            if not non_empty:
                continue
            normalized = [normalize_text(value) for value in non_empty]
            if any(key in {"season", "style cw", "thread color", "sap code", "sap codes", "consumption in co", "consumption"} for key in normalized):
                return idx
            if any(any(token in key for token in GRAND_TOTAL_TOKENS) for key in normalized):
                continue
            if len(non_empty) >= 2 and any("thread" in key for key in normalized):
                return idx
            if len(non_empty) >= 3 and sum(1 for value in non_empty if len(value) > 1) >= 2:
                return idx
        return 0

    header_index = find_header_index(cleaned_rows)
    header_row = cleaned_rows[header_index]
    if not any(header_row):
        return pd.DataFrame()

    header_labels = [header if header else f"Column_{i + 1}" for i, header in enumerate(header_row)]
    data_rows = cleaned_rows[header_index + 1 :]

    if not data_rows:
        return pd.DataFrame(columns=header_labels)

    filtered_rows = []
    for row in data_rows:
        normalized_row = [normalize_text(value) for value in row]
        if any(any(token in value for token in GRAND_TOTAL_TOKENS) for value in normalized_row if value):
            continue
        if not any(row):
            continue
        filtered_rows.append(row)

    if not filtered_rows:
        return pd.DataFrame(columns=header_labels)

    col_count = len(header_labels)
    normalized_rows = []
    for row in filtered_rows:
        if len(row) > col_count:
            normalized_rows.append(row[:col_count])
        elif len(row) < col_count:
            normalized_rows.append(row + [""] * (col_count - len(row)))
        else:
            normalized_rows.append(row)

    data = pd.DataFrame(normalized_rows, columns=header_labels)
    data.columns = [str(c) for c in data.columns]
    data = data.loc[:, ~data.columns.duplicated()].copy()

    for column in data.columns:
        data[column] = data[column].apply(clean_cell)
    data = data.loc[~(data.apply(lambda row: not any(str(v).strip() for v in row), axis=1))].copy()
    return data


def _process_frame(
    df: pd.DataFrame,
    file_path: Path,
    root: Path,
    collected_frames: list[pd.DataFrame],
    metadata_log: list[dict],
) -> None:
    mapping = normalize_headers(df.columns.tolist())
    renamed_columns = []
    seen: dict[str, int] = {}
    for original_name in df.columns.tolist():
        canonical_name = mapping.get(original_name, original_name)
        if canonical_name in {"Season", "Style-CW", "Thread-Color", "SAP Codes", "Consumption in CO"}:
            canonical_name = canonical_name
        count = seen.get(canonical_name, 0)
        if count:
            renamed_columns.append(f"{canonical_name}_{count + 1}")
        else:
            renamed_columns.append(canonical_name)
        seen[canonical_name] = count + 1

    df = df.copy()
    df.columns = renamed_columns

    for essential_col in ESSENTIAL_COLUMNS:
        variants = [c for c in df.columns if c == essential_col]
        variants += [c for c in df.columns if c.startswith(f"{essential_col}_")]
        if len(variants) > 1:
            merged = df[variants[0]]
            for var in variants[1:]:
                merged = merged.where(merged.notna() & merged.ne(""), df[var])
            df[essential_col] = merged
            df = df.drop(columns=variants[1:])

    df["Source Folder"] = str(file_path.parent.relative_to(root)) if file_path.parent != root else "Root"
    df["Source File"] = file_path.name
    df["Source Sheet"] = file_path.name
    df["Source Row Count"] = len(df)
    collected_frames.append(df)
    metadata_log.append({
        "file": str(file_path),
        "sheet": "all",
        "status": "ok",
        "rows": len(df),
        "columns": df.columns.tolist(),
    })


def build_master_db(main_folder: str, progress_callback: Callable[[str, int, int], None] | None = None) -> tuple[pd.DataFrame, list[dict]]:
    root = Path(main_folder).expanduser()
    if not root.exists():
        raise FileNotFoundError(f"Folder not found: {root}")

    workbook_files = sorted([p for p in root.rglob("*.xlsx") if p.is_file()])
    collected_frames: list[pd.DataFrame] = []
    metadata_log: list[dict] = []

    if progress_callback is not None:
        progress_callback("Scanning Excel files under the selected folder tree…", 0, max(1, len(workbook_files)))

    for index, file_path in enumerate(workbook_files, start=1):
        if progress_callback is not None:
            progress_callback(f"Reading {file_path.name}", index, max(1, len(workbook_files)))

        try:
            workbook = pd.ExcelFile(file_path)
        except Exception as exc:
            metadata_log.append({
                "file": str(file_path),
                "status": "error",
                "message": str(exc),
            })
            continue

        sheet_names = [sheet for sheet in workbook.sheet_names if isinstance(sheet, str) and sheet.strip()]
        preferred_sheets = []
        if "Thread_DB" in sheet_names:
            preferred_sheets.append("Thread_DB")
        preferred_sheets.extend([sheet for sheet in sheet_names if sheet != "Thread_DB"])
        if not preferred_sheets and sheet_names:
            preferred_sheets = sheet_names
        elif not preferred_sheets:
            preferred_sheets = [workbook.sheet_names[0]] if workbook.sheet_names else []

        for sheet_name in preferred_sheets:
            try:
                df = read_sheet_dataframe(file_path, sheet_name)
            except Exception as exc:
                metadata_log.append({
                    "file": str(file_path),
                    "sheet": sheet_name,
                    "status": "error",
                    "message": str(exc),
                })
                continue

            if df.empty:
                metadata_log.append({
                    "file": str(file_path),
                    "sheet": sheet_name,
                    "status": "empty",
                    "rows": 0,
                    "columns": [],
                })
                continue

            _process_frame(df, file_path, root, collected_frames, metadata_log)

    if progress_callback is not None:
        progress_callback("Combining rows into one master table…", len(workbook_files), max(1, len(workbook_files)))

    return _combine_frames(collected_frames, metadata_log)


def build_master_db_from_files(
    uploaded_files: List[st.runtime.uploaded_file_manager.UploadedFile],
    progress_callback: Callable[[str, int, int], None] | None = None,
) -> tuple[pd.DataFrame, list[dict]]:
    collected_frames: list[pd.DataFrame] = []
    metadata_log: list[dict] = []
    temp_dir = Path(tempfile.gettempdir()) / "thread_db_uploads"
    temp_dir.mkdir(parents=True, exist_ok=True)

    if progress_callback is not None:
        progress_callback("Processing uploaded files…", 0, max(1, len(uploaded_files)))

    for index, uploaded in enumerate(uploaded_files, start=1):
        if progress_callback is not None:
            progress_callback(f"Reading {uploaded.name}", index, max(1, len(uploaded_files)))

        safe_name = re.sub(r'[^A-Za-z0-9_\-\.]+', '_', uploaded.name)
        temp_path = temp_dir / safe_name
        temp_path.write_bytes(uploaded.read())
        file_path = Path(temp_path)

        try:
            workbook = pd.ExcelFile(file_path)
        except Exception as exc:
            metadata_log.append({
                "file": uploaded.name,
                "status": "error",
                "message": str(exc),
            })
            continue

        sheet_names = [sheet for sheet in workbook.sheet_names if isinstance(sheet, str) and sheet.strip()]
        preferred_sheets = []
        if "Thread_DB" in sheet_names:
            preferred_sheets.append("Thread_DB")
        preferred_sheets.extend([sheet for sheet in sheet_names if sheet != "Thread_DB"])
        if not preferred_sheets and sheet_names:
            preferred_sheets = sheet_names
        elif not preferred_sheets:
            preferred_sheets = [workbook.sheet_names[0]] if workbook.sheet_names else []

        for sheet_name in preferred_sheets:
            try:
                df = read_sheet_dataframe(file_path, sheet_name)
            except Exception as exc:
                metadata_log.append({
                    "file": uploaded.name,
                    "sheet": sheet_name,
                    "status": "error",
                    "message": str(exc),
                })
                continue

            if df.empty:
                metadata_log.append({
                    "file": uploaded.name,
                    "sheet": sheet_name,
                    "status": "empty",
                    "rows": 0,
                    "columns": [],
                })
                continue

            _process_frame(df, file_path, file_path.parent, collected_frames, metadata_log)

    if progress_callback is not None:
        progress_callback("Combining rows into one master table…", len(uploaded_files), max(1, len(uploaded_files)))

    return _combine_frames(collected_frames, metadata_log)


def _combine_frames(collected_frames: list[pd.DataFrame], metadata_log: list[dict]) -> tuple[pd.DataFrame, list[dict]]:
    if not collected_frames:
        return pd.DataFrame(columns=ESSENTIAL_COLUMNS), metadata_log

    combined_rows: list[pd.DataFrame] = []
    for frame in collected_frames:
        frame_copy = frame.copy()
        for col in ESSENTIAL_COLUMNS:
            if col not in frame_copy.columns:
                frame_copy[col] = ""
        if "Consumption in CO" in frame_copy.columns:
            frame_copy["Consumption in CO"] = frame_copy["Consumption in CO"].fillna("")
            for col in [c for c in frame_copy.columns if c.startswith("Consumption in CO") and c != "Consumption in CO"]:
                frame_copy["Consumption in CO"] = frame_copy["Consumption in CO"].fillna(frame_copy[col])
                frame_copy.drop(columns=[col], inplace=True)
        keep_cols = [c for c in ESSENTIAL_COLUMNS if c in frame_copy.columns]
        essential_df = frame_copy[keep_cols]
        essential_df = essential_df.loc[~(essential_df.apply(lambda row: not any(str(v).strip() for v in row), axis=1))].copy()
        combined_rows.append(essential_df)

    master_db = pd.concat(combined_rows, ignore_index=True)
    master_db = master_db.drop_duplicates(subset=ESSENTIAL_COLUMNS, keep="first").reset_index(drop=True)
    return master_db, metadata_log


def export_excel_bytes(df: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Master_DB")
    return buffer.getvalue()


st.title("🧵 Thread DB Master Builder")
st.markdown(
    """
    Build one **Master DB** from Thread DB Excel files. Use either:
    - **Local folder mode**: point the app at a folder on this machine
    - **Upload mode**: upload Excel files directly — works on **Streamlit Cloud**
    """
)

with st.sidebar:
    st.header("⚙️ Settings")
    today_str = datetime.now().strftime("%Y-%m-%d")
    output_name = st.text_input(
        "Output Excel file name",
        value=f"master_thread_db_{today_str}.xlsx",
        help="File will be saved to the output folder below.",
    )
    output_folder = st.text_input(
        "Save to folder",
        value=str(Path.cwd()),
        help="Full path where the master Excel file will be written.",
    )
    st.divider()
    st.subheader("Input mode")
    input_mode = st.radio(
        "Source",
        options=["Local folder", "Upload files"],
        help="Choose Local folder for desktop use, or Upload files for Streamlit Cloud.",
    )
    main_folder = ""
    uploaded_files = []
    if input_mode == "Local folder":
        default_root = str(Path.cwd())
        main_folder = st.text_input(
            "Main folder path",
            value=default_root,
            help="Path to the folder that contains FA26, HO26, SP27, SU27, etc.",
        )
    else:
        uploaded_files = st.file_uploader(
            "Upload Excel files",
            type=["xlsx", "xlsm", "xls"],
            accept_multiple_files=True,
            help="Upload one or more Thread DB Excel files.",
        )
    process_button = st.button("🚀 Create master DB", use_container_width=True, type="primary")

    st.divider()
    st.markdown(
        """
        **Columns extracted**
        - Season
        - Style-CW
        - Thread-Color
        - SAP Codes
        - Consumption in CO
        - Source Folder / File / Sheet
        """
    )

if process_button:
    if input_mode == "Local folder" and not main_folder:
        st.error("Please enter a main folder path.")
        st.stop()
    if input_mode == "Upload files" and not uploaded_files:
        st.error("Please upload at least one Excel file.")
        st.stop()

    try:
        progress_bar = st.progress(0)
        status_text = st.empty()

        def update_progress(message: str, current: int, total: int) -> None:
            status_text.text(message)
            if total:
                progress_bar.progress(min(1.0, current / total))

        if input_mode == "Local folder":
            master_db, metadata_log = build_master_db(main_folder, progress_callback=update_progress)
        else:
            master_db, metadata_log = build_master_db_from_files(uploaded_files, progress_callback=update_progress)
    except FileNotFoundError as exc:
        st.error(str(exc))
        st.stop()

    progress_bar.progress(1.0)
    status_text.text("Completed.")
    st.success("Master workbook generated successfully.")

    if master_db.empty:
        st.info("No usable rows were found.")
        st.subheader("Processing details")
        st.dataframe(pd.DataFrame(metadata_log), use_container_width=True)
        st.stop()

    output_path = Path(output_folder).expanduser() / output_name
    output_path.parent.mkdir(parents=True, exist_ok=True)
    master_db.to_excel(output_path, index=False)

    st.success(f"Saved master result to: `{output_path}`")

    col1, col2, col3 = st.columns(3)
    col1.metric("Rows", len(master_db))
    col2.metric("Columns", len(master_db.columns))
    col3.metric(
        "Workbook files scanned",
        len([entry for entry in metadata_log if entry.get("status") == "ok"]),
    )

    st.subheader("Master database preview")
    st.dataframe(master_db.head(200), use_container_width=True)

    st.subheader("Processing summary")
    summary_df = pd.DataFrame(metadata_log)
    st.dataframe(summary_df, use_container_width=True)

    with open(output_path, "rb") as fh:
        file_bytes = fh.read()
    st.download_button(
        label="📥 Download master Excel",
        data=file_bytes,
        file_name=output_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
else:
    st.info("👈 Choose an input mode in the sidebar and click **Create master DB** to get started.")
