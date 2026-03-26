"""Google Drive file uploader — uploads any local binary file and returns a shareable link."""
import logging
import mimetypes
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from token_manager import get_access_token

logger = logging.getLogger(__name__)

MIME_TYPES = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "pdf": "application/pdf",
}


def upload_file_to_drive(
    user_id: str,
    local_path: str,
    filename: str,
    document_type: str,
) -> dict:
    """
    Upload a local binary file to Google Drive and make it readable by anyone with the link.

    Args:
        user_id:       User whose Drive credentials are used.
        local_path:    Absolute path to the file on disk.
        filename:      Filename to use in Drive (e.g. "Q3 Report.docx").
        document_type: One of "docx", "xlsx", "pptx", "pdf".

    Returns:
        {"file_id": str, "url": str, "name": str}
    """
    token = get_access_token(user_id)
    creds = Credentials(token=token)
    service = build("drive", "v3", credentials=creds)

    mimetype = MIME_TYPES.get(document_type) or (
        mimetypes.guess_type(filename)[0] or "application/octet-stream"
    )

    file_metadata = {"name": filename}
    media = MediaFileUpload(local_path, mimetype=mimetype, resumable=False)

    file = (
        service.files()
        .create(body=file_metadata, media_body=media, fields="id,name,webViewLink")
        .execute()
    )

    file_id = file["id"]

    # Make the file readable by anyone with the link
    service.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "reader"},
    ).execute()

    url = file.get("webViewLink", f"https://drive.google.com/file/d/{file_id}/view")
    logger.info(
        "Uploaded %s to Drive for user %s: %s", filename, user_id, url
    )

    return {"file_id": file_id, "url": url, "name": file["name"]}
