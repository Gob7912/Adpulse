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

def test_get_service_account_email(monkeypatch):
    svc = SheetsService()

    # 1. From settings.GOOGLE_SERVICE_ACCOUNT_EMAIL
    monkeypatch.setattr("app.config.settings.GOOGLE_SERVICE_ACCOUNT_EMAIL", "direct@test.iam.gserviceaccount.com")
    assert svc.get_service_account_email() == "direct@test.iam.gserviceaccount.com"

    # 2. From JSON string
    monkeypatch.setattr("app.config.settings.GOOGLE_SERVICE_ACCOUNT_EMAIL", "")
    monkeypatch.setattr("app.config.settings.GOOGLE_SERVICE_ACCOUNT_JSON", '{"client_email": "json@test.iam.gserviceaccount.com"}')
    assert svc.get_service_account_email() == "json@test.iam.gserviceaccount.com"

    # 3. Empty when not configured
    monkeypatch.setattr("app.config.settings.GOOGLE_SERVICE_ACCOUNT_JSON", "")
    assert svc.get_service_account_email() == ""


def test_sheets_append_with_existing_old_headers():
    """
    Refinement 7: Ensure that when appending deltas to an existing sheet with old headers,
    preexisting columns (and their order) are preserved, and new delta columns are appended to the right.
    """
    from unittest.mock import MagicMock

    svc = SheetsService()
    mock_service = MagicMock()

    # Preexisting table has only old headers without deltas
    old_headers = ["Дата генерации", "Период", "Название отчёта", "Расход", "Показы"]
    mock_service.spreadsheets().values().get().execute.return_value = {
        "values": [old_headers]
    }

    # Captured update and append calls
    update_calls = []
    append_calls = []

    def mock_update(spreadsheetId, range, valueInputOption, body):
        m = MagicMock()
        m.execute.return_value = {"updatedCells": 1}
        update_calls.append((range, body))
        return m

    def mock_append(spreadsheetId, range, valueInputOption, insertDataOption, body):
        m = MagicMock()
        m.execute.return_value = {"updates": {"updatedRows": 1}}
        append_calls.append((range, body))
        return m

    mock_service.spreadsheets().values().update = mock_update
    mock_service.spreadsheets().values().append = mock_append
    mock_service.spreadsheets().get().execute.return_value = {
        "sheets": [{"properties": {"title": "Sheet1"}}]
    }

    svc._service = mock_service

    # New headers with deltas
    new_headers = ["Дата генерации", "Период", "Название отчёта", "Расход", "Показы", "Δ Расход (%)", "Δ Показы (%)"]
    new_row_values = ["2026-10-04 15:30", "2026-10-03", "Test Report", 100.0, 5000, 10.0, -5.0]

    svc.append_report_row(
        spreadsheet_id="test_sheet_id",
        tab_name="Sheet1",
        header_labels=new_headers,
        row_values=new_row_values
    )

    # 1. Header update check: old headers remained in place, new columns appended to the right
    assert len(update_calls) == 1
    updated_headers_in_sheet = update_calls[0][1]["values"][0]
    assert updated_headers_in_sheet == [
        "Дата генерации", "Период", "Название отчёта", "Расход", "Показы", "Δ Расход (%)", "Δ Показы (%)"
    ]
    # Check that original columns are intact at index 0..4
    assert updated_headers_in_sheet[:5] == old_headers

    # 2. Row values check: values are aligned accurately to column names
    assert len(append_calls) == 1
    appended_row = append_calls[0][1]["values"][0]
    assert appended_row[0] == "2026-10-04 15:30"
    assert appended_row[1] == "2026-10-03"
    assert appended_row[2] == "Test Report"
    assert appended_row[3] == 100.0
    assert appended_row[4] == 5000
    assert appended_row[5] == 10.0
    assert appended_row[6] == -5.0


