# EC2 Auto Start/Stop — Overview & Decision Guide

## What Is This?

This document explains how to automatically stop and start EC2 instances on a schedule to save costs — for example, shutting down dev/test servers at night and starting them again in the morning.

Three approaches are documented here, each suited to a different scale and complexity level.

---

## The Problem

EC2 instances cost money even when idle. Dev, test, and UAT environments typically don't need to run 24/7. A simple stop/start schedule on non-production instances can cut EC2 costs by 50–65% depending on your working hours.

**Example (9 AM – 9 PM schedule, 12 hrs/day):**
- Without schedule: 730 hours/month billed
- With schedule: ~365 hours/month billed
- **Saving: ~50%**

---

## IST ↔ UTC Reference

All AWS scheduling uses UTC. India Standard Time (IST) = UTC + 5:30.

| IST | UTC | Common Use |
|---|---|---|
| 9:00 AM IST | 03:30 UTC | Start instances (morning) |
| 10:00 AM IST | 04:30 UTC | Start instances (morning) |
| 6:00 PM IST | 12:30 UTC | Stop instances (evening) |
| 9:00 PM IST | 15:30 UTC | Stop instances (night) |

> Exception: AWS Instance Scheduler (Phase 3) supports IST natively — no UTC conversion needed.

---

## The 3 Options at a Glance

| | Phase 1 | Phase 2 | Phase 3 |
|---|---|---|---|
| **Approach** | EventBridge + SSM Native | EventBridge + Lambda + SSM | AWS Instance Scheduler |
| **Code required** | None | ~30 lines Python | None |
| **Best for** | 1–5 instances | 5–20 instances | 20+ instances / enterprise |
| **Targeting** | Per instance ID | Tag-based | Tag-based |
| **Rules needed** | 4 rules per 2 instances | 2 rules always | 0 rules (DynamoDB config) |
| **Add new instance** | Create 2 new rules | Add a tag | Add a tag |
| **Multi-account** | No | Manual | Yes |
| **Multi-region** | No | Manual | Yes |
| **RDS support** | No | No | Yes |
| **Timezone support** | Manual UTC conversion | Manual UTC conversion | Native (IST etc.) |
| **Maintained by** | You | You | AWS |
| **Complexity** | Low | Medium | Low (AWS manages it) |

---

## When to Use Which

### Use Phase 1 — EventBridge + SSM Native if:
- You have 1 to 5 instances
- You want zero code and zero Lambda
- This is for learning, research, or a small personal project
- Instance count is fixed and rarely changes

📄 See: [ec2-scheduler-phase1-eventbridge-ssm-native.md](./ec2-scheduler-phase1-eventbridge-ssm-native.md)

---

### Use Phase 2 — EventBridge + Lambda + SSM if:
- You have 5 to 20 instances
- You want tag-based targeting (auto-include new instances by just tagging)
- You need CloudWatch logging and optional alerting (SNS/Slack)
- You want one solution that scales without creating new rules each time

📄 See: [ec2-scheduler-phase2-eventbridge-lambda-ssm.md](./ec2-scheduler-phase2-eventbridge-lambda-ssm.md)

---

### Use Phase 3 — AWS Instance Scheduler if:
- You have 20+ instances across multiple accounts or regions
- You need to schedule RDS instances as well
- You want timezone-aware scheduling without UTC math
- You want a fully AWS-maintained solution with no custom code
- You need advanced periods (weekdays only, skip holidays, multiple time windows)

📄 See: [ec2-scheduler-phase3-aws-instance-scheduler.md](./ec2-scheduler-phase3-aws-instance-scheduler.md)

---

## Industry Best Practice (Production Reality)

Most production DevOps teams use **Phase 2 (Lambda-based)** as the default — not because Phase 1 can't work, but because:

- Tag-based targeting gives flexibility — stop all `env=dev` instances in one shot
- New instances are auto-included just by adding a tag — no rule changes needed
- Lambda adds logging, error handling, and notification hooks (SNS, Slack)
- One function handles 2 or 200 instances the same way
- The Lambda itself is a tiny ~30-line Python function — not significant overhead

Phase 3 (Instance Scheduler) is used when the team manages dozens of accounts and needs a governed, auditable, AWS-supported scheduling solution.

---

## Recommended Learning Path

If you are learning this for the first time, go in order:

```
Phase 1  →  Understand the native AWS flow, no code involved
    ↓
Phase 2  →  Feel the limitation of Phase 1, appreciate why Lambda is added
    ↓
Phase 3  →  Understand enterprise-scale scheduling patterns
```

Starting with Phase 1 gives you the foundation. You will naturally understand why Lambda is needed once you experience the limitation of managing per-instance rules manually.

---

## Services Involved (Quick Reference)

| Service | Role |
|---|---|
| **Amazon EventBridge** | Cron-based scheduler — triggers the automation at set times |
| **AWS Systems Manager (SSM)** | Executes `AWS-StopEC2Instance` and `AWS-StartEC2Instance` built-in documents |
| **AWS Lambda** | (Phase 2 only) Bridge between EventBridge and SSM, handles tag-based discovery |
| **Amazon DynamoDB** | (Phase 3 only) Stores schedule and period configuration |
| **AWS IAM** | Roles and policies that give SSM/Lambda permission to act on EC2 |
| **Amazon CloudWatch** | Logs for Lambda execution and SSM automation runs |

---

## Folder Structure

```
ec2-scheduling/
├── README.md                                          ← You are here
├── ec2-scheduler-phase1-eventbridge-ssm-native.md    ← Phase 1 full guide
├── ec2-scheduler-phase2-eventbridge-lambda-ssm.md    ← Phase 2 full guide
└── ec2-scheduler-phase3-aws-instance-scheduler.md    ← Phase 3 full guide
```
