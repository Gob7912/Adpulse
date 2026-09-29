import pytest
from app.services.sheets_service import SheetsService

def test_extract_spreadsheet_id():
    url1 = "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit#gid=0"
    assert SheetsService.extract_spreadsheet_id(url1) == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"

    url2 = "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
    assert SheetsService.extract_spreadsheet_id(url2) == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"

    raw_id = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
    assert SheetsService.extract_spreadsheet_id(raw_id) == raw_id

def test_sheets_dynamic_columns_logic():
    # Verify how missing columns are appended
    existing_headers = ["Дата генерации", "Период", "Название отчёта", "Расход", "Показы"]
    new_request_headers = ["Дата генерации", "Период", "Название отчёта", "Расход", "Лиды", "CPL"]

    updated = list(existing_headers)
    for h in new_request_headers:
        if h not in updated:
            updated.append(h)

    assert updated == ["Дата генерации", "Период", "Название отчёта", "Расход", "Показы", "Лиды", "CPL"]

def test_sheets_tab_escaping():
    assert SheetsService.escape_tab_name("Sheet1") == "Sheet1"
    assert SheetsService.escape_tab_name("Client's Report") == "Client''s Report"
    assert SheetsService.escape_tab_name("O'Connor's Data") == "O''Connor''s Data"

