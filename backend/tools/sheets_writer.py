"""Google Sheets writer — create and populate spreadsheets via Sheets API."""
import logging
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from token_manager import get_access_token

logger = logging.getLogger(__name__)


def create_google_sheet(
    user_id: str, title: str, headers: list, rows: list = None
) -> dict:
    """Create a new Google Sheet with column headers and optional data rows."""
    token = get_access_token(user_id)
    creds = Credentials(token=token)
    service = build("sheets", "v4", credentials=creds)

    # Create the spreadsheet
    sheet = service.spreadsheets().create(
        body={"properties": {"title": title}}
    ).execute()
    sheet_id = sheet["spreadsheetId"]

    # Write headers + data
    all_rows = [headers] + (rows or [])
    service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range="Sheet1!A1",
        valueInputOption="USER_ENTERED",
        body={"values": all_rows},
    ).execute()

    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
    logger.info("Created Google Sheet '%s' for user %s: %s", title, user_id, url)

    return {"title": title, "sheet_id": sheet_id, "url": url}
