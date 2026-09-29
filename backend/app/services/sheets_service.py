import re
import json
import logging
from typing import Any, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.config import settings

logger = logging.getLogger("adpulse.sheets")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

class SheetsService:
    def __init__(self):
        self._service = None

    def _get_credentials(self):
        # 1. From JSON env string or file
        if settings.GOOGLE_SERVICE_ACCOUNT_JSON:
            raw = settings.GOOGLE_SERVICE_ACCOUNT_JSON.strip()
            if raw.startswith("{"):
                info = json.loads(raw)
                return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
            else:
                # File path
                return service_account.Credentials.from_service_account_file(raw, scopes=SCOPES)
        return None

    def get_service(self):
        if not self._service:
            creds = self._get_credentials()
            if not creds:
                raise ValueError("Google Service Account не настроен в AdPulse (отсутствует GOOGLE_SERVICE_ACCOUNT_JSON).")
            self._service = build("sheets", "v4", credentials=creds, cache_discovery=False)
        return self._service

    @staticmethod
    def extract_spreadsheet_id(url_or_id: str) -> str:
        """Extracts the 44-character spreadsheet ID from a Google Sheets URL or returns the input if already an ID."""
        cleaned = url_or_id.strip()
        match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", cleaned)
        if match:
            return match.group(1)
        return cleaned

    @staticmethod
    def escape_tab_name(tab_name: str) -> str:
        """
        Escapes single quotes in sheet tab name according to Google Sheets A1 notation rules.
        In A1 notation, single quotes in sheet titles must be doubled (' -> '').
        """
        return tab_name.replace("'", "''")

    def _ensure_tab_exists(self, service, spreadsheet_id: str, tab_name: str) -> bool:
        """Ensures that the specified sheet tab exists in the spreadsheet, creating it if needed."""
        try:
            sheet_meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            sheets = sheet_meta.get("sheets", [])
            sheet_titles = [s.get("properties", {}).get("title") for s in sheets]

            if tab_name not in sheet_titles:
                body = {
                    "requests": [
                        {
                            "addSheet": {
                                "properties": {"title": tab_name}
                            }
                        }
                    ]
                }
                service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()
                logger.info(f"Created missing sheet tab '{tab_name}' in spreadsheet {spreadsheet_id}")
            return True
        except Exception as exc:
            logger.warning(f"Could not verify/create sheet tab '{tab_name}': {exc}")
            return False

    def verify_sheet_access(self, spreadsheet_id: str, tab_name: str | None = None) -> dict[str, Any]:
        """Validates read and write permissions to the Google Sheet and checks tab name."""
        try:
            service = self.get_service()
            sheet_meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            title = sheet_meta.get("properties", {}).get("title", "Untitled")

            sheets = sheet_meta.get("sheets", [])
            sheet_titles = [s.get("properties", {}).get("title") for s in sheets]

            tab_to_use = tab_name or (sheet_titles[0] if sheet_titles else "Sheet1")
            
            # Verify if tab exists, or can create it
            if tab_to_use not in sheet_titles:
                self._ensure_tab_exists(service, spreadsheet_id, tab_to_use)

            return {
                "success": True,
                "title": title,
                "tab_name": tab_to_use,
                "message": f"Доступ к таблице «{title}» успешно подтвержден"
            }
        except HttpError as exc:
            status = exc.resp.status
            if status == 404:
                return {"success": False, "message": "Таблица не найдена. Проверьте правильность ссылки."}
            elif status == 403:
                email = settings.GOOGLE_SERVICE_ACCOUNT_EMAIL or "service-account email"
                return {
                    "success": False,
                    "message": f"Нет прав доступа к таблице. Поделитесь таблицей с email: {email} и выдайте роль «Редактор»."
                }
            return {"success": False, "message": f"Ошибка Google Sheets API: {exc}"}
        except Exception as exc:
            return {"success": False, "message": f"Ошибка проверки таблицы: {str(exc)}"}

    def append_report_row(
        self,
        spreadsheet_id: str,
        tab_name: str,
        header_labels: list[str],
        row_values: list[Any]
    ) -> bool:
        """
        Appends a report row to the target spreadsheet.
        Automatically creates tab and header row if missing, and dynamically adds missing columns.
        """
        service = self.get_service()
        tab = tab_name or "Sheet1"

        # Ensure tab exists in the spreadsheet
        self._ensure_tab_exists(service, spreadsheet_id, tab)
        escaped_tab = self.escape_tab_name(tab)

        # 1. Fetch current header row (A1:ZZ1)
        res = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"'{escaped_tab}'!1:1"
        ).execute()

        existing_rows = res.get("values", [])
        if not existing_rows or not existing_rows[0]:
            # Sheet is empty, write headers at row 1
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"'{escaped_tab}'!A1",
                valueInputOption="USER_ENTERED",
                body={"values": [header_labels]}
            ).execute()
            active_headers = list(header_labels)
        else:
            active_headers = list(existing_rows[0])
            # Check if any new headers need to be appended
            updated_headers = list(active_headers)
            headers_modified = False
            for h in header_labels:
                if h not in active_headers:
                    updated_headers.append(h)
                    headers_modified = True

            if headers_modified:
                service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range=f"'{escaped_tab}'!A1",
                    valueInputOption="USER_ENTERED",
                    body={"values": [updated_headers]}
                ).execute()
                active_headers = updated_headers

        # Build row aligned to active_headers, preserving numeric types
        row_map = dict(zip(header_labels, row_values))
        aligned_row = []
        for col in active_headers:
            val = row_map.get(col, "")
            if val is None:
                aligned_row.append("")
            else:
                aligned_row.append(val)

        # 2. Append the data row
        service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=f"'{escaped_tab}'!A1",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": [aligned_row]}
        ).execute()

        logger.info(f"Appended row into sheet {spreadsheet_id} tab {tab}")
        return True

sheets_service = SheetsService()
