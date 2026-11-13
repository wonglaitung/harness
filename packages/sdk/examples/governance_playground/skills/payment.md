---
name: payment-agent
description: 手工测试用治理技能（付款）
tools:
  allowed: [pay:transfer]
governance:
  agent_id: payment-agent
  version: 1.0.0
  approved_by: "manual-test"
  business_intent: 执行放款
  owners:
    accountable: Tester
    technical: Tester
  material: true
  tools:
    - name: pay:transfer
      capability: payment
      idempotent: false
      constraints:
        required_fields: [amount]
        amount_field: amount
        max_amount: 1000000
  workflow:
    steps:
      - id: disburse
        tools: [pay:transfer]
  limits:
    max_tool_calls_per_run: 5
    max_calls_per_minute: 5
    max_tokens_per_run: 200000
  approval_required_for: [pay:transfer]
---

正文
