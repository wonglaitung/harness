---
name: report-assembler
description: 手工测试用治理技能（报告组装）
tools:
  allowed: [core_banking_api:read_only, aml_screening:run, report_writer:draft]
governance:
  agent_id: report-assembler
  version: 1.0.0
  approved_by: "manual-test"
  business_intent: 组装信贷报告初稿供人工复核
  owners:
    accountable: Tester
    technical: Tester
  material: true
  tools:
    - name: core_banking_api:read_only
      capability: read
      idempotent: true
    - name: aml_screening:run
      capability: write
      idempotent: true
      outputs:
        - name: aml_hit
          from: metadata
          path: aml_hit
    - name: report_writer:draft
      capability: write
      idempotent: false
  workflow:
    steps:
      - id: collect_data
        tools: [core_banking_api:read_only]
      - id: aml_check
        tools: [aml_screening:run]
      - id: draft_report
        tools: [report_writer:draft]
  limits:
    max_tool_calls_per_run: 20
    max_calls_per_minute: 10
    max_tokens_per_run: 200000
---

正文
