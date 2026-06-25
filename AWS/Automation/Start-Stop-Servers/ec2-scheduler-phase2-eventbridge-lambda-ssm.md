# EC2 Auto Start/Stop — Phase 2: EventBridge + Lambda + SSM (Tag-Based)

## Overview

**Use case:** 5–20 EC2 instances, tag-based targeting, scalable  
**Services used:** Amazon EventBridge + AWS Lambda (Python) + SSM Automation  
**Advantage:** One Lambda function handles any number of instances — just tag them

---

## Architecture

```
9:00 PM IST  →  EventBridge  →  Lambda (action=stop)  →  Find instances by tag  →  SSM Stop
10:00 AM IST →  EventBridge  →  Lambda (action=start) →  Find instances by tag  →  SSM Start
```

---

## IST to UTC Conversion

| IST Time | UTC Time | Purpose |
|---|---|---|
| 9:00 PM IST | 15:30 UTC | Stop instances |
| 10:00 AM IST | 04:30 UTC | Start instances |

> IST = UTC + 5:30

---

## Step 1 — Tag Your EC2 Instances

Go to **EC2 → Instances → Select instance → Tags → Manage tags**

Add tag to every instance you want scheduled:

| Key | Value |
|---|---|
| `AutoSchedule` | `true` |

> Any new instance tagged with `AutoSchedule=true` is automatically included — no rule changes needed.

---

## Step 2 — Create IAM Policy for SSM

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

## Step 3 — Create IAM Role for SSM

Go to **IAM → Roles → Create Role**

- Trusted entity: **AWS Service**
- Use case: **Systems Manager**
- Attach policy: `SSMAutomationEC2Policy`
- Role name: `SSMAutomationEC2Role`
- Click **Create role** → Copy the **Role ARN**

```
ARN format: arn:aws:iam::YOUR_ACCOUNT_ID:role/SSMAutomationEC2Role
```

---

## Step 4 — Create IAM Policy for Lambda

Go to **IAM → Policies → Create Policy → JSON tab** and paste:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "ssm:StartAutomationExecution",
        "iam:PassRole"
      ],
      "Resource": "*"
    }
  ]
}
```

- Policy name: `LambdaEC2SchedulerPolicy`
- Click **Create policy**

> `iam:PassRole` is required so Lambda can pass the SSM role ARN when triggering SSM Automation.

---

## Step 5 — Create IAM Role for Lambda

Go to **IAM → Roles → Create Role**

- Trusted entity: **AWS Service**
- Use case: **Lambda**
- Attach policies:
  - `LambdaEC2SchedulerPolicy` (created above)
  - `AWSLambdaBasicExecutionRole` (AWS managed — for CloudWatch logs)
- Role name: `LambdaEC2SchedulerRole`
- Click **Create role**

---

## Step 6 — Create Lambda Function

Go to **Lambda → Create function**

- Function name: `EC2Scheduler`
- Runtime: **Python 3.12**
- Execution role: **Use an existing role** → select `LambdaEC2SchedulerRole`
- Click **Create function**

In the **Code** tab, replace the default code with:

```python
import boto3

ec2 = boto3.client('ec2', region_name='ap-south-1')
ssm = boto3.client('ssm', region_name='ap-south-1')

SSM_ROLE_ARN = 'arn:aws:iam::YOUR_ACCOUNT_ID:role/SSMAutomationEC2Role'

def get_tagged_instances():
    response = ec2.describe_instances(
        Filters=[
            {'Name': 'tag:AutoSchedule', 'Values': ['true']},
            {'Name': 'instance-state-name', 'Values': ['running', 'stopped']}
        ]
    )
    instance_ids = []
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instance_ids.append(instance['InstanceId'])
    return instance_ids

def lambda_handler(event, context):
    action = event.get('action')  # 'stop' or 'start'
    instances = get_tagged_instances()

    if not instances:
        print("No tagged instances found.")
        return {'status': 'no instances found'}

    doc = 'AWS-StopEC2Instance' if action == 'stop' else 'AWS-StartEC2Instance'

    for instance_id in instances:
        ssm.start_automation_execution(
            DocumentName=doc,
            Parameters={'InstanceId': [instance_id]},
            AutomationAssumeRole=SSM_ROLE_ARN
        )
        print(f"{action.upper()} triggered via SSM for: {instance_id}")

    return {'status': 'success', 'action': action, 'instances': instances}
```

> Replace `YOUR_ACCOUNT_ID` and `ap-south-1` with your actual values.

- Click **Deploy**

### Test the Function

Click **Test** → Create a test event:

```json
{ "action": "stop" }
```

Verify your tagged instances stop. Then test with `{ "action": "start" }`.

---

## Step 7 — Create EventBridge Rule: Stop at 9 PM IST

Go to **EventBridge → Scheduled rules → Create rule**

### Rule Detail
- Name: `EC2-Stop-9PM-IST`
- Description: `Stop all AutoSchedule=true EC2 instances at 9 PM IST`
- Click **Next**

### Define Schedule
- Pattern: **A fine-grained schedule** (cron)

| Field | Value |
|---|---|
| Minutes | `30` |
| Hours | `15` |
| Day of month | `*` |
| Month | `*` |
| Day of week | `?` |
| Year | `*` |

Click **Next**

### Select Target
- Target type: **AWS service**
- Select target: **Lambda function**
- Function: `EC2Scheduler`
- Additional settings → Configure input → **Constant (JSON text)**:

```json
{"action": "stop"}
```

Click **Next** → Skip tags → **Create rule**

---

## Step 8 — Create EventBridge Rule: Start at 10 AM IST

Repeat Step 7 with:

- Name: `EC2-Start-10AM-IST`
- Cron:

| Field | Value |
|---|---|
| Minutes | `30` |
| Hours | `4` |
| Day of month | `*` |
| Month | `*` |
| Day of week | `?` |
| Year | `*` |

- Input:

```json
{"action": "start"}
```

---

## End Result — 2 Rules Only (Scales to Any Number of Instances)

| Rule Name | Cron (UTC) | Target | Input |
|---|---|---|---|
| `EC2-Stop-9PM-IST` | `cron(30 15 * * ? *)` | Lambda: EC2Scheduler | `{"action":"stop"}` |
| `EC2-Start-10AM-IST` | `cron(30 4 * * ? *)` | Lambda: EC2Scheduler | `{"action":"start"}` |

---

## Flow Summary

```
9:00 PM IST
EventBridge → Lambda (action=stop)
  → Find all EC2 with tag AutoSchedule=true
  → SSM: AWS-StopEC2Instance for each

10:00 AM IST
EventBridge → Lambda (action=start)
  → Find all EC2 with tag AutoSchedule=true
  → SSM: AWS-StartEC2Instance for each
```

---

## Advantages Over Phase 1

| Feature | Phase 1 (SSM Native) | Phase 2 (Lambda) |
|---|---|---|
| Rules needed | 4 (for 2 instances) | 2 (always) |
| Add new instance | Create 2 new rules | Just add tag |
| Logging | SSM execution logs only | CloudWatch + SSM logs |
| Error handling | None | Can add SNS/Slack alerts |
| Scale | Up to ~5 instances (manageable) | Unlimited |

---

## Optional: Add SNS Alert on Failure

In Lambda, wrap the for loop in try/except and publish to SNS:

```python
import json

sns = boto3.client('sns', region_name='ap-south-1')
SNS_TOPIC_ARN = 'arn:aws:sns:ap-south-1:YOUR_ACCOUNT_ID:EC2SchedulerAlerts'

try:
    ssm.start_automation_execution(...)
except Exception as e:
    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject=f'EC2 Scheduler Failed: {instance_id}',
        Message=str(e)
    )
```

> For 20+ instances at enterprise scale, move to **Phase 3: AWS Instance Scheduler**.
