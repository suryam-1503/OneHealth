from src.gsheet.gsheet_client import get_uhc_file_sheet
from utils.env_data import EnvData


def get_practices_from_sheet(sheet, section_name: str) -> list[str]:
    """
    Get all practice names from the Google Sheet for a specific section.
    Returns list of practice names without status suffixes.
    """
    if not sheet:
        print(" Google Sheet not available for reading")
        return []

    print(f"Reading practice names from Google Sheet for {section_name}...")

    col_mapping = {
        "Appeals and Disputes": 1,
        "Claim Letters": 2,
        "Overpayment Documents": 3,
        "Prior Auth Letters": 4,
    }

    col = col_mapping.get(section_name, 1)
    column_values = sheet.col_values(col)
    practice_names = []

    for cell_value in column_values:
        if cell_value and cell_value.strip():
            if " - " in cell_value:
                name = cell_value.split(" - ")[0].strip()
            else:
                name = cell_value.strip()

            if name.lower() not in [
                "appeals and disputes",
                "claim letters",
                "overpayment documents",
                "prior auth letters",
            ]:
                practice_names.append(name)

    print(f"Found {len(practice_names)} practices in Google Sheet for {section_name}")
    return practice_names


def bulk_update_uhc_file_status(
    sheet,
    section_name: str,
    updates: dict
):
    """
    Bulk update practice statuses in Google Sheet.

    updates example:
    {
        "Practice A": "file downloaded",
        "Practice B": "FILE NOT FOUND"
    }
    """

    if not sheet:
        print("Google Sheet not available")
        return

    headers = sheet.row_values(1)

    if section_name not in headers:
        raise Exception(f"Column '{section_name}' not found in Google Sheet")

    col_index = headers.index(section_name) + 1
    col_letter = chr(64 + col_index)

    col_values = sheet.col_values(col_index)

    batch_data = []

    for i, cell_value in enumerate(col_values[1:], start=2):  # skip header row

        base_name = cell_value.split(" - ")[0].strip()

        if base_name in updates:

            status = updates[base_name]
            new_value = f"{base_name} - {status}"

            batch_data.append({
                "range": f"{col_letter}{i}",
                "values": [[new_value]]
            })

    if batch_data:

        sheet.batch_update(batch_data)

        print(f"Bulk updated {len(batch_data)} rows")
    
def batch_update_practice_names(sheet, practice_names: list[str], section_name: str):
    """
    Batch update multiple practice names (names only, NO status).
    """
    if not sheet or not practice_names:
        print(" No sheet or practice names to update")
        return False

    print(f" Batch writing {len(practice_names)} practices into '{section_name}'")

    # Column mapping (adjust if your sheet layout changes)
    col_mapping = {
        "Appeals and Disputes": 1,
        "Claim Letters": 2,
        "Overpayment Documents": 3,
        "Prior Auth Letters": 4,
    }

    col = col_mapping.get(section_name)
    if not col:
        raise Exception(f"Column not defined for section: {section_name}")

    start_row = 2  # after header row

    #  gspread expects VALUES FIRST, then RANGE
    values = [[name] for name in practice_names]
    range_name = f"{chr(64 + col)}{start_row}:{chr(64 + col)}{start_row + len(practice_names) - 1}"

    sheet.update(values, range_name)

    print(" Practice names written to Google Sheet (no status)")
    return True