#!/usr/bin/env python3
import os
import json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = "/Users/tainguyen/Programing/Python/Money-Tool"
secret_path = os.getenv("CLIENT_SECRET_PATH", "client_secret.json")
TOKEN_CACHE_PATH = os.path.join(BASE_DIR, "token_cache.json")

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl"
]


def get_youtube_service():
    creds = None

    if os.path.exists(TOKEN_CACHE_PATH):
        with open(TOKEN_CACHE_PATH, "r") as f:
            token_data = json.load(f)
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            creds = None

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(secret_path, SCOPES)
        creds = flow.run_local_server(port=0)

    with open(TOKEN_CACHE_PATH, "w") as f:
        f.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)


def list_playlists(youtube):
    playlists = []
    request = youtube.playlists().list(
        part="snippet",
        mine=True,
        maxResults=50
    )

    while request:
        response = request.execute()
        playlists.extend(response.get("items", []))
        request = youtube.playlists().list_next(request, response)

    return playlists


def main():
    youtube = get_youtube_service()
    playlists = list_playlists(youtube)

    if not playlists:
        print("No playlists found.")
        return

    print(f"\nFound {len(playlists)} playlist(s):\n")
    for p in playlists:
        pid = p["id"]
        title = p["snippet"]["title"]
        print(f"{pid} - {title}")


if __name__ == "__main__":
    main()
