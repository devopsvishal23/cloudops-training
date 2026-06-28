import anthropic
import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

CATEGORIES = [
    "PROMOTIONAL", "NEWSLETTER", "RECRUITER", "TRANSACTIONAL",
    "SOCIAL", "SECURITY", "PERSONAL", "UNKNOWN"
]

AUTO_DELETE_CATEGORIES = {"PROMOTIONAL", "NEWSLETTER", "RECRUITER", "SOCIAL"}
AUTO_KEEP_CATEGORIES   = {"TRANSACTIONAL", "SECURITY", "PERSONAL"}


def classify_email(sender: str, subject: str, snippet: str) -> str:
    """Returns DELETE or KEEP for a single email."""
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    prompt = f"""You are an email classification assistant. Reply with exactly one word: DELETE or KEEP.

DELETE if: promotional, marketing, newsletters, automated app notifications,
social media notifications, recruiter outreach, spam.

KEEP if: from a real person writing directly, work/project email,
financial statement, legal document, security alert, requires human reply.

Sender: {sender}
Subject: {subject}
Preview: {snippet}

Reply with DELETE or KEEP only:"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=10,
        messages=[{"role": "user", "content": prompt}]
    )

    result = message.content[0].text.strip().upper()
    if result not in ["DELETE", "KEEP"]:
        return "KEEP"
    return result


def categorize_emails(emails: list) -> list:
    """
    Categorizes a list of emails using Claude in batches of 20.
    Each email dict must have: id, sender_email, sender_name, subject, snippet
    Returns list of dicts with added: category, action
    """
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    results = []
    batch_size = 20
    total = len(emails)
    total_batches = (total + batch_size - 1) // batch_size

    print(f"\n  Sending {total} emails to Claude in {total_batches} batch(es)...")

    for batch_start in range(0, total, batch_size):
        batch = emails[batch_start:batch_start + batch_size]
        batch_num = (batch_start // batch_size) + 1
        print(f"  Classifying batch {batch_num}/{total_batches} "
              f"({len(batch)} emails)...", end=" ", flush=True)

        email_list = ""
        for i, email in enumerate(batch, 1):
            email_list += (
                f"{i}. Sender: {email['sender_email']} | "
                f"Name: {email['sender_name']} | "
                f"Subject: {email['subject']} | "
                f"Preview: {email['snippet'][:120]}\n"
            )

        prompt = f"""You are an email classifier. Classify each email into exactly one category.

CATEGORIES:
- PROMOTIONAL  : sales, offers, discounts, deals, product launches
- NEWSLETTER   : blogs, digests, thought leadership, weekly roundups
- RECRUITER    : job offers, hiring outreach, staffing agencies
- TRANSACTIONAL: receipts, invoices, bank alerts, payment confirmations, statements, government notices
- SOCIAL       : LinkedIn, Facebook, Instagram, Reddit, Quora notifications
- SECURITY     : login alerts, 2FA codes, account verification, password reset
- PERSONAL     : real human wrote this directly, requires a reply
- UNKNOWN      : cannot determine with confidence

EMAILS TO CLASSIFY:
{email_list}

RESPOND WITH ONLY A JSON ARRAY. No explanation. No markdown. No backticks.
[
  {{"id": 1, "category": "NEWSLETTER"}},
  {{"id": 2, "category": "PROMOTIONAL"}}
]"""

        try:
            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )

            raw = message.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()

            classifications = json.loads(raw)

            for item in classifications:
                idx = item["id"] - 1
                if idx < len(batch):
                    email = batch[idx]
                    category = item["category"].upper()
                    if category not in CATEGORIES:
                        category = "UNKNOWN"
                    if category in AUTO_DELETE_CATEGORIES:
                        action = "DELETE"
                    elif category in AUTO_KEEP_CATEGORIES:
                        action = "KEEP"
                    else:
                        action = "REVIEW"

                    results.append({
                        "email_id": email["id"],
                        "sender_email": email["sender_email"],
                        "sender_name": email["sender_name"],
                        "subject": email["subject"],
                        "date": email.get("date", ""),
                        "category": category,
                        "action": action
                    })

            print("done.")

        except Exception as e:
            print(f"ERROR: {e}")
            for email in batch:
                results.append({
                    "email_id": email["id"],
                    "sender_email": email["sender_email"],
                    "sender_name": email["sender_name"],
                    "subject": email["subject"],
                    "date": email.get("date", ""),
                    "category": "UNKNOWN",
                    "action": "REVIEW"
                })

    return results