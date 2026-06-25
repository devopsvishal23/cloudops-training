# EC2 Auto Start/Stop — Cost Analysis

## Overview

The scheduling solution itself (EventBridge + SSM) costs nothing. The only financial impact is the money you **save** on EC2 runtime by not running instances when they are not needed.

---

## Solution Cost — EventBridge + SSM Native (Phase 1)

### 1. Amazon EventBridge (Scheduled Rules)

**Free tier:** First 5 million events/month at no charge.

| Metric | Value |
|---|---|
| Rules created | 4 |
| Triggers per rule per day | 1 |
| Total events per month | 4 × 30 = **120 events** |
| Free tier limit | 5,000,000 events |
| **Monthly cost** | **$0.00** |

---

### 2. AWS Systems Manager — SSM Automation

**Free tier:** First 1,000 Automation steps/month at no charge.

| Metric | Value |
|---|---|
| SSM executions per day | 4 (2 stop + 2 start) |
| Steps per execution | 1 |
| Total steps per month | 4 × 30 = **120 steps** |
| Free tier limit | 1,000 steps |
| **Monthly cost** | **$0.00** |

---

### 3. AWS Lambda

Not used in Phase 1.  
**Monthly cost: $0.00**

---

## Solution Cost — EventBridge + Lambda + SSM (Phase 2)

### Lambda (additional cost vs Phase 1)

**Free tier:** 1 million requests/month and 400,000 GB-seconds compute free.

| Metric | Value |
|---|---|
| Lambda invocations per day | 2 (1 stop + 1 start) |
| Total invocations per month | 2 × 30 = **60 invocations** |
| Free tier limit | 1,000,000 invocations |
| Avg execution duration | ~2 seconds |
| Memory | 128 MB |
| GB-seconds used | 60 × 2 × 0.125 = **15 GB-seconds** |
| Free tier limit | 400,000 GB-seconds |
| **Monthly cost** | **$0.00** |

---

## Total Monthly Cost by Phase

| Phase | EventBridge | SSM | Lambda | **Total** |
|---|---|---|---|---|
| Phase 1 — SSM Native | $0.00 | $0.00 | N/A | **$0.00** |
| Phase 2 — Lambda | $0.00 | $0.00 | $0.00 | **$0.00** |
| Phase 3 — Instance Scheduler | $0.00 | $0.00 | $0.00* | **$0.00** |

> *Phase 3 Lambda is AWS-managed and also falls within free tier for typical usage.

**All three phases cost $0.00/month within normal usage.**

---

## EC2 Savings — What You Actually Gain

This is where the real value is. By stopping instances overnight and on weekends, you reduce billed hours significantly.

### Schedule Assumed
- **Start:** 10:00 AM IST daily
- **Stop:** 9:00 PM IST daily
- **Runtime per day:** 11 hours (down from 24)

### Savings Per Instance Type (Mumbai — ap-south-1, On-Demand)

| Instance Type | On-Demand Rate | Without Schedule | With Schedule | Monthly Saving |
|---|---|---|---|---|
| t3.micro | $0.0116/hr | $8.35 | $3.83 | **$4.52** |
| t3.small | $0.0232/hr | $16.70 | $7.66 | **$9.04** |
| t3.medium | $0.0464/hr | $33.41 | $15.31 | **$18.10** |
| t3.large | $0.0928/hr | $66.82 | $30.62 | **$36.20** |
| m5.large | $0.1100/hr | $79.20 | $36.30 | **$42.90** |
| m5.xlarge | $0.2200/hr | $158.40 | $72.60 | **$85.80** |

> Rates are approximate. Check https://aws.amazon.com/ec2/pricing/on-demand/ for current pricing.

---

### Savings for Your Setup (2 Instances)

Example using `t3.medium` for both instances:

| | Without Schedule | With Schedule |
|---|---|---|
| Hours/day per instance | 24 hrs | 11 hrs |
| Hours/month per instance | 720 hrs | 330 hrs |
| Cost per instance/month | ~$33.41 | ~$15.31 |
| Cost for 2 instances/month | ~$66.82 | ~$30.62 |
| **Monthly saving** | | **~$36.20** |
| **Annual saving** | | **~$434.40** |

---

## Saving by Schedule Type

| Schedule | Runtime/Day | Hours/Month | % Saving vs 24x7 |
|---|---|---|---|
| 24x7 (no schedule) | 24 hrs | 720 hrs | 0% |
| 10 AM – 9 PM (11 hrs) | 11 hrs | 330 hrs | **54%** |
| 9 AM – 6 PM weekdays only | 9 hrs | ~180 hrs | **75%** |
| 10 AM – 9 PM weekdays only | 11 hrs | ~220 hrs | **69%** |

---

## Key Takeaway

> The scheduling solution costs **$0.00/month** to run.  
> It saves you **40–75% on EC2 costs** depending on your schedule.  
> For dev/test environments, this is the easiest cost optimisation available in AWS.

---

## References

- EventBridge Pricing: https://aws.amazon.com/eventbridge/pricing/
- SSM Pricing: https://aws.amazon.com/systems-manager/pricing/
- Lambda Pricing: https://aws.amazon.com/lambda/pricing/
- EC2 On-Demand Pricing (Mumbai): https://aws.amazon.com/ec2/pricing/on-demand/
