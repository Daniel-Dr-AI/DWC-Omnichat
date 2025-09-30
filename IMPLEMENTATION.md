

## Phase 3 Update — Escalation Improved
- Escalation now sends up to **3 alerts** (1/3, 2/3, 3/3) and then stops.
- Alerts only trigger when the last user message is older than `ESCALATE_AFTER_SECONDS` and there hasn't been a recent escalation.
- Resets on **claim** or **staff/manager reply** (escalated_count=0, escalated_at cleared).
