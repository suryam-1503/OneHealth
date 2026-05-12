from src.gsheet.gsheet_client import get_uhc_file_sheet
from src.utils.env_data import EnvData
from src.utils.logger import setup_logger


logger = setup_logger(__name__)

def get_practices_from_sheet(sheet, section_name: str) -> list[str]:
    """
    Get all practice names from the Google Sheet for a specific section.
    Returns list of practice names without status suffixes.
    """
    if not sheet:
        logger.info("Google Sheet not available for reading")
        return []

    logger.info(f"Reading practice names from Google Sheet for {section_name}...")

    col_mapping = {
        "Appeals and Disputes": 1,
        "Claim Letters": 2,
        "HouseCalls Documentation": 3,
        "Overpayment Documents": 4,
        "Prior Auth Letters": 5,
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
                "housecalls documentation",
                "overpayment documents",
                "prior auth letters",
            ]:
                practice_names.append(name)

    logger.info(
        f"Found {len(practice_names)} practices in Google Sheet for {section_name}"
    )
    return practice_names


def bulk_update_uhc_file_status(sheet, section_name: str, updates: dict):
    

    if not sheet:
        logger.info("Google Sheet not available")
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

            batch_data.append({"range": f"{col_letter}{i}", "values": [[new_value]]})

    if batch_data:

        sheet.batch_update(batch_data)

        logger.info(f"Bulk updated {len(batch_data)} rows")


def batch_update_practice_names(sheet, practice_names: list[str], section_name: str):
    """
    Batch update multiple practice names (names only, NO status).
    """
    if not sheet or not practice_names:
        logger.info(" No sheet or practice names to update")
        return False

    logger.info(f" Batch writing {len(practice_names)} practices into '{section_name}'")

    # Column mapping (adjust if your sheet layout changes)
    col_mapping = {
        "Appeals and Disputes": 1,
        "Claim Letters": 2,
        "HouseCalls Documentation": 3,
        "Overpayment Documents": 4,
        "Prior Auth Letters": 5,
    }

    col = col_mapping.get(section_name)
    if not col:
        raise Exception(f"Column not defined for section: {section_name}")

    start_row = 2  # after header row

    #  gspread expects VALUES FIRST, then RANGE
    values = [[name] for name in practice_names]
    range_name = f"{chr(64 + col)}{start_row}:{chr(64 + col)}{start_row + len(practice_names) - 1}"

    sheet.update(values, range_name)

    logger.info(" Practice names written to Google Sheet (no status)")
    return True


def clear_sheet(sheet):
    """
    Clear only data (keep header row intact)
    """
    try:
        # Get all values
        all_values = sheet.get_all_values()

        if len(all_values) <= 1:
            logger.info("Sheet already empty (only header present)")
            return

        # Number of rows and columns
        num_rows = len(all_values)
        num_cols = len(all_values[0])

        # Create empty data (excluding header)
        empty_data = [["" for _ in range(num_cols)] for _ in range(num_rows - 1)]

        # Clear from row 2 onwards
        range_name = f"A2:{chr(64 + num_cols)}{num_rows}"

        sheet.update(empty_data, range_name)

        logger.info("Sheet data cleared (header preserved)")

    except Exception as e:
        logger.error(f"Error clearing sheet: {e}")


def get_failed_practices(sheet, section_name):
    try:
        col_mapping = {
            "Appeals and Disputes": 1,
            "Claim Letters": 2,
            "HouseCalls Documentation": 3,
            "Overpayment Documents": 4,
            "Prior Auth Letters": 5,
        }

        col = col_mapping.get(section_name)
        column_values = sheet.col_values(col)

        failed_practices = []

        for cell in column_values[1:]:  # skip header
            if "FILE NOT FOUND" in cell:
                name = cell.split(" - ")[0].strip()
                failed_practices.append(name)

        logger.info(f"Total failed practices: {len(failed_practices)}")
        return failed_practices

    except Exception as e:
        logger.error(f"Error reading sheet: {e}")
        return []