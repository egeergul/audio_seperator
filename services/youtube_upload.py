from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .common import validate_readable_file
from .config import YOUTUBE_CLIENT_SECRETS_PATH, YOUTUBE_TOKEN_PATH

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
VALID_PRIVACY_STATUSES = {"private", "unlisted", "public"}
MAX_RETRIES = 5


def parse_video_metadata(metadata_text_path: Path) -> dict[str, Any]:
    validated = validate_readable_file(metadata_text_path)
    content = validated.read_text(encoding="utf-8")

    title = ""
    description = ""
    tags: list[str] = []

    sections = content.split("\n")
    current_section: str | None = None
    section_lines: dict[str, list[str]] = {
        "title": [],
        "description": [],
        "tags": [],
    }

    for line in sections:
        stripped = line.strip()
        if stripped.lower() == "title:":
            current_section = "title"
            continue
        elif stripped.lower() == "description:":
            current_section = "description"
            continue
        elif stripped.lower() == "tags:":
            current_section = "tags"
            continue
        elif stripped.lower() == "pin comment:":
            current_section = None
            continue

        if current_section and current_section in section_lines:
            section_lines[current_section].append(line)

    title = "\n".join(section_lines["title"]).strip()
    description = "\n".join(section_lines["description"]).strip()

    raw_tags = "\n".join(section_lines["tags"]).strip()
    if raw_tags:
        tags = [t.strip() for t in raw_tags.split(",") if t.strip()]

    if not title:
        raise ValueError(f"Could not parse title from metadata file: {validated}")

    return {"title": title, "description": description, "tags": tags}


def authenticate_youtube(
    client_secrets_path: Path,
    token_path: Path,
) -> Any:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds: Credentials | None = None

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            creds = None
            token_path.unlink(missing_ok=True)

    if not creds or not creds.valid:
        if not client_secrets_path.is_file():
            raise FileNotFoundError(
                f"YouTube client secrets file not found: {client_secrets_path}\n"
                "To set up YouTube uploads:\n"
                "  1. Go to https://console.cloud.google.com\n"
                "  2. Create a project and enable the YouTube Data API v3\n"
                "  3. Create OAuth 2.0 credentials (Desktop app)\n"
                "  4. Download the JSON and save as client_secrets.json in the project root"
            )
        flow = InstalledAppFlow.from_client_secrets_file(
            str(client_secrets_path), SCOPES
        )
        creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return build("youtube", "v3", credentials=creds)


def upload_video_to_youtube(
    video_file_path: Path,
    metadata_text_path: Path,
    privacy_status: str = "public",
    client_secrets_path: Path | None = None,
    token_path: Path | None = None,
) -> str:
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    validated_video = validate_readable_file(video_file_path)
    validated_metadata = validate_readable_file(metadata_text_path)

    if client_secrets_path is None:
        client_secrets_path = YOUTUBE_CLIENT_SECRETS_PATH
    if token_path is None:
        token_path = YOUTUBE_TOKEN_PATH

    if privacy_status not in VALID_PRIVACY_STATUSES:
        raise ValueError(
            f"Invalid privacy status: {privacy_status!r}. "
            f"Must be one of: {', '.join(sorted(VALID_PRIVACY_STATUSES))}"
        )

    metadata = parse_video_metadata(validated_metadata)

    print("  Authenticating with YouTube...")
    youtube = authenticate_youtube(client_secrets_path, token_path)

    body = {
        "snippet": {
            "title": metadata["title"],
            "description": metadata["description"],
            "tags": metadata["tags"],
            "categoryId": "10",
        },
        "status": {
            "privacyStatus": privacy_status,
        },
    }

    media = MediaFileUpload(
        str(validated_video),
        mimetype="video/mp4",
        resumable=True,
        chunksize=10 * 1024 * 1024,
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    print(f"  Uploading {validated_video.name}...")
    response = None
    retry = 0
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                print(f"  Upload progress: {int(status.progress() * 100)}%")
        except HttpError as exc:
            if exc.resp.status in (500, 502, 503, 504) and retry < MAX_RETRIES:
                retry += 1
                wait = 2**retry
                print(f"  Retryable error ({exc.resp.status}), waiting {wait}s...")
                time.sleep(wait)
            else:
                raise

    video_id = response["id"]
    return video_id
