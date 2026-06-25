# EC2 Auto Start/Stop — Phase 1: EventBridge + SSM Native (No Code)

## Overview

**Use case:** 1–5 EC2 instances, no custom code, 100% AWS native  
**Services used:** Amazon EventBridge (Scheduled Rules) + AWS Systems Manager (SSM) Automation  
**Cost:** Free (within AWS Free Tier limits for EventBridge and SSM)

---

## Architecture

```
9:00 PM IST  →  EventBridge Scheduled Rule  →  SSM Automation (AWS-StopEC2Instance)  →  EC2
10:00 AM IST →  EventBridge Scheduled Rule  →  SSM Automation (AWS-StartEC2Instance) →  EC2
```

> **Limitation:** SSM Automation via EventBridge accepts one Instance ID per rule.  
> For 2 instances you will create 4 rules total (2 stop + 2 start).

---

## IST to UTC Conversion

| IST Time | UTC Time | Purpose |
|---|---|---|
| 9:00 PM IST | 15:30 UTC | Stop instances |
| 10:00 AM IST | 04:30 UTC | Start instances |

> IST = UTC + 5:30

---

## Pre-requisite — Note Your Instance IDs

Go to **EC2 → Instances** and note down both instance IDs:

```
Instance 1: i-0xxxxxxxxxxxxxxxxx
Instance 2: i-0xxxxxxxxxxxxxxxxx
```

---

## Step 1 — Create IAM Policy for SSM

Go to **IAM → Policies → Create Policy → JSON tab** and paste:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:StopInstances",
        "ec2:StartInstances",
        "ec2:DescribeInstances",
        "ec2:DescribeInstanceStatus"
      ],
      "Resource": "*"
    }
  ]
}
```

- Policy name: `SSMAutomationEC2Policy`
- Click **Create policy**

---

## Step 2 — Create IAM Role for SSM

Go to **IAM → Roles → Create Role**

- Trusted entity: **AWS Service**
- Use case: **Systems Manager**
- Attach policy: `SSMAutomationEC2Policy` (the one you just created)
- Role name: `SSMAutomationEC2Role`
- Click **Create role**

After creation, click into the role and **copy the Role ARN**. You will need it in Step 4.

```
ARN format: arn:aws:iam::YOUR_ACCOUNT_ID:role/SSMAutomationEC2Role
```

---

## Step 3 — Test SSM Document Manually First

Before scheduling, verify SSM can actually stop your instance.

Go to **Systems Manager → Automation → Execute automation**

- Search document: `AWS-StopEC2Instance`
- Click on it → **Execute automation**
- Execution mode: **Simple execution**
- Input parameters:
  - `InstanceId`: your Instance 1 ID
  - `AutomationAssumeRole`: paste the Role ARN from Step 2
- Click **Execute**

Check EC2 console — instance should stop.

Then repeat with `AWS-StartEC2Instance` to bring it back.

> This confirms SSM has correct permissions before adding the schedule.

---

## Step 4 — Create EventBridge Rule: Stop Instance 1 at 9 PM IST

Go to **EventBridge → Scheduled rules → Create rule**

### Step 4.1 — Define Rule Detail
- Name: `EC2-Stop-9PM-IST-Instance1`
- Description: `Stop EC2 Instance 1 at 9 PM IST daily`
- Click **Next**

### Step 4.2 — Define Schedule
- Pattern: **A fine-grained schedule** (cron)
- Cron fields:

| Field | Value |
|---|---|
| Minutes | `30` |
| Hours | `15` |
| Day of month | `*` |
| Month | `*` |
| Day of week | `?` |
| Year | `*` |

- Verify **Next 10 trigger dates** appear → Click **Next**

### Step 4.3 — Select Target
- Target type: **AWS service**
- Select target: **SSM Automation**
- Document: `AWS-StopEC2Instance`
- Input parameters:
  - `InstanceId`: your Instance 1 ID
  - `AutomationAssumeRole`: `arn:aws:iam::YOUR_ACCOUNT_ID:role/SSMAutomationEC2Role`

> ⚠️ The `AutomationAssumeRole` ARN field is mandatory. If left blank, the rule will fail with error:  
> *"The Automation definition for an SSM Automation target must contain an AssumeRole that evaluates to an IAM role ARN."*

- Click **Next**

### Step 4.4 — Tags
Skip → Click **Next**

### Step 4.5 — Review and Create
Click **Create rule**

---

## Step 5 — Create EventBridge Rule: Stop Instance 2 at 9 PM IST

Repeat Step 4 exactly with:
- Name: `EC2-Stop-9PM-IST-Instance2`
- Same cron: `30 15 * * ? *`
- Same target: `AWS-StopEC2Instance`
- `InstanceId`: your Instance 2 ID
- Same `AutomationAssumeRole` ARN

---

## Step 6 — Create EventBridge Rule: Start Instance 1 at 10 AM IST

### Step 6.1 — Define Rule Detail
- Name: `EC2-Start-10AM-IST-Instance1`
- Description: `Start EC2 Instance 1 at 10 AM IST daily`
- Click **Next**

### Step 6.2 — Define Schedule
- Cron fields:

| Field | Value |
|---|---|
| Minutes | `30` |
| Hours | `4` |
| Day of month | `*` |
| Month | `*` |
| Day of week | `?` |
| Year | `*` |

### Step 6.3 — Select Target
- Target type: **AWS service**
- Select target: **SSM Automation**
- Document: `AWS-StartEC2Instance`
- Input parameters:
  - `InstanceId`: your Instance 1 ID
  - `AutomationAssumeRole`: `arn:aws:iam::YOUR_ACCOUNT_ID:role/SSMAutomationEC2Role`
- Click **Next** → Skip tags → **Create rule**

---

## Step 7 — Create EventBridge Rule: Start Instance 2 at 10 AM IST

Repeat Step 6 exactly with:
- Name: `EC2-Start-10AM-IST-Instance2`
- `InstanceId`: your Instance 2 ID
- Same `AutomationAssumeRole` ARN

---

## End Result — 4 Rules Total

| Rule Name | Cron (UTC) | SSM Document | Instance |
|---|---|---|---|
| `EC2-Stop-9PM-IST-Instance1` | `cron(30 15 * * ? *)` | AWS-StopEC2Instance | Instance 1 |
| `EC2-Stop-9PM-IST-Instance2` | `cron(30 15 * * ? *)` | AWS-StopEC2Instance | Instance 2 |
| `EC2-Start-10AM-IST-Instance1` | `cron(30 4 * * ? *)` | AWS-StartEC2Instance | Instance 1 |
| `EC2-Start-10AM-IST-Instance2` | `cron(30 4 * * ? *)` | AWS-StartEC2Instance | Instance 2 |

---

## Flow Summary

```
9:00 PM IST
EventBridge Rule 1 → SSM → Stop Instance 1
EventBridge Rule 2 → SSM → Stop Instance 2

10:00 AM IST
EventBridge Rule 3 → SSM → Start Instance 1
EventBridge Rule 4 → SSM → Start Instance 2
```

---

## Limitation of This Approach

- One rule per instance — does not scale beyond 5 instances
- Adding a new instance requires creating 2 new EventBridge rules manually
- No tag-based targeting support natively

> For 5–20 instances, move to **Phase 2: EventBridge + Lambda + SSM (tag-based)**.
