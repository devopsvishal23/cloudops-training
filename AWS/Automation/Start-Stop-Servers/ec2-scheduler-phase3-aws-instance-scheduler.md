# EC2 Auto Start/Stop — Phase 3: AWS Instance Scheduler (Enterprise)

## Overview

**Use case:** 20+ instances, enterprise scale, multi-account, multi-region  
**Services used:** AWS-provided CloudFormation solution (no custom code)  
**Maintained by:** AWS — updated and supported officially  
**Official page:** https://aws.amazon.com/solutions/implementations/instance-scheduler-on-aws/

---

## Architecture

```
DynamoDB (Schedule Config)
        ↓
EventBridge → Lambda (AWS-managed) → EC2 / RDS
        ↑
Tagged instances (Schedule=office-hours)
```

> Everything is deployed by CloudFormation. You only configure DynamoDB schedules and tag your instances.

---

## What It Supports

- EC2 and RDS instances
- Multiple schedules (office hours, weekends-off, etc.)
- Multiple AWS accounts and regions (hub-spoke model)
- Timezone-aware scheduling (supports IST natively — no UTC conversion needed)
- Custom periods (e.g., Mon–Fri only, skip holidays)

---

## Step 1 — Deploy CloudFormation Stack

### 1.1 — Get the Template

Go to the official AWS Solutions page:  
https://aws.amazon.com/solutions/implementations/instance-scheduler-on-aws/

Click **Launch in the AWS Console** or download the CloudFormation template.

### 1.2 — Deploy the Stack

Go to **CloudFormation → Create stack → With new resources**

- Template source: **Amazon S3 URL** (paste the URL from the solutions page)
- Click **Next**

### 1.3 — Configure Stack Parameters

| Parameter | Value |
|---|---|
| Stack name | `EC2-Instance-Scheduler` |
| Regions | `ap-south-1` (Mumbai) |
| Default timezone | `Asia/Kolkata` |
| Schedule EC2 instances | `Yes` |
| Schedule RDS instances | `Yes` (or No if not needed) |
| Create RDS snapshot before stop | `Yes` (recommended) |
| Frequency | `5` (checks every 5 minutes) |
| Started tags | `ScheduleMessage=Started by scheduler` |
| Stopped tags | `ScheduleMessage=Stopped by scheduler` |

- Click **Next** → Skip tags → **Create stack**

Wait for stack status: `CREATE_COMPLETE` (~5 minutes)

---

## Step 2 — Configure a Schedule in DynamoDB

The stack creates a DynamoDB table named `EC2-Instance-Scheduler-ConfigTable` (or similar).

Go to **DynamoDB → Tables → find the config table → Explore items**

### 2.1 — Create a Period

A **period** defines a time window (e.g., 10 AM to 9 PM).

Click **Create item** → Switch to JSON view → paste:

```json
{
  "type": { "S": "period" },
  "name": { "S": "office-hours" },
  "begintime": { "S": "10:00" },
  "endtime": { "S": "21:00" },
  "weekdays": { "SS": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"] }
}
```

> `begintime` = start (10:00 AM IST), `endtime` = stop (9:00 PM IST)  
> Timezone is IST because we set `Asia/Kolkata` as default in the stack.

Click **Create item**

### 2.2 — Create a Schedule

A **schedule** references one or more periods.

Click **Create item** → JSON view → paste:

```json
{
  "type": { "S": "schedule" },
  "name": { "S": "office-hours" },
  "periods": { "SS": ["office-hours"] },
  "timezone": { "S": "Asia/Kolkata" }
}
```

Click **Create item**

---

## Step 3 — Tag Your EC2 Instances

Go to **EC2 → Instances → Select instance → Tags → Manage tags**

Add this tag to every instance you want scheduled:

| Key | Value |
|---|---|
| `Schedule` | `office-hours` |

> The tag value must match the schedule name you created in DynamoDB.  
> Any instance with `Schedule=office-hours` is automatically included.

---

## Step 4 — Verify

The scheduler Lambda runs every 5 minutes (based on Frequency set during deploy).

Within 5 minutes of 10:00 AM IST → instances with `Schedule=office-hours` will start  
Within 5 minutes of 9:00 PM IST → instances will stop

### Check Logs

Go to **CloudWatch → Log groups** → find `/aws/lambda/EC2-Instance-Scheduler-*`

Logs will show which instances were started/stopped and why.

---

## Common Schedule Examples

### Weekdays Only (Mon–Fri)

```json
{
  "type": { "S": "period" },
  "name": { "S": "weekdays-only" },
  "begintime": { "S": "10:00" },
  "endtime": { "S": "21:00" },
  "weekdays": { "SS": ["mon", "tue", "wed", "thu", "fri"] }
}
```

### Always Off (for dev instances over weekend)

```json
{
  "type": { "S": "schedule" },
  "name": { "S": "weekdays-only" },
  "periods": { "SS": ["weekdays-only"] },
  "timezone": { "S": "Asia/Kolkata" }
}
```

Tag weekend-only instances: `Schedule=weekdays-only`

---

## Multiple Schedules Example

| Schedule Name | Period | Use Case |
|---|---|---|
| `office-hours` | 10 AM – 9 PM, all days | Dev/test instances |
| `weekdays-only` | 10 AM – 9 PM, Mon–Fri | QA instances |
| `always-on` | No stop | Production instances |

Each instance gets a `Schedule` tag pointing to the right schedule name.

---

## Advantages Over Phase 1 and Phase 2

| Feature | Phase 1 (SSM Native) | Phase 2 (Lambda) | Phase 3 (Instance Scheduler) |
|---|---|---|---|
| Code required | None | ~30 lines Python | None |
| Scale | 1–5 instances | 5–20 instances | Unlimited |
| Multi-account | No | Manual | Yes (hub-spoke) |
| Multi-region | No | Manual | Yes |
| RDS support | No | No | Yes |
| Timezone support | Manual UTC conversion | Manual UTC conversion | Native (IST, etc.) |
| Maintained by | You | You | AWS |
| Schedule flexibility | Fixed cron only | Fixed cron only | Periods, weekdays, holidays |

---

## Cleanup — Delete Stack

To remove everything:

Go to **CloudFormation → Stacks → EC2-Instance-Scheduler → Delete**

This removes the Lambda, EventBridge rules, DynamoDB table, and IAM roles created by the solution.

---

## Learning Path Reference

```
Phase 1 (Beginner)   → EventBridge + SSM Native     (1–5 instances, no code)
Phase 2 (Intermediate) → EventBridge + Lambda + SSM  (5–20 instances, tag-based)
Phase 3 (Enterprise) → AWS Instance Scheduler        (20+ instances, multi-account)
```
