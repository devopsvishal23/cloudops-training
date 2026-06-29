import sys
import json
import os
from datetime import datetime, timedelta
from gmail_client import (
    get_gmail_service,
    fetch_emails,
    group_by_sender,
    move_to_trash,
    mark_as_read,
    unstar_email
)
from classifier import categorize_emails

# ── SAFETY SWITCH ─────────────────────────────────────────
DRY_RUN = False
# ──────────────────────────────────────────────────────────

CACHE_UNREAD          = "cache_unread.json"
CACHE_STARRED         = "cache_starred.json"
CACHE_MAX_AGE_MINUTES = 30
PAGE_SIZE             = 20

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
    "1": ("Last 30 days",  30),
    "2": ("Last 6 months", 180),
    "3": ("Last 1 year",   365),
    "4": ("Last 3 years",  1095),
    "5": ("Last 5 years",  1825),
    "6": ("Everything",    None),
    "7": ("Custom range",  "custom"),
}

LARGE_WINDOW_THRESHOLD = 365


# ════════════════════════════════════════════════════════════
# CACHE HELPERS
# ════════════════════════════════════════════════════════════

def save_cache(emails, cache_file):
    cache = {
        "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "emails": emails
    }
    with open(cache_file, "w") as f:
        json.dump(cache, f)


def load_cache(cache_file):
    if not os.path.exists(cache_file):
        return None, None, None
    try:
        with open(cache_file, "r") as f:
            cache = json.load(f)
        fetched_at_str = cache["fetched_at"]
        fetched_at_dt  = datetime.strptime(fetched_at_str, "%Y-%m-%d %H:%M:%S")
        age_minutes    = int((datetime.now() - fetched_at_dt).total_seconds() // 60)
        return cache["emails"], fetched_at_str, age_minutes
    except Exception:
        return None, None, None


def fetch_fresh(service, mode, cache_file,
                date_after=None, date_before=None):
    print("\n  Fetching from Gmail...")
    emails = fetch_emails(service, mode=mode,
                          date_after=date_after, date_before=date_before)
    save_cache(emails, cache_file)
    fetched_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"  Fetched {len(emails)} emails. Cache saved.")
    return emails, fetched_at


def get_age(fetched_at_str):
    return int(
        (datetime.now() -
         datetime.strptime(fetched_at_str, "%Y-%m-%d %H:%M:%S")
         ).total_seconds() // 60
    )


# ════════════════════════════════════════════════════════════
# PAGINATED BIFURCATION TABLE
# ════════════════════════════════════════════════════════════

def print_page(senders_list, grouped, mode, page, fetched_at, age_minutes):
    total_senders = len(senders_list)
    total_pages   = max(1, (total_senders + PAGE_SIZE - 1) // PAGE_SIZE)
    start         = page * PAGE_SIZE
    end           = min(start + PAGE_SIZE, total_senders)
    total_emails  = sum(d["count"] for d in grouped.values())

    mode_icons = {
        "unread":  "📬 UNREAD",
        "read":    "📂 READ",
        "starred": "⭐ STARRED"
    }
    mode_label = mode_icons.get(mode, mode.upper())

    print("\n" + "=" * 72)
    print(f"  {mode_label}  |  Page {page + 1}/{total_pages}  "
          f"|  {total_senders} senders  |  {total_emails} emails")
    if fetched_at:
        age_str = f"({age_minutes} min ago)" if age_minutes is not None else ""
        stale   = "  ⚠️ STALE — press [F]" \
                  if age_minutes is not None \
                  and age_minutes > CACHE_MAX_AGE_MINUTES else ""
        print(f"  Fetched: {fetched_at} {age_str}{stale}")

    print(f"  {'#':<5} {'SENDER EMAIL':<40} {'NAME':<16} {'EMAILS':>6} {'⭐':>4}")
    print("=" * 72)

    for abs_idx in range(start, end):
        sender_email  = senders_list[abs_idx]
        data          = grouped[sender_email]
        name          = data["name"][:14] if data["name"] else "-"
        starred_count = data.get("starred_count", 0)
        star_str      = f"⭐{starred_count}" if starred_count > 0 else ""
        print(f"  {abs_idx + 1:<5} {sender_email[:38]:<40} "
              f"{name:<16} {data['count']:>6} {star_str:>4}")

    print("=" * 72)
    nav = []
    if page > 0:
        nav.append("[P] Prev")
    if page < total_pages - 1:
        nav.append("[N] Next")
    nav += ["[#] Jump", "[A] Claude", "[F] Refresh", "[Q] Back"]
    print("  " + "  |  ".join(nav))
    print("=" * 72)


# ════════════════════════════════════════════════════════════
# PREVIEW WITH DATE + SKIP
# ════════════════════════════════════════════════════════════

def preview_emails(emails, sender_email):
    """Show emails with date and starred flag. Returns indices to skip."""
    print(f"\n  {len(emails)} email(s) from {sender_email}")
    print("  " + "-" * 68)
    for i, email in enumerate(emails, 1):
        date_str  = f"[{email.get('date', '?')}]"
        star_flag = "⭐" if email.get("starred") else "  "
        subject   = email["subject"][:42]
        print(f"  {i:>3}. {star_flag} {date_str:<14}  {subject}")
    print("  " + "-" * 68)
    print("  ⭐ = starred (will be auto-protected from deletion)")

    print("\n  Enter numbers to SKIP/KEEP (e.g. 1,3) or press Enter for ALL:")
    raw = input("  Skip: ").strip()

    skip_indices = set()
    if raw:
        for part in raw.split(","):
            part = part.strip()
            if part.isdigit():
                idx = int(part)
                if 1 <= idx <= len(emails):
                    skip_indices.add(idx - 1)

    if skip_indices:
        print(f"\n  Keeping {len(skip_indices)} email(s):")
        for i in sorted(skip_indices):
            print(f"    ↩️  {emails[i]['subject'][:60]}")

    return skip_indices


# ════════════════════════════════════════════════════════════
# BULK ACTION EXECUTOR — starred emails are always protected
# ════════════════════════════════════════════════════════════

def execute_bulk_action(service, emails, action, label,
                        skip_indices=None, allow_starred=False):
    """
    Execute delete or mark-as-read on a list of emails.
    Starred emails are skipped automatically unless allow_starred=True
    (only True when explicitly in starred management mode).
    """
    if skip_indices is None:
        skip_indices = set()

    to_act        = []
    starred_skipped = []

    for i, email in enumerate(emails):
        if i in skip_indices:
            continue
        if email.get("starred") and not allow_starred:
            starred_skipped.append(email)
        else:
            to_act.append(email)

    # Warn about starred emails being protected
    if starred_skipped:
        print(f"\n  ⭐ Starred protection — skipping "
              f"{len(starred_skipped)} starred email(s):")
        for e in starred_skipped:
            print(f"     ⭐ {e.get('date', '?'):13}  {e['subject'][:52]}")

    total = len(to_act)
    if total == 0:
        print("  Nothing to action (all emails were starred or skipped).")
        return 0

    verb   = "trash" if action == "delete" else "mark as read"
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
            elif action == "unstar":
                if unstar_email(service, email["id"]):
                    success += 1
        else:
            success += 1

    label2 = "DRY RUN: Would have processed" if DRY_RUN else "Done:"
    skipped_note = (f"  {len(starred_skipped)} starred email(s) protected."
                    if starred_skipped else "")
    print(f"  {label2} {success}/{total} emails. {skipped_note}")
    return success


# ════════════════════════════════════════════════════════════
# SENDER ACTION HANDLER
# ════════════════════════════════════════════════════════════

def handle_sender(service, sender_email, grouped, emails,
                  cache_file, mode):
    selected_data   = grouped[sender_email]
    selected_emails = selected_data["emails"]
    starred_count   = selected_data.get("starred_count", 0)

    print(f"\n  Selected: {sender_email}")
    print(f"  Emails: {len(selected_emails)}", end="")
    if starred_count:
        print(f"  (⭐ {starred_count} starred — protected from deletion)", end="")
    print()

    # In starred mode show unstar option
    if mode == "starred":
        print("\n  CHOOSE AN ACTION:")
        print("  [1] Preview — show all emails with date (option to skip some)")
        print("  [2] Delete All — move all to Trash")
        print("  [3] Mark All as Read")
        print("  [4] Unstar All — remove star from all emails")
        print("  [5] Back")
        print("-" * 72)
        action_map = {"2": "delete", "3": "read", "4": "unstar"}
        back_key   = "5"
    else:
        print("\n  CHOOSE AN ACTION:")
        print("  [1] Preview — show all emails with date (option to skip some)")
        print("  [2] Delete All — move all to Trash")
        print("  [3] Mark All as Read")
        print("  [4] Back")
        if starred_count:
            print(f"  ⭐ Note: {starred_count} starred email(s) will be "
                  f"automatically skipped during delete/read actions.")
        print("-" * 72)
        action_map = {"2": "delete", "3": "read"}
        back_key   = "4"

    action_raw = input("  Your action: ").strip()

    if action_raw == back_key or action_raw not in (["1"] + list(action_map.keys())):
        if action_raw != back_key:
            print("  Invalid choice.")
        return grouped, emails

    # ── Preview with skip ────────────────────────────────────
    if action_raw == "1":
        skip_indices = preview_emails(selected_emails, sender_email)
        remaining    = len(selected_emails) - len(skip_indices)

        if remaining == 0:
            print("  All emails skipped. No action taken.")
            return grouped, emails

        if mode == "starred":
            print(f"\n  ACTION FOR {remaining} non-skipped email(s):")
            print("  [2] Delete  [3] Mark as Read  [4] Unstar  [5] Cancel")
            sub        = input("  Your action: ").strip()
            action_map2 = {"2": "delete", "3": "read", "4": "unstar"}
            if sub not in action_map2:
                print("  Cancelled.")
                return grouped, emails
            action = action_map2[sub]
        else:
            print(f"\n  ACTION FOR {remaining} non-skipped email(s):")
            print("  [2] Delete  [3] Mark as Read  [4] Cancel")
            sub = input("  Your action: ").strip()
            if sub not in ["2", "3"]:
                print("  Cancelled.")
                return grouped, emails
            action = "delete" if sub == "2" else "read"

        confirm = input(
            f"\n  Confirm: {action.upper()} {remaining} email(s) "
            f"from {sender_email}? (yes/no): "
        ).strip().lower()

        if confirm != "yes":
            print("  Cancelled.")
            return grouped, emails

        allow_starred = (mode == "starred")
        execute_bulk_action(service, selected_emails, action,
                            sender_email, skip_indices,
                            allow_starred=allow_starred)

        if not DRY_RUN and len(skip_indices) == 0:
            del grouped[sender_email]
            emails = [e for e in emails if e["sender_email"] != sender_email]
            save_cache(emails, cache_file)

        return grouped, emails

    # ── Direct bulk action (no preview) ─────────────────────
    action = action_map[action_raw]
    confirm = input(
        f"\n  Confirm: {action.upper()} ALL {len(selected_emails)} "
        f"email(s) from {sender_email}? (yes/no): "
    ).strip().lower()

    if confirm != "yes":
        print("  Cancelled.")
        return grouped, emails

    allow_starred = (mode == "starred")
    execute_bulk_action(service, selected_emails, action,
                        sender_email, allow_starred=allow_starred)

    if not DRY_RUN:
        del grouped[sender_email]
        emails = [e for e in emails if e["sender_email"] != sender_email]
        save_cache(emails, cache_file)

    return grouped, emails


# ════════════════════════════════════════════════════════════
# CLAUDE ANALYSIS
# ════════════════════════════════════════════════════════════

def run_claude_analysis(service, grouped, emails, fetched_at,
                        cache_file, mode):
    print("\n" + "=" * 72)
    print("  CLAUDE AI ANALYSIS — Senders with 1–9 emails")
    print("=" * 72)

    single_senders = {k: v for k, v in grouped.items() if v["count"] <= 9}
    total          = len(single_senders)

    if total == 0:
        print("\n  No senders with 9 or fewer emails found.")
        return grouped, emails

    est_cost    = total * 0.000001
    est_batches = (total + 19) // 20
    print(f"\n  Found {total} senders with 1–9 emails.")
    print(f"  Estimated cost: ${est_cost:.6f}  |  Batches: {est_batches}")

    confirm = input("\n  Proceed? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("  Cancelled.")
        return grouped, emails

    emails_to_classify = []
    for sender_email, data in single_senders.items():
        for email in data["emails"]:
            emails_to_classify.append({
                "id":           email["id"],
                "sender_email": sender_email,
                "sender_name":  data["name"],
                "subject":      email["subject"],
                "snippet":      email["snippet"],
                "date":         email.get("date", ""),
                "starred":      email.get("starred", False)
            })

    classified = categorize_emails(emails_to_classify)

    by_category = {}
    for item in classified:
        cat = item["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(item)

    print("\n" + "=" * 72)
    print("  ANALYSIS RESULTS")
    print("=" * 72)
    cat_list = []
    for idx, (cat, items) in enumerate(
        sorted(by_category.items(), key=lambda x: len(x[1]), reverse=True), 1
    ):
        emoji, rec     = CATEGORY_CONFIG.get(cat, ("  ", "Recommended: REVIEW"))
        starred_in_cat = sum(1 for i in items if i.get("starred"))
        star_note      = f"  (⭐{starred_in_cat} protected)" if starred_in_cat else ""
        print(f"  [{idx}] {emoji} {cat:<15} {len(items):>4} emails   "
              f"{rec}{star_note}")
        cat_list.append(cat)
    print("=" * 72)

    while True:
        print("\n  Enter CATEGORY NUMBER to act | [B] Back")
        cat_raw = input("  Your choice: ").strip().upper()

        if cat_raw == "B":
            break

        try:
            cat_num = int(cat_raw)
            if cat_num < 1 or cat_num > len(cat_list):
                print(f"  Enter 1–{len(cat_list)}.")
                continue
        except ValueError:
            print("  Invalid.")
            continue

        selected_cat   = cat_list[cat_num - 1]
        selected_items = by_category[selected_cat]
        emoji, rec     = CATEGORY_CONFIG.get(selected_cat, ("  ", ""))

        print(f"\n  {emoji} {selected_cat} — {len(selected_items)} emails")
        print("  " + "-" * 68)
        for i, item in enumerate(selected_items, 1):
            date_str  = f"[{item.get('date', '?')}]"
            star_flag = "⭐" if item.get("starred") else "  "
            print(f"  {i:>3}. {star_flag} {date_str:<14}  "
                  f"{item['sender_email'][:26]:<28}  {item['subject'][:18]}")
        print("  " + "-" * 68)
        print(f"  {rec}")
        print("  ⭐ Starred emails will be automatically protected during delete.")

        print("\n  [1] Delete All  [2] Mark All as Read  [3] Skip")
        action_raw = input("  Your choice: ").strip()

        if action_raw == "3":
            continue
        if action_raw not in ["1", "2"]:
            print("  Invalid.")
            continue

        action  = "delete" if action_raw == "1" else "read"
        confirm = input(
            f"\n  Confirm: {action.upper()} ALL {len(selected_items)} "
            f"{selected_cat} emails? (yes/no): "
        ).strip().lower()

        if confirm != "yes":
            print("  Cancelled.")
            continue

        email_objs = [
            {"id": item["email_id"], "starred": item.get("starred", False),
             "subject": item["subject"], "date": item.get("date", "")}
            for item in selected_items
        ]
        allow_starred = (mode == "starred")
        execute_bulk_action(service, email_objs, action,
                            f"{len(email_objs)} {selected_cat} senders",
                            allow_starred=allow_starred)

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
                sorted(by_category.items(),
                       key=lambda x: len(x[1]), reverse=True), 1
            ):
                emoji, rec = CATEGORY_CONFIG.get(cat, ("  ", ""))
                print(f"  [{idx}] {emoji} {cat:<15} {len(items):>4} emails   {rec}")
                cat_list.append(cat)
            print("=" * 72)

    return grouped, emails


# ════════════════════════════════════════════════════════════
# TIME WINDOW SELECTOR
# ════════════════════════════════════════════════════════════

def select_time_window():
    print("\n" + "=" * 72)
    print("  SELECT TIME WINDOW FOR READ EMAILS")
    print("=" * 72)
    for key, (label, days) in TIME_WINDOWS.items():
        warn = "  ⚠️  may take 30+ mins" \
               if isinstance(days, int) and days > LARGE_WINDOW_THRESHOLD else ""
        print(f"  [{key}] {label}{warn}")
    print("=" * 72)

    while True:
        choice = input("  Your choice: ").strip()
        if choice not in TIME_WINDOWS:
            print(f"  Enter 1–{len(TIME_WINDOWS)}.")
            continue

        label, days = TIME_WINDOWS[choice]

        if choice == "6":
            confirm = input(
                "\n  ⚠️  Fetching ALL emails may take 30–90 minutes. "
                "Continue? (yes/no): "
            ).strip().lower()
            if confirm != "yes":
                continue
            return None, None, "Everything"

        if choice == "7":
            print("\n  Format: YYYY/MM/DD")
            date_after  = input("  From: ").strip()
            date_before = input("  To:   ").strip()
            return date_after, date_before, f"{date_after} to {date_before}"

        date_after = (datetime.now() - timedelta(days=days)).strftime("%Y/%m/%d")

        if isinstance(days, int) and days > LARGE_WINDOW_THRESHOLD:
            confirm = input(
                f"\n  ⚠️  {label} may take 10–30 minutes. Continue? (yes/no): "
            ).strip().lower()
            if confirm != "yes":
                continue

        return date_after, None, label


# ════════════════════════════════════════════════════════════
# SHARED INBOX LOOP WITH PAGINATION
# ════════════════════════════════════════════════════════════

def inbox_loop(service, mode, cache_file,
               date_after=None, date_before=None, window_label=""):

    emails, fetched_at, age_minutes = load_cache(cache_file)

    if emails and age_minutes is not None and age_minutes <= CACHE_MAX_AGE_MINUTES:
        print(f"\n  Loaded {len(emails)} emails from cache "
              f"({age_minutes} min ago). [F] to force refresh.")
    else:
        if emails and age_minutes is not None:
            print(f"\n  Cache is {age_minutes} min old. Fetching fresh...")
        else:
            label = {
                "unread":  "unread",
                "read":    "read",
                "starred": "starred"
            }.get(mode, mode)
            print(f"\n  No cache. Fetching {label} emails...")
        emails, fetched_at = fetch_fresh(
            service, mode, cache_file, date_after, date_before
        )
        age_minutes = 0

    if not emails:
        mode_names = {
            "unread": "unread", "read": "read", "starred": "starred"
        }
        print(f"\n  No {mode_names.get(mode, mode)} emails found. 🎉")
        return

    grouped      = group_by_sender(emails)
    senders_list = list(grouped.keys())
    current_page = 0

    print_page(senders_list, grouped, mode,
               current_page, fetched_at, age_minutes)

    while True:
        raw = input("\n  Your choice: ").strip().upper()

        total_pages = max(1, (len(senders_list) + PAGE_SIZE - 1) // PAGE_SIZE)

        if raw == "N":
            if current_page < total_pages - 1:
                current_page += 1
            else:
                print("  Already on last page.")
            print_page(senders_list, grouped, mode,
                       current_page, fetched_at, get_age(fetched_at))
            continue

        if raw == "P":
            if current_page > 0:
                current_page -= 1
            else:
                print("  Already on first page.")
            print_page(senders_list, grouped, mode,
                       current_page, fetched_at, get_age(fetched_at))
            continue

        if raw == "Q":
            print("\n  Returning to main menu...")
            break

        if raw == "F":
            emails, fetched_at = fetch_fresh(
                service, mode, cache_file, date_after, date_before
            )
            grouped      = group_by_sender(emails)
            senders_list = list(grouped.keys())
            current_page = 0
            print_page(senders_list, grouped, mode,
                       current_page, fetched_at, 0)
            continue

        if raw == "A":
            grouped, emails = run_claude_analysis(
                service, grouped, emails, fetched_at, cache_file, mode
            )
            senders_list = list(grouped.keys())
            total_pages  = max(1, (len(senders_list) + PAGE_SIZE - 1) // PAGE_SIZE)
            current_page = min(current_page, total_pages - 1)
            print_page(senders_list, grouped, mode,
                       current_page, fetched_at, get_age(fetched_at))
            continue

        if raw == "#":
            try:
                num = int(input("  Enter sender number: ").strip())
                if 1 <= num <= len(senders_list):
                    sender_email    = senders_list[num - 1]
                    grouped, emails = handle_sender(
                        service, sender_email, grouped,
                        emails, cache_file, mode
                    )
                    senders_list = list(grouped.keys())
                    total_pages  = max(1, (len(senders_list) + PAGE_SIZE - 1) // PAGE_SIZE)
                    current_page = min(current_page, total_pages - 1)
                    print_page(senders_list, grouped, mode,
                               current_page, fetched_at, get_age(fetched_at))
                else:
                    print(f"  Enter 1–{len(senders_list)}.")
            except ValueError:
                print("  Invalid number.")
            continue

        # Direct sender number
        try:
            num = int(raw)
            if 1 <= num <= len(senders_list):
                sender_email    = senders_list[num - 1]
                grouped, emails = handle_sender(
                    service, sender_email, grouped,
                    emails, cache_file, mode
                )
                senders_list = list(grouped.keys())
                total_pages  = max(1, (len(senders_list) + PAGE_SIZE - 1) // PAGE_SIZE)
                current_page = min(current_page, total_pages - 1)
                print_page(senders_list, grouped, mode,
                           current_page, fetched_at, get_age(fetched_at))
            else:
                print(f"  Enter 1–{len(senders_list)}, N, P, #, A, F, or Q.")
        except ValueError:
            print("  Invalid. Enter a sender number, N, P, #, A, F, or Q.")


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
        print("  [3] ⭐ STARRED emails — review and manage starred emails")
        print("  [Q] Quit")
        print("=" * 72)
        print("  ⭐ Note: starred emails are always protected from deletion")
        print("     in modes 1 and 2. Use mode 3 to manage them explicitly.")
        print("=" * 72)

        choice = input("  Your choice (default 1): ").strip().upper()

        if choice == "Q":
            print("\n  Goodbye.")
            break

        elif choice == "2":
            date_after, date_before, window_label = select_time_window()
            safe_label = window_label.replace(" ", "_").replace("/", "-")
            cache_file = f"cache_read_{safe_label}.json"
            inbox_loop(
                service, mode="read",
                cache_file=cache_file,
                date_after=date_after,
                date_before=date_before,
                window_label=window_label
            )

        elif choice == "3":
            inbox_loop(
                service, mode="starred",
                cache_file=CACHE_STARRED
            )

        else:
            # Default: unread
            inbox_loop(service, mode="unread", cache_file=CACHE_UNREAD)


if __name__ == "__main__":
    run()