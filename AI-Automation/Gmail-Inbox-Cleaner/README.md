Your Gmail Inbox
      ↓
Gmail API (fetches emails in batches)
      ↓
Claude (reads each email, decides: KEEP or DELETE)
      ↓
Gmail API (moves DELETE emails to Trash)
      ↓
Log file (shows you exactly what happened)

Note: Your script will never permanently delete anything. Every "delete" is a move to Trash, which Gmail keeps for 30 days before auto-purging.



PHASE 1 CHECKLIST (7 Steps)
[ ] STEP 1 — Create your project folder and Python environment
[ ] STEP 2 — Create your Google Cloud Project
[ ] STEP 3 — Enable the Gmail API
[ ] STEP 4 — Configure the OAuth Consent Screen
[ ] STEP 5 — Create OAuth Credentials and download credentials.json
[ ] STEP 6 — Get your Anthropic API Key and create .env file
[ ] STEP 7 — Install Python dependencies
[ ] STEP 8 — Create the three core Python files
[ ] STEP 9 — Run the first dry-run test





STEP 2 — Create Your Google Cloud Project
