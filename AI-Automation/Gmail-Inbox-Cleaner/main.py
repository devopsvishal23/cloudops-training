import sys
import json
import os
from datetime import datetime, timedelta
from gmail_client import (
    get_gmail_service,
    fetch_emails,
    group_by_sender,
    move_to_trash,
    mark_as_read
)
from classifier import categorize_emails

# ── SAFETY SWITCH ─────────────────────────────────────────
# True  = show what WOULD happen, touch nothing
# False = actually modify your Gmail inbox
DRY_RUN = False
# ──────────────────────────────────────────────────────────

CACHE_UNREAD = "cache_unread.json"
CACHE_READ   = "cache_read.json"
CACHE_MAX_AGE_MINUTES = 30

CATEGORY_CONFIG = {
    "PROMOTIONAL":   ("🛍️ ", "Recommended: DELETE"),
    "NEWSLETTER":    ("📰 ", "Recommended: DELETE"),
    "RECRUITER":     ("💼 ", "Recommended: DELETE"),
    "TRANSACTIONAL": ("🏦 ", "Recommended: KEEP"),
    "SOCIAL":        ("📱 ", "Recommended: DELETE"),
    "SECURITY":      ("🔒 ", "Recommended: KEEP"),
    "PERSONAL":      ("👤 ", "Recommended: KEEP"),
    "UNKNOWN":       ("❓ ", "Recommended: REVIEW"),
}

TIME_WINDOWS = {
    "1": ("Last 30 days",    30),
    "2": ("Last 6 months",   180),
    "3": ("Last 1 year",     365),
    "4": ("Last 3 years",    1095),
    "5": ("Last 5 years",    1825),
    "6": ("Everything",      None),
    "7": ("Custom range",    "custom"),
}

LARGE_WINDOW_THRESHOLD = 365  # warn if window is larger than 1 year


# ════════════════════════════════════════════════════════════
# CACHE HELPERS
# ════════════════════════════════════════════════════════════

def save_cache(emails: list, cache_file: str):
    cache = {
        "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "emails": emails
    }
    with open(cache_file, "w") as f:
        json.dump(cache, f)


def load_cache(cache_file: str):
    if not os.path.exists(cache_file):
        return None, None, None
    try:
        with open(cache_file, "r") as f:
            cache = json.load(f)
        fetched_at_str = cache["fetched_at"]
        fetched_at_dt = datetime.strptime(fetched_at_str, "%Y-%m-%d %H:%M:%S")
        age_minutes = int((datetime.now() - fetched_at_dt).total_seconds() // 60)
        return cache["emails"], fetched_at_str, age_minutes
    except Exception:
        return None, None, None


def fetch_fresh(service, mode: str, cache_file: str,
                date_after: str = None, date_before: str = None):
    print("\n  Fetching from Gmail...")
    emails = fetch_emails(service, mode=mode,
                          date_after=date_after, date_before=date_before)
    save_cache(emails, cache_file)
    fetched_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"  Fetched {len(emails)} emails. Cache saved.")
    return emails, fetched_at


# ════════════════════════════════════════════════════════════
# DISPLAY HELPERS
# ════════════════════════════════════════════════════════════

def print_bifurcation_table(grouped: dict, mode: str,
                             fetched_at: str = None, age_minutes: int = None):
    mode_label = "📬 UNREAD" if mode == "unread" else "📂 READ"
    print("\n" + "=" * 72)
    print(f"  {mode_label} EMAIL SENDER TABLE")
    if fetched_at:
        age_str = f"  ({age_minutes} min ago)" if age_minutes is not None else ""
        stale = ""
        if age_minutes is not None and age_minutes > CACHE_MAX_AGE_MINUTES:
            stale = "  ⚠️  STALE — press [F] to refresh"
        print(f"  Data fetched: {fetched_at}{age_str}{stale}")
    print(f"  {'#':<5} {'SENDER EMAIL':<42} {'NAME':<20} {'EMAILS':>5}")
    print("=" * 72)
    for idx, (sender_email, data) in enumerate(grouped.items(), 1):
        name = data["name"][:18] if data["name"] else "-"
        print(f"  {idx:<5} {sender_email[:40]:<42} {name:<20} {data['count']:>5}")
    print("=" * 72)
    total_emails = sum(d["count"] for d in grouped.values())
    print(f"  Total senders: {len(grouped)}  |  Total emails: {total_emails}")
    print("=" * 72)


def preview_emails(emails: list, sender_email: str):
    """
    Show all emails from a sender with date and subject.
    Allows user to skip specific emails before bulk action.
    Returns list of email IDs the user wants to SKIP (keep).
    """
    print(f"\n  📬 {len(emails)} email(s) from {sender_email}")
    print("  " + "-" * 65)
    for i, email in enumerate(emails, 1):
        date_str = f"[{email.get('date', 'Unknown date')}]"
        subject = email["subject"][:45]
        print(f"  {i:>3}. {date_str:<15}  {subject}")
    print("  " + "-" * 65)

    print("\n  SKIP specific emails? (enter numbers to KEEP, e.g. 1,3,5)")
    print("  Or press Enter to act on ALL emails.")
    raw = input("  Emails to skip: ").strip()

    skip_indices = set()
    if raw:
        for part in raw.split(","):
            part = part.strip()
            if part.isdigit():
                idx = int(part)
                if 1 <= idx <= len(emails):
                    skip_indices.add(idx - 1)

    if skip_indices:
        skipped = [emails[i]["subject"][:50] for i in skip_indices]
        print(f"\n  Skipping {len(skip_indices)} email(s):")
        for s in skipped:
            print(f"    ↩️  {s}")

    return skip_indices


def execute_bulk_action(service, emails: list, action: str,
                        label: str, skip_indices: set = None):
    if skip_indices is None:
        skip_indices = set()

    to_act = [e for i, e in enumerate(emails) if i not in skip_indices]
    total = len(to_act)

    if total == 0:
        print("  Nothing to action after skipping.")
        return 0

    verb = "trash" if action == "delete" else "mark as read"
    prefix = "[DRY RUN] Would" if DRY_RUN else ""
    print(f"\n  {prefix} {verb} {total} email(s) from {label}...")

    success = 0
    for email in to_act:
        if not DRY_RUN:
            if action == "delete":
                if move_to_trash(service, email["id"]):
                    success += 1
            elif action == "read":
                if mark_as_read(service, email["id"]):
                    success += 1
        else:
            success += 1

    label2 = "DRY RUN: Would have processed" if DRY_RUN else "Done:"
    print(f"  {label2} {success}/{total} emails.")
    return success


# ════════════════════════════════════════════════════════════
# CLAUDE ANALYSIS — works for both modes
# ════════════════════════════════════════════════════════════

def run_claude_analysis(service, grouped: dict, emails: list,
                        fetched_at: str, cache_file: str, mode: str):
    print("\n" + "=" * 72)
    print("  CLAUDE AI ANALYSIS — Senders with 1–9 emails")
    print("=" * 72)

    single_senders = {k: v for k, v in grouped.items() if v["count"] <= 9}
    total = len(single_senders)

    if total == 0:
        print("\n  No senders with 9 or fewer emails found.")
        return grouped, emails

    est_cost = total * 0.000001
    est_batches = (total + 19) // 20
    print(f"\n  Found {total} senders with 1–9 emails.")
    print(f"  Estimated cost: ${est_cost:.6f}  |  Batches: {est_batches}")

    confirm = input("\n  Proceed with Claude analysis? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("  Cancelled.")
        return grouped, emails

    emails_to_classify = []
    for sender_email, data in single_senders.items():
        for email in data["emails"]:
            emails_to_classify.append({
                "id": email["id"],
                "sender_email": sender_email,
                "sender_name": data["name"],
                "subject": email["subject"],
                "snippet": email["snippet"],
                "date": email.get("date", "")
            })

    classified = categorize_emails(emails_to_classify)

    # Group by category
    by_category = {}
    for item in classified:
        cat = item["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(item)

    # Display summary
    print("\n" + "=" * 72)
    print("  ANALYSIS RESULTS")
    print("=" * 72)
    cat_list = []
    for idx, (cat, items) in enumerate(
        sorted(by_category.items(), key=lambda x: len(x[1]), reverse=True), 1
    ):
        emoji, rec = CATEGORY_CONFIG.get(cat, ("  ", "Recommended: REVIEW"))
        print(f"  [{idx}] {emoji} {cat:<15} {len(items):>4} emails   {rec}")
        cat_list.append(cat)
    print("=" * 72)

    while True:
        print("\n  Enter CATEGORY NUMBER to act | [B] Back to main menu")
        cat_raw = input("  Your choice: ").strip().upper()

        if cat_raw == "B":
            break

        try:
            cat_num = int(cat_raw)
            if cat_num < 1 or cat_num > len(cat_list):
                print(f"  Enter a number between 1 and {len(cat_list)}.")
                continue
        except ValueError:
            print("  Invalid input.")
            continue

        selected_cat = cat_list[cat_num - 1]
        selected_items = by_category[selected_cat]
        emoji, rec = CATEGORY_CONFIG.get(selected_cat, ("  ", ""))

        print(f"\n  {emoji} {selected_cat} — {len(selected_items)} emails")
        print("  " + "-" * 65)
        for i, item in enumerate(selected_items, 1):
            date_str = f"[{item.get('date', '?')}]"
            print(f"  {i:>3}. {date_str:<15}  "
                  f"{item['sender_email'][:28]:<30}  {item['subject'][:20]}")
        print("  " + "-" * 65)
        print(f"  {rec}")

        print("\n  ACTION:")
        print("  [1] Delete All")
        print("  [2] Mark All as Read")
        print("  [3] Skip this category")
        action_raw = input("  Your choice: ").strip()

        if action_raw == "3":
            continue
        if action_raw not in ["1", "2"]:
            print("  Invalid. Enter 1, 2, or 3.")
            continue

        action = "delete" if action_raw == "1" else "read"
        confirm = input(
            f"\n  Confirm: {action.upper()} ALL {len(selected_items)} "
            f"{selected_cat} emails? (yes/no): "
        ).strip().lower()

        if confirm != "yes":
            print("  Cancelled.")
            continue

        email_objs = [{"id": item["email_id"]} for item in selected_items]
        execute_bulk_action(service, email_objs, action,
                            f"{len(email_objs)} {selected_cat} senders")

        if not DRY_RUN:
            affected = {item["sender_email"] for item in selected_items}
            for sender in affected:
                if sender in grouped:
                    del grouped[sender]
            emails = [e for e in emails if e["sender_email"] not in affected]
            save_cache(emails, cache_file)
            del by_category[selected_cat]
            cat_list.remove(selected_cat)

            if not by_category:
                print("\n  All categories processed.")
                break

            print("\n" + "=" * 72)
            print("  REMAINING CATEGORIES")
            print("=" * 72)
            cat_list = []
            for idx, (cat, items) in enumerate(
                sorted(by_category.items(), key=lambda x: len(x[1]), reverse=True), 1
            ):
                emoji, rec = CATEGORY_CONFIG.get(cat, ("  ", ""))
                print(f"  [{idx}] {emoji} {cat:<15} {len(items):>4} emails   {rec}")
                cat_list.append(cat)
            print("=" * 72)

    return grouped, emails


# ════════════════════════════════════════════════════════════
# TIME WINDOW SELECTOR (for READ mode)
# ════════════════════════════════════════════════════════════

def select_time_window():
    """
    Shows time window menu and returns (date_after, date_before, label).
    """
    print("\n" + "=" * 72)
    print("  SELECT TIME WINDOW FOR READ EMAILS")
    print("=" * 72)
    for key, (label, days) in TIME_WINDOWS.items():
        warn = "  ⚠️  may take 30+ mins" if isinstance(days, int) and days > LARGE_WINDOW_THRESHOLD else ""
        print(f"  [{key}] {label}{warn}")
    print("=" * 72)

    while True:
        choice = input("  Your choice: ").strip()
        if choice not in TIME_WINDOWS:
            print(f"  Enter a number between 1 and {len(TIME_WINDOWS)}.")
            continue

        label, days = TIME_WINDOWS[choice]

        if choice == "6":
            confirm = input(
                "\n  ⚠️  Fetching ALL emails may take 30–90 minutes and "
                "could scan 50,000+ emails.\n  Are you sure? (yes/no): "
            ).strip().lower()
            if confirm != "yes":
                print("  Cancelled. Please pick another window.")
                continue
            return None, None, "Everything"

        if choice == "7":
            print("\n  Enter custom date range (format: YYYY/MM/DD)")
            date_after  = input("  From date (e.g. 2020/01/01): ").strip()
            date_before = input("  To date   (e.g. 2022/12/31): ").strip()
            return date_after, date_before, f"{date_after} to {date_before}"

        date_after = (datetime.now() - timedelta(days=days)).strftime("%Y/%m/%d")

        if days > LARGE_WINDOW_THRESHOLD:
            confirm = input(
                f"\n  ⚠️  Fetching {label} may take 10–30 minutes. "
                f"Continue? (yes/no): "
            ).strip().lower()
            if confirm != "yes":
                print("  Cancelled. Please pick another window.")
                continue

        return date_after, None, label


# ════════════════════════════════════════════════════════════
# SHARED INBOX LOOP — used by both modes
# ════════════════════════════════════════════════════════════

def inbox_loop(service, mode: str, cache_file: str,
               date_after: str = None, date_before: str = None,
               window_label: str = ""):
    """
    Main interactive loop shared by both unread and read modes.
    """
    mode_label = "📬 UNREAD" if mode == "unread" else f"📂 READ ({window_label})"

    # Load cache or fetch fresh
    emails, fetched_at, age_minutes = load_cache(cache_file)

    if emails and age_minutes is not None and age_minutes <= CACHE_MAX_AGE_MINUTES:
        print(f"\n  Loaded {len(emails)} emails from cache "
              f"(fetched {age_minutes} min ago).")
        print("  Press [F] to force a fresh fetch.")
    else:
        if emails and age_minutes is not None:
            print(f"\n  Cache is {age_minutes} min old. Fetching fresh...")
        else:
            print(f"\n  No cache found. Fetching {mode} emails...")
        emails, fetched_at = fetch_fresh(
            service, mode, cache_file, date_after, date_before
        )
        age_minutes = 0

    if not emails:
        print(f"\n  No {mode} emails found for this selection. 🎉")
        return

    grouped = group_by_sender(emails)
    senders_list = list(grouped.keys())
    print_bifurcation_table(grouped, mode, fetched_at, age_minutes)

    while True:
        print("\n" + "-" * 72)
        print(f"  {mode_label}")
        print("  # = act on sender | [A] Claude analysis (1–9 email senders) |"
              " [R] Redisplay | [F] Fresh fetch | [Q] Back to main menu")
        print("-" * 72)

        raw = input("  Your choice: ").strip().upper()

        if raw == "Q":
            print("\n  Returning to main menu...")
            break

        elif raw == "R":
            age_minutes = int(
                (datetime.now() - datetime.strptime(
                    fetched_at, "%Y-%m-%d %H:%M:%S")).total_seconds() // 60
            )
            print_bifurcation_table(grouped, mode, fetched_at, age_minutes)
            continue

        elif raw == "F":
            emails, fetched_at = fetch_fresh(
                service, mode, cache_file, date_after, date_before
            )
            age_minutes = 0
            grouped = group_by_sender(emails)
            senders_list = list(grouped.keys())
            print_bifurcation_table(grouped, mode, fetched_at, age_minutes)
            continue

        elif raw == "A":
            grouped, emails = run_claude_analysis(
                service, grouped, emails, fetched_at, cache_file, mode
            )
            senders_list = list(grouped.keys())
            print("\n  Returning to sender table...")
            age_minutes = int(
                (datetime.now() - datetime.strptime(
                    fetched_at, "%Y-%m-%d %H:%M:%S")).total_seconds() // 60
            )
            print_bifurcation_table(grouped, mode, fetched_at, age_minutes)
            continue

        try:
            sender_num = int(raw)
            if sender_num < 1 or sender_num > len(senders_list):
                print(f"  Enter a number between 1 and {len(senders_list)}.")
                continue
        except ValueError:
            print("  Invalid input. Enter a number, A, R, F, or Q.")
            continue

        selected_email = senders_list[sender_num - 1]
        selected_data  = grouped[selected_email]
        selected_emails = selected_data["emails"]

        print(f"\n  Selected: {selected_email}")
        print(f"  Emails from this sender: {len(selected_emails)}")

        print("\n  CHOOSE AN ACTION:")
        print("  [1] Preview — show all emails with date (option to skip some)")
        print("  [2] Delete All — move all to Trash")
        print("  [3] Mark All as Read")
        print("  [4] Back")
        print("-" * 72)

        action_raw = input("  Your action: ").strip()

        if action_raw == "1":
            skip_indices = preview_emails(selected_emails, selected_email)

            if len(selected_emails) - len(skip_indices) == 0:
                print("  All emails skipped. No action taken.")
                continue

            print("\n  NOW CHOOSE ACTION FOR NON-SKIPPED EMAILS:")
            print("  [2] Delete")
            print("  [3] Mark as Read")
            print("  [4] Cancel")
            sub = input("  Your action: ").strip()

            if sub == "4":
                print("  Cancelled.")
                continue

            if sub not in ["2", "3"]:
                print("  Invalid.")
                continue

            action = "delete" if sub == "2" else "read"
            remaining = len(selected_emails) - len(skip_indices)
            confirm = input(
                f"\n  Confirm: {action.upper()} {remaining} email(s) "
                f"from {selected_email}? (yes/no): "
            ).strip().lower()

            if confirm != "yes":
                print("  Cancelled.")
                continue

            execute_bulk_action(
                service, selected_emails, action,
                selected_email, skip_indices
            )

            if not DRY_RUN and len(skip_indices) == 0:
                del grouped[selected_email]
                senders_list = list(grouped.keys())
                emails = [e for e in emails
                          if e["sender_email"] != selected_email]
                save_cache(emails, cache_file)
                age_minutes = 0
                print_bifurcation_table(grouped, mode, fetched_at, age_minutes)

        elif action_raw == "2":
            confirm = input(
                f"\n  Confirm: trash ALL {len(selected_emails)} emails "
                f"from {selected_email}? (yes/no): "
            ).strip().lower()
            if confirm == "yes":
                execute_bulk_action(
                    service, selected_emails, "delete", selected_email
                )
                if not DRY_RUN:
                    del grouped[selected_email]
                    senders_list = list(grouped.keys())
                    emails = [e for e in emails
                              if e["sender_email"] != selected_email]
                    save_cache(emails, cache_file)
                    fetched_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    age_minutes = 0
                    print_bifurcation_table(grouped, mode, fetched_at, age_minutes)
            else:
                print("  Cancelled.")

        elif action_raw == "3":
            confirm = input(
                f"\n  Confirm: mark ALL {len(selected_emails)} emails "
                f"from {selected_email} as read? (yes/no): "
            ).strip().lower()
            if confirm == "yes":
                execute_bulk_action(
                    service, selected_emails, "read", selected_email
                )
                if not DRY_RUN:
                    del grouped[selected_email]
                    senders_list = list(grouped.keys())
                    emails = [e for e in emails
                              if e["sender_email"] != selected_email]
                    save_cache(emails, cache_file)
                    fetched_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    age_minutes = 0
                    print_bifurcation_table(grouped, mode, fetched_at, age_minutes)
            else:
                print("  Cancelled.")

        elif action_raw == "4":
            age_minutes = int(
                (datetime.now() - datetime.strptime(
                    fetched_at, "%Y-%m-%d %H:%M:%S")).total_seconds() // 60
            )
            print_bifurcation_table(grouped, mode, fetched_at, age_minutes)

        else:
            print("  Invalid. Enter 1, 2, 3, or 4.")


# ════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ════════════════════════════════════════════════════════════

def run():
    print("\n" + "=" * 72)
    print("  Gmail Inbox Cleaner")
    if DRY_RUN:
        print("  ⚠️  DRY RUN MODE — no emails will be modified")
    else:
        print("  🔴 LIVE MODE — actions will modify your real inbox")
    print("=" * 72)

    print("\n  Connecting to Gmail...")
    service = get_gmail_service()
    print("  ✅ Connected")

    while True:
        print("\n" + "=" * 72)
        print("  WHAT WOULD YOU LIKE TO CLEAN?")
        print("=" * 72)
        print("  [1] 📬 UNREAD emails  — bulk clean your unread inbox")
        print("  [2] 📂 READ emails    — clean up old read emails by time window")
        print("  [Q] Quit")
        print("=" * 72)

        choice = input("  Your choice (default 1): ").strip().upper()

        if choice == "Q":
            print("\n  Goodbye.")
            break

        elif choice == "2":
            date_after, date_before, window_label = select_time_window()
            # Use a cache file named after the window so different
            # windows don't overwrite each other
            safe_label = window_label.replace(" ", "_").replace("/", "-")
            cache_file = f"cache_read_{safe_label}.json"
            inbox_loop(
                service, mode="read",
                cache_file=cache_file,
                date_after=date_after,
                date_before=date_before,
                window_label=window_label
            )

        else:
            # Default: unread mode
            inbox_loop(
                service, mode="unread",
                cache_file=CACHE_UNREAD
            )


if __name__ == "__main__":
    run()