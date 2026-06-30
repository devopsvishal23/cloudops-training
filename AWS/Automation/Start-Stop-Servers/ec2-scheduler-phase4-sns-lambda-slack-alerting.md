# EC2 Auto Start/Stop — Phase 4: Ops Alerting via SNS + Lambda + Slack

## Overview

**Purpose:** Get real-time Slack notifications every time your EC2 instances are started or stopped by the Phase 1 scheduler — both success and failure.

**Services used:** Amazon SNS + AWS Lambda (Python 3.12) + Amazon EventBridge (event pattern) + Slack Incoming Webhook

**Channel:** `#devops-ops-alerts` (bot-only — no human chat in this channel)

**Cost:** $0.00/month — all services stay within AWS free tier at this usage volume

---

## Architecture

```
SSM Automation (stop/start EC2)
        ↓  fires a state-change event on completion
EventBridge Rule (event pattern — watches SSM execution status)
        ↓
SNS Topic (ec2-scheduler-alerts)
        ↓
Lambda Function (SNSToSlack)
        ↓  calls EC2 + SSM APIs to enrich the alert
#devops-ops-alerts (Slack)
```

> This is completely additive — your 4 existing Phase 1 EventBridge scheduled rules are untouched. This new EventBridge rule reacts to SSM events after they happen.

---

## Pre-requisites

Before starting:
- Phase 1 is complete and working (4 EventBridge scheduled rules, SSM stops/starts instances)
- You have a Slack workspace with a `#devops-ops-alerts` channel already created
- You are logged into the AWS Console in `ap-south-1` (Mumbai)

---

## Step 1 — Create Slack Incoming Webhook

1. Go to `https://api.slack.com/apps` in your browser
2. Click **Create New App** → **From scratch**
3. App name: `AWS-Ops-Alerts`
4. Select your workspace (Skyonix)
5. Click **Create App**
6. In the left sidebar click **Incoming Webhooks**
7. Toggle **Activate Incoming Webhooks** to **On**
8. Click **Add New Webhook to Workspace** at the bottom
9. In the channel dropdown, select `#devops-ops-alerts`
10. Click **Allow**
11. You are returned to the Incoming Webhooks page — scroll down to see your new webhook
12. Click **Copy** next to the webhook URL

> The webhook URL looks like: `https://hooks.slack.com/services/TXXXXXXXX/BXXXXXXXX/XXXXXXXXXXXXXXXXXXXXXXXX`
> Save this — you will paste it into the Lambda code in Step 4.

---

## Step 2 — Create SNS Topic

1. Go to **SNS → Topics → Create topic**
2. Type: **Standard**
3. Name: `ec2-scheduler-alerts`
4. Scroll to bottom → click **Create topic**
5. You land on the topic detail page — copy the **ARN** shown at the top

> ARN format: `arn:aws:sns:ap-south-1:YOUR_ACCOUNT_ID:ec2-scheduler-alerts`
> You will need this ARN in Step 5 when creating the EventBridge rule target.

---

## Step 3 — Create Lambda IAM Role Permissions

The Lambda function needs permissions to:
- Write logs to CloudWatch (basic execution)
- Call `ssm:GetAutomationExecution` (to look up which instance was involved)
- Call `ec2:DescribeInstances` (to look up the instance Name tag)

### Step 3.1 — Create inline policy

1. Go to **IAM → Roles**
2. Search for the role that was auto-created for your Lambda — it will be named something like `SNSToSlack-role-xxxxxxxx`. If you haven't created the Lambda yet, come back to this step after Step 4.
3. Click into the role → **Add permissions → Create inline policy**
4. Click **JSON** tab → paste:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ssm:GetAutomationExecution",
        "ec2:DescribeInstances"
      ],
      "Resource": "*"
    }
  ]
}
```

5. Policy name: `SNSToSlackSSMEC2Policy`
6. Click **Create policy**

> `AWSLambdaBasicExecutionRole` (for CloudWatch logging) is already attached automatically when Lambda creates the execution role — you do not need to add it manually.

---

## Step 4 — Create Lambda Function

> ⚠️ Critical: Use ONLY the plain AWS Console inline editor. Do NOT use the "Open in Visual Studio Code" button — it creates a hash-sync mechanism that causes deploy conflicts.

1. Go to **Lambda → Functions → Create function**
2. Select **Author from scratch**
3. Function name: `SNSToSlack`
4. Runtime: **Python 3.12**
5. Architecture: leave as default (x86_64 if shown, otherwise leave unchanged)
6. Permissions → leave as **Create a new role with basic Lambda permissions**
7. Click **Create function**
8. Wait for the green success banner

### Step 4.1 — Add the code

1. On the function page, click the **Code** tab
2. In the file explorer on the left, confirm the file is named `lambda_function.py` — click on it to open it
3. Select all existing code (Ctrl+A / Cmd+A) → delete it
4. Paste this exact code:

```python
import json
import urllib.request
import boto3
from datetime import datetime, timezone, timedelta

SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/YOUR_WEBHOOK_URL_HERE"

IST = timezone(timedelta(hours=5, minutes=30))

ssm = boto3.client('ssm', region_name='ap-south-1')
ec2 = boto3.client('ec2', region_name='ap-south-1')

def format_ist(time_str):
    if not time_str:
        return 'unknown'
    try:
        dt = datetime.strptime(time_str, "%b %d, %Y, %I:%M:%S %p")
        dt_utc = dt.replace(tzinfo=timezone.utc)
        dt_ist = dt_utc.astimezone(IST)
        return dt_ist.strftime("%b %d, %Y, %I:%M:%S %p IST")
    except Exception:
        return time_str

def get_instance_info(execution_id):
    instance_id = 'unknown'
    instance_name = 'unknown'

    try:
        response = ssm.get_automation_execution(AutomationExecutionId=execution_id)
        params = response['AutomationExecution'].get('Parameters', {})
        ids = params.get('InstanceId', [])
        if ids:
            instance_id = ids[0]
    except Exception as e:
        print(f"SSM lookup failed: {e}")
        return instance_id, instance_name

    try:
        ec2_response = ec2.describe_instances(InstanceIds=[instance_id])
        reservations = ec2_response.get('Reservations', [])
        if reservations:
            tags = reservations[0]['Instances'][0].get('Tags', [])
            for tag in tags:
                if tag['Key'] == 'Name':
                    instance_name = tag['Value']
                    break
    except Exception as e:
        print(f"EC2 name lookup failed: {e}")

    return instance_id, instance_name


def lambda_handler(event, context):
    for record in event['Records']:
        sns_data = record.get('Sns') or record.get('SNS')
        message_raw = sns_data['Message']

        try:
            message = json.loads(message_raw)
        except (json.JSONDecodeError, TypeError):
            message = {}

        detail = message.get('detail', {})

        status = detail.get('Status', 'Unknown')
        doc = detail.get('Definition', 'Unknown document')
        execution_id = detail.get('ExecutionId', '')
        start_time = format_ist(detail.get('StartTime', ''))
        end_time = format_ist(detail.get('EndTime', ''))

        instance_id, instance_name = get_instance_info(execution_id) if execution_id else ('unknown', 'unknown')

        emoji = "✅" if status == "Success" else "❌"
        action = "Stop" if "Stop" in doc else "Start" if "Start" in doc else doc

        text = (
            f"{emoji} EC2 {action} — {status}\n"
            f"Instance: `{instance_name}` (`{instance_id}`)\n"
            f"Started: {start_time}   Ended: {end_time}"
        )

        slack_payload = {"text": text}

        req = urllib.request.Request(
            SLACK_WEBHOOK_URL,
            data=json.dumps(slack_payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        urllib.request.urlopen(req)

    return {'statusCode': 200}
```

5. Replace `YOUR_WEBHOOK_URL_HERE` with the actual Slack webhook URL you copied in Step 1
6. Click **Deploy** (the button directly above the code editor area, NOT inside any VS Code panel)
7. Wait for the banner to say **"Changes deployed"** and confirm **Last modified** timestamp updates

> ⚠️ If you see a red banner saying "The provided project hash does not match the remote hash" — this means the VS Code sync panel is conflicting. Close that panel entirely and use only the plain console editor. See Errors section at the bottom for the fix.

### Step 4.2 — Add IAM permissions to the Lambda role

Now go back to Step 3 and complete it — the role now exists and can be found.

---

## Step 5 — Subscribe SNS to Lambda

1. Go to **SNS → Topics → ec2-scheduler-alerts**
2. Click the **Subscriptions** tab
3. Click **Create subscription**
4. Protocol: **AWS Lambda**
5. Endpoint: click the dropdown and select your `SNSToSlack` function
6. Click **Create subscription**
7. The subscription should immediately show **Status: Confirmed** — Lambda subscriptions do not require manual confirmation unlike email

> If you see a broken/pending subscription from an earlier attempt, select it → **Delete** before creating the new one. Having two subscriptions pointing to the same Lambda causes duplicate Slack messages.

---

## Step 6 — Create EventBridge Rule (SSM Status Watcher)

This rule watches for SSM Automation completion events and routes them to your SNS topic.

1. Go to **Amazon EventBridge → Rules → Create rule**
2. On the EventBridge home page you will see options: select **EventBridge Rule with event pattern** (the first option — this reacts to events, not a schedule)
3. Click **Create rule**

### Step 6.1 — Define rule detail

- Name: `SSM-Automation-StatusChange-Alert`
- Description: `Watch SSM Automation execution status and notify Slack via SNS`
- Event bus: `default`
- Rule type: **Rule with an event pattern** (already selected)
- Click **Next**

### Step 6.2 — Define event pattern

- Event source: **AWS services**
- AWS service: **Systems Manager**
- Event type: **EC2 Automation Execution Status-change Notification**

If the dropdowns don't give you this exact combination, select **Custom pattern (JSON editor)** and paste:

```json
{
  "source": ["aws.ssm"],
  "detail-type": ["EC2 Automation Execution Status-change Notification"],
  "detail": {
    "Status": ["Success", "Failed", "TimedOut", "Cancelled"]
  }
}
```

- Click **Next**

### Step 6.3 — Select target

- Target type: **AWS service**
- Select target: **SNS topic**
- Topic: select `ec2-scheduler-alerts`
- Click **Next**

### Step 6.4 — Tags

Skip → Click **Next**

### Step 6.5 — Review and create

- Review the event pattern and target
- Click **Create rule**

---

## Step 7 — Verify Instance Name Tags Exist

The Lambda looks up the instance's `Name` tag to include a readable name in the alert. If your instances don't have a Name tag, the alert will show `unknown` instead of a name.

1. Go to **EC2 → Instances**
2. Select each instance → **Tags tab** → confirm there is a tag with:
   - Key: `Name`
   - Value: something meaningful like `Nixace-Lab-1` or `Dev-Server-1`
3. If missing, click **Manage tags → Add tag** → add the Name tag → **Save**

---

## Step 8 — Test the Full Pipeline

Do not use the Lambda console Test button — it sends a synthetic event that doesn't match the real SSM event structure and will produce errors. Always test using a real SSM execution.

1. Go to **Systems Manager → Automation → Execute automation**
2. Search for and select `AWS-StartEC2Instance`
3. Execution mode: **Simple execution**
4. Input parameters:
   - `InstanceId`: one of your instance IDs
   - `AutomationAssumeRole`: `arn:aws:iam::YOUR_ACCOUNT_ID:role/SSMAutomationEC2Role`
5. Click **Execute**
6. Wait 15–30 seconds
7. Check `#devops-ops-alerts` in Slack

Expected result:
```
✅ EC2 Start — Success
Instance: `Dev-Server-1` (`i-0xxxxxxxxxxxxxxxxx`)
Started: Jun 30, 2026, 7:01:04 PM   Ended: Jun 30, 2026, 7:01:06 PM
```

---

## Errors Encountered During Setup (Real Errors — Real Fixes)

These are actual errors hit during this setup, documented so you don't repeat the debugging cycle.

---

### Error 1 — Lambda ImportModuleError

**Error message in CloudWatch logs:**
```
[ERROR] Runtime.ImportModuleError: Unable to import module 'lambda_function':
No module named 'lambda_function'
```

**Why it happens:**
Lambda expects the file to be named exactly `lambda_function.py` with the handler function named `lambda_handler`. If the file was renamed, or the **Handler** configuration field was changed, Lambda cannot find the entry point.

**Fix:**
1. Go to **Lambda → SNSToSlack → Code tab**
2. In the file explorer (left side), confirm the file is literally named `lambda_function.py` — not `index.py`, not `lambda_function (1).py`
3. Confirm the function is defined as `def lambda_handler(event, context):`
4. Go to **Configuration → General configuration** → confirm Handler field says exactly: `lambda_function.lambda_handler`
5. Click **Deploy** again

---

### Error 2 — Hash Conflict on Deploy (VS Code Sync)

**Error message (red banner on Lambda code page):**
```
Failed to update the function "SNSToSlack": The provided project hash
RJ8oZ/mDz/Am3fZHBicQBVOYxbdkC/aToKq5PosFb18= does not match the
remote hash a8K+7Q7bjU37ie/BYFkRlNmoikdqsbRv3mmiE1tOUZk=
```

**Why it happens:**
The **"Open in Visual Studio Code"** button in the Lambda console creates a hash-based sync between local VS Code and the deployed Lambda. If the remote function was edited directly in the console at any point, the hashes diverge and all future deploys from the VS Code panel are blocked.

**Fix:**
- Close the VS Code-integrated editor pane entirely
- Use only the plain inline Lambda console editor
- Click only the standard **Deploy** button (not inside the VS Code panel)
- If the error persists even in the plain console: select all code → delete → click Deploy (this resets the remote hash with a blank function) → paste your code back → click Deploy again

---

### Error 3 — KeyError: 'SNS' in Lambda

**Error message in CloudWatch logs:**
```
[ERROR] KeyError: 'SNS'
File "/var/task/lambda_function.py", line 8, in lambda_handler
    message = json.loads(record['SNS']['Message'])
```

**Why it happens:**
AWS uses `Sns` (capital S, lowercase ns) in some event payloads and `SNS` (all caps) in others. The Lambda console's built-in Test button uses the test template casing, which may differ from what real SNS-to-Lambda delivery sends. Code that assumes all-caps `SNS` breaks when the real event uses mixed-case `Sns`.

**Fix:**
Use `.get()` with a fallback for both casings:
```python
sns_data = record.get('Sns') or record.get('SNS')
```
This handles both formats without errors regardless of which one arrives.

> Never use the Lambda console Test button to validate this pipeline — always use a real SSM execution to trigger the real event chain.

---

### Error 4 — Slack alert shows "Unknown document — Unknown / Instance: unknown"

**Slack message received:**
```
❌ EC2 Unknown document — Unknown
Instance: unknown
```

**Why it happens:**
The Lambda code was trying to extract `DocumentName`, `Status`, and `Targets` from the top level of the SNS message JSON. But the real SSM EventBridge event nests everything inside a `detail` block, and uses `Definition` instead of `DocumentName`. The actual payload structure is:

```json
{
  "detail-type": "EC2 Automation Execution Status-change Notification",
  "source": "aws.ssm",
  "detail": {
    "Definition": "AWS-StopEC2Instance",
    "Status": "Success",
    "ExecutionId": "8f6800e5-d6e4-41de-a6da-52d6583e348f",
    "StartTime": "...",
    "EndTime": "..."
  }
}
```

**Fix:**
Extract from `detail` sub-object, and use the correct field name `Definition`:
```python
detail = message.get('detail', {})
status = detail.get('Status', 'Unknown')
doc = detail.get('Definition', 'Unknown document')
execution_id = detail.get('ExecutionId', '')
```

Also note: the `Targets` field with instance IDs does not exist in this event payload at all. Instance ID must be fetched separately via `ssm.get_automation_execution(ExecutionId)`.

---

### Error 5 — Slack alert shows correct status but "Instance: unknown"

**Slack message received:**
```
✅ EC2 Stop — Success
Document: AWS-StopEC2Instance
Instance: unknown
```

**Why it happens:**
The SSM Status-change event does not include the instance ID directly. It must be looked up by calling the SSM API using the `ExecutionId` from the event. Additionally, the Lambda execution role did not have `ssm:GetAutomationExecution` permission, so the lookup silently failed and returned `unknown`.

**Fix — two parts:**

Part 1: Add IAM permission to Lambda role:
```json
{
  "Effect": "Allow",
  "Action": [
    "ssm:GetAutomationExecution",
    "ec2:DescribeInstances"
  ],
  "Resource": "*"
}
```

Part 2: Add the lookup functions to Lambda code (included in the final code in Step 4).

---

## End Result

When your EventBridge scheduled rules fire every night at 9 PM IST and every morning at 10 AM IST, `#devops-ops-alerts` will receive one alert per instance per action:

```
✅ EC2 Stop — Success
Instance: `Dev-Server-1` (`i-0xxxxxxxxxxxxxxxxx`)
Started: Jul 01, 2026, 02:30:05 AM IST   Ended: Jul 01, 2026, 02:30:35 AM IST

✅ EC2 Stop — Success
Instance: `Dev-Server-2` (`i-0xxxxxxxxxxxxxxxxx`)
Started: Jul 01, 2026, 02:30:06 AM IST   Ended: Jul 01, 2026, 02:31:29 AM IST
```

And on failure:
```
❌ EC2 Stop — Failed
Instance: `Dev-Server-1` (`i-0xxxxxxxxxxxxxxxxx`)
Started: Jul 01, 2026, 02:30:05 AM IST   Ended: Jul 01, 2026, 02:30:10 AM IST
```

---

## Resources Created in This Phase

| Resource | Name | Service |
|---|---|---|
| Slack App | AWS-Ops-Alerts | Slack |
| Slack Webhook | #devops-ops-alerts | Slack |
| SNS Topic | ec2-scheduler-alerts | Amazon SNS |
| Lambda Function | SNSToSlack | AWS Lambda |
| IAM Inline Policy | SNSToSlackSSMEC2Policy | AWS IAM |
| EventBridge Rule | SSM-Automation-StatusChange-Alert | Amazon EventBridge |

---

## Channel Convention Reminder

`#devops-ops-alerts` is a **bot-only channel** — no human conversation in it.
When an alert fires and needs follow-up discussion, take the conversation to `#devops-general` and reference the alert.

This keeps alerts scannable. The moment people start replying inline in an alerts channel, it becomes noise and team members start muting it.
test

---

## Error 6 — Timestamps showing in UTC instead of IST

**Slack message received:**
```
✅ EC2 Stop — Success
Instance: `Jenkins-Pipeline` (`i-034f6d80f94fe6ca3`)
Started: Jun 30, 2026, 7:11:37 PM   Ended: Jun 30, 2026, 7:11:38 PM
```

**Why it happens:**
AWS stores and returns all timestamps in UTC. The `StartTime` and `EndTime` fields in the SSM event payload are UTC. Lambda has no awareness of your local timezone and does not convert automatically.

`7:11 PM UTC = 12:41 AM IST (UTC + 5:30)`

**Fix:**
Add a `format_ist()` conversion function and call it on both timestamps.

**Confirmed working result:**
```
✅ EC2 Stop — Success
Instance: `Jenkins-Pipeline` (`i-034f6d80f94fe6ca3`)
Started: Jul 01, 2026, 12:41:37 AM IST   Ended: Jul 01, 2026, 12:41:38 AM IST
```
This fix is already included in the final Lambda code in Step 4.
