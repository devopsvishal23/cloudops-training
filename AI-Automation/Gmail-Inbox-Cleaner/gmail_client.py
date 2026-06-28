import os
from collections import defaultdict
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.utils import parsedate_to_datetime

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"


def get_gmail_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def build_query(mode: str, date_after: str = None, date_before: str = None) -> str:
    """
    Build Gmail search query string.
    mode: 'unread' or 'read'
    date_after / date_before: strings in format YYYY/MM/DD
    """
    parts = []
    if mode == "unread":
        parts.append("is:unread")
    elif mode == "read":
        parts.append("is:read")
    if date_after:
        parts.append(f"after:{date_after}")
    if date_before:
        parts.append(f"before:{date_before}")
    return " ".join(parts)


def parse_date(date_str: str) -> str:
    """
    Parse email Date header into clean DD Mon YYYY format.
    Returns empty string if parsing fails.
    """
    if not date_str:
        return ""
    try:
        dt = parsedate_to_datetime(date_str)
        return dt.strftime("%d %b %Y")
    except Exception:
        return date_str[:16]


def fetch_emails(service, mode: str = "unread",
                 date_after: str = None, date_before: str = None) -> list:
    """
    Fetch emails from Gmail using batch requests.
    mode     : 'unread' or 'read'
    date_after  : 'YYYY/MM/DD' — fetch emails after this date
    date_before : 'YYYY/MM/DD' — fetch emails before this date

    Returns flat list of dicts:
    {id, sender_name, sender_email, subject, snippet, date}
    """
    query = build_query(mode, date_after, date_before)

    # ── Step 1: Collect all message IDs ─────────────────────
    all_ids = []
    page_token = None

    print("  Collecting message IDs", end="", flush=True)

    while True:
        print(".", end="", flush=True)
        kwargs = {
            "userId": "me",
            "labelIds": ["INBOX"],
            "q": query,
            "maxResults": 500
        }
        if page_token:
            kwargs["pageToken"] = page_token

        result = service.users().messages().list(**kwargs).execute()
        messages = result.get("messages", [])
        all_ids.extend([m["id"] for m in messages])

        page_token = result.get("nextPageToken")
        if not page_token:
            break

    print(f" found {len(all_ids)} emails.")

    if not all_ids:
        return []

    # ── Step 2: Fetch metadata in batches of 100 ────────────
    emails = []
    batch_size = 100
    total_batches = (len(all_ids) + batch_size - 1) // batch_size

    print(f"  Fetching metadata in {total_batches} batch(es)", end="", flush=True)

    for batch_start in range(0, len(all_ids), batch_size):
        print(".", end="", flush=True)
        batch_ids = all_ids[batch_start:batch_start + batch_size]
        batch_results = {}

        def make_callback(msg_id):
            def callback(request_id, response, exception):
                if exception:
                    return
                batch_results[msg_id] = response
            return callback

        batch = service.new_batch_http_request()
        for msg_id in batch_ids:
            batch.add(
                service.users().messages().get(
                    userId="me",
                    id=msg_id,
                    format="metadata",
                    metadataHeaders=["From", "Subject", "Date"]
                ),
                callback=make_callback(msg_id)
            )
        batch.execute()

        for msg_id, msg_data in batch_results.items():
            headers = {
                h["name"]: h["value"]
                for h in msg_data["payload"]["headers"]
            }
            raw_from = headers.get("From", "Unknown")

            if "<" in raw_from and ">" in raw_from:
                sender_name = raw_from.split("<")[0].strip().strip('"')
                sender_email = raw_from.split("<")[1].strip(">").strip()
            else:
                sender_name = raw_from
                sender_email = raw_from

            emails.append({
                "id": msg_id,
                "sender_raw": raw_from,
                "sender_name": sender_name,
                "sender_email": sender_email.lower(),
                "subject": headers.get("Subject", "(No Subject)"),
                "snippet": msg_data.get("snippet", ""),
                "date": parse_date(headers.get("Date", ""))
            })

    print(" done.\n")
    return emails


def group_by_sender(emails: list) -> dict:
    """
    Groups emails by sender_email.
    Returns dict sorted by count descending.
    """
    groups = defaultdict(lambda: {
        "name": "", "sender_email": "", "emails": [], "count": 0
    })

    for email in emails:
        key = email["sender_email"]
        groups[key]["name"] = email["sender_name"] if email["sender_name"] else key
        groups[key]["sender_email"] = key
        groups[key]["emails"].append(email)
        groups[key]["count"] += 1

    return dict(
        sorted(groups.items(), key=lambda x: x[1]["count"], reverse=True)
    )


def move_to_trash(service, email_id: str) -> bool:
    try:
        service.users().messages().trash(userId="me", id=email_id).execute()
        return True
    except Exception as e:
        print(f"  Failed to trash {email_id}: {e}")
        return False


def mark_as_read(service, email_id: str) -> bool:
    try:
        service.users().messages().modify(
            userId="me",
            id=email_id,
            body={"removeLabelIds": ["UNREAD"]}
        ).execute()
        return True
    except Exception as e:
        print(f"  Failed to mark as read {email_id}: {e}")
        return False