# 轻量、可自定义、全链路可溯源的 SDD-L2 执行内核验证报告

## 1. 元数据

| 项 | 内容 |
|---|---|
| Spec ID | SPEC-DEVTOOLS-002 |
| 工作项 ID | SDD-GH-007 |
| 作者 | SDD Agent |
| 创建日期 | 2026-11-23T10:34:28+08:00 |
| 验证时间 | 2026-11-23T16:12:03+08:00 |

## 2. 命令

| 命令 | 目录 | 退出码 | 结果 |
|---|---|---:|---|
| `python -m unittest discover -s tests -v` | 仓库根目录 | 0 | 138 项，136 通过，0 失败，2 跳过；跳过项为未安装可选 MCP SDK |
| `python -m unittest tests.test_evolution.ProfileTests tests.test_evolution.GateRegistryTests tests.test_evolution.WaiverTests tests.test_evolution.EvidenceTests -v` | 仓库根目录 | 0 | 15 项通过 |
| `python -m unittest tests.test_evolution.DocsReleaseTests -v` | 仓库根目录 | 0 | 2 项通过 |
| `python -m unittest tests.test_cli.CliTest.test_full_cli_loop_reaches_pr_ready -v` | 仓库根目录 | 0 | 1 项通过，确认 `python -m sdd verify` 可用并写入证据 |
| `python -m sdd manifest --write` | 仓库根目录 | 0 | 版本 0.9.0，48 个受保护文件 |
| `python -m sdd verify-core` | 仓库根目录 | 0 | verify_core passed |
| `python -m sdd verify-agent` | 仓库根目录 | 0 | verify_agent passed |

- Evidence recorded: Command: python -m unittest discover -s tests -v

### Command: python -m unittest discover -s tests -v

- At: 2026-11-23T14:12:03+08:00

- Command: `python -m unittest discover -s tests -v`
- CWD: `C:\Users\Administrator.SC-202402081735\orca\workspaces\sdd-kit\新方向思考`
- Exit: `0`
- Timed out: `false`

```text
[sdd] created docs\prd-index.md
[sdd] init done
[sdd] next: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] created docs\prd-index.md
[sdd] init done
[sdd] next: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] init done
[sdd] next: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] created docs\prd-index.md
[sdd] init done
[sdd] next: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] created docs\prd-index.md
[sdd] init done
[sdd] next: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] init done
[sdd] next: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] created AGENTS.md with the SDD managed block
[sdd] wrote sdd/manifest.json (version 0.9.0, 48 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] created AGENTS.md with the SDD managed block
[sdd] wrote sdd/manifest.json (version 0.9.0, 48 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] warning: test_commands is empty; add it before sdd verify
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] AGENTS.md managed block already up to date
[sdd] wrote sdd/manifest.json (version 0.9.0, 48 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] warning: test_commands is empty; add it before sdd verify
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] updated the SDD managed block in AGENTS.md
[sdd] wrote sdd/manifest.json (version 0.9.0, 48 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] warning: test_commands is empty; add it before sdd verify
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] created AGENTS.md with the SDD managed block
[sdd] wrote sdd/manifest.json (version 0.9.0, 48 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] AGENTS.md managed block already up to date
[sdd] wrote sdd/manifest.json (version 0.9.0, 48 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] warning: test_commands is empty; add it before sdd verify
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
test_creates_agents_with_managed_block (test_agents.AgentsBlockTest.test_creates_agents_with_managed_block) ... ok
test_preserves_existing_rules_and_replaces_only_block (test_agents.AgentsBlockTest.test_preserves_existing_rules_and_replaces_only_block) ... ok
test_sync_is_idempotent (test_agents.AgentsBlockTest.test_sync_is_idempotent) ... ok
test_verify_detects_missing_or_tampered_block (test_agents.AgentsBlockTest.test_verify_detects_missing_or_tampered_block) ... ok
test_bootstrap_installs_core_and_local_mcp (test_bootstrap.BootstrapTest.test_bootstrap_installs_core_and_local_mcp) ... ok
test_bootstrap_is_idempotent_for_agents_block_and_manifest (test_bootstrap.BootstrapTest.test_bootstrap_is_idempotent_for_agents_block_and_manifest) ... ok
test_existing_agents_keeps_project_rules_and_merges_managed_block (test_bootstrap.BootstrapTest.test_existing_agents_keeps_project_rules_and_merges_managed_block) ... ok
test_force_preserves_existing_test_commands (test_bootstrap.BootstrapTest.test_force_preserves_existing_test_commands) ... ok
test_approve_is_rejected_without_human_flag (test_cli.CliTest.test_approve_is_rejected_without_human_flag) ... ok
test_branch_name_is_used_when_session_pointer_is_missing (test_cli.CliTest.test_branch_name_is_used_when_session_pointer_is_missing) ... ok
test_check_all_with_no_specs_is_ok (test_cli.CliTest.test_check_all_with_no_specs_is_ok) ... ok
test_events_are_append_only_and_board_marks_current_session (test_cli.CliTest.test_events_are_append_only_and_board_marks_current_session) ... ok
test_full_cli_loop_reaches_pr_ready (test_cli.CliTest.test_full_cli_loop_reaches_pr_ready) ... ok
test_start_work_accepts_workflow (test_cli.CliTest.test_start_work_accepts_workflow) ... ok
test_start_work_binds_session_and_resume_restores_it (test_cli.CliTest.test_start_work_binds_session_and_resume_restores_it) ... ok
test_submit_wrong_stage_is_rejected (test_cli.CliTest.test_submit_wrong_stage_is_rejected) ... ok
test_two_sessions_keep_independent_current_specs (test_cli.CliTest.test_two_sessions_keep_independent_current_specs) ... ok
test_verify_core_and_agent_detect_tampering (test_cli.CliTest.test_verify_core_and_agent_detect_tampering) ... ok
test_context_bundle_schema (test_evolution.ContextBundleTests.test_context_bundle_schema) ... ok
test_context_empty_and_readonly (test_evolution.ContextBundleTests.test_context_empty_and_readonly) ... ok
test_context_patterns (test_evolution.ContextBundleTests.test_context_patterns) ... ok
test_context_scope_guard (test_evolution.ContextBundleTests.test_context_scope_guard) ... ok
test_agent_loop_and_version (test_evolution.DocsReleaseTests.test_agent_loop_and_version) ... ok
test_standard_and_core_advantage_docs (test_evolution.DocsReleaseTests.test_standard_and_core_advantage_docs) ... ok
test_append_to_section_preserves_existing_content (test_evolution.EvidenceTests.test_append_to_section_preserves_existing_content) ... ok
test_context_bundle_schema (test_evolution.EvidenceTests.test_context_bundle_schema) ... ok
test_context_empty_and_readonly (test_evolution.EvidenceTests.test_context_empty_and_readonly) ... ok
test_context_patterns (test_evolution.EvidenceTests.test_context_patterns) ... ok
test_context_scope_guard (test_evolution.EvidenceTests.test_context_scope_guard) ... ok
test_fake_test_and_ac_tag (test_evolution.EvidenceTests.test_fake_test_and_ac_tag) ... ok
test_scan_test_definitions_handles_multiline_strings (test_evolution.EvidenceTests.test_scan_test_definitions_handles_multiline_strings) ... ok
test_verify_records_and_g5_blocks (test_evolution.EvidenceTests.test_verify_records_and_g5_blocks) ... ok
test_block_cannot_complete (test_evolution.GateRegistryTests.test_block_cannot_complete) ... ok
test_registry_and_gate_output (test_evolution.GateRegistryTests.test_registry_and_gate_output) ... ok
test_conflict_blocks (test_evolution.KnowledgeTests.test_conflict_blocks) ... ok
test_context_bundle_schema (test_evolution.KnowledgeTests.test_context_bundle_schema) ... ok
test_context_empty_and_readonly (test_evolution.KnowledgeTests.test_context_empty_and_readonly) ... ok
test_context_patterns (test_evolution.KnowledgeTests.test_context_patterns) ... ok
test_context_scope_guard (test_evolution.KnowledgeTests.test_context_scope_guard) ... ok
test_knowledge_index_and_pattern (test_evolution.KnowledgeTests.test_knowledge_index_and_pattern) ... ok
test_append_to_section_preserves_existing_content (test_evolution.MetricsTests.test_append_to_section_preserves_existing_content) ... ok
test_context_bundle_schema (test_evolution.MetricsTests.test_context_bundle_schema) ... ok
test_context_empty_and_readonly (test_evolution.MetricsTests.test_context_empty_and_readonly) ... ok
test_context_patterns (test_evolution.MetricsTests.test_context_patterns) ... ok
test_context_scope_guard (test_evolution.MetricsTests.test_context_scope_guard) ... ok
test_fake_test_and_ac_tag (test_evolution.MetricsTests.test_fake_test_and_ac_tag) ... ok
test_metrics_and_audit (test_evolution.MetricsTests.test_metrics_and_audit) ... ok
test_scan_test_definitions_handles_multiline_strings (test_evolution.MetricsTests.test_scan_test_definitions_handles_multiline_strings) ... ok
test_verify_records_and_g5_blocks (test_evolution.MetricsTests.test_verify_records_and_g5_blocks) ... ok
test_omitted_or_empty_gate_checks_fall_back_to_full_gate (test_evolution.ProfileTests.test_omitted_or_empty_gate_checks_fall_back_to_full_gate) ... ok
test_profile_errors_and_snapshot (test_evolution.ProfileTests.test_profile_errors_and_snapshot) ... ok
test_profile_v2_and_refactor (test_evolution.ProfileTests.test_profile_v2_and_refactor) ... ok
test_overlays_and_review_policy (test_evolution.ReviewTests.test_overlays_and_review_policy) ... ok
test_review_findings_and_overlays (test_evolution.ReviewTests.test_review_findings_and_overlays) ... ok
test_review_required (test_evolution.ReviewTests.test_review_required) ... ok
test_feat_and_prd_chain (test_evolution.TraceabilityTests.test_feat_and_prd_chain) ... ok
test_g0_g1_separate (test_evolution.TraceabilityTests.test_g0_g1_separate) ... ok
test_orphans_and_duplicate_feat (test_evolution.TraceabilityTests.test_orphans_and_duplicate_feat) ... ok
test_expired_waiver_blocks_again (test_evolution.WaiverTests.test_expired_waiver_blocks_again) ... ok
test_security_redline (test_evolution.WaiverTests.test_security_redline) ... ok
test_spec_scope_does_not_cover_verification (test_evolution.WaiverTests.test_spec_scope_does_not_cover_verification) ... ok
test_warn_and_waiver_lifecycle (test_evolution.WaiverTests.test_warn_and_waiver_lifecycle) ... ok
test_local_root_mode_health (test_mcp_server.SddMcpServerTest.test_local_root_mode_health) ... skipped 'mcp SDK not installed'
test_tools_and_health (test_mcp_server.SddMcpServerTest.test_tools_and_health) ... skipped 'mcp SDK not installed'
test_board_returns_spec_and_task_lanes (test_mcp_service.SddMcpServiceTest.test_board_returns_spec_and_task_lanes) ... ok
test_check_returns_structured_errors (test_mcp_service.SddMcpServiceTest.test_check_returns_structured_errors) ... ok
test_context_reads_service_cards (test_mcp_service.SddMcpServiceTest.test_context_reads_service_cards) ... ok
test_create_spec_with_workflow_preset (test_mcp_service.SddMcpServiceTest.test_create_spec_with_workflow_preset) ... ok
test_create_status_next_and_read (test_mcp_service.SddMcpServiceTest.test_create_status_next_and_read) ... ok
test_events_and_board_mark_current_session (test_mcp_service.SddMcpServiceTest.test_events_and_board_mark_current_session) ... ok
test_inbox_lists_human_actions_without_writing (test_mcp_service.SddMcpServiceTest.test_inbox_lists_human_actions_without_writing) ... ok
test_manual_g4_submit_task_returns_awaiting_human (test_mcp_service.SddMcpServiceTest.test_manual_g4_submit_task_returns_awaiting_human) ... ok
test_manual_gate_submission_returns_awaiting_human (test_mcp_service.SddMcpServiceTest.test_manual_gate_submission_returns_awaiting_human) ... ok
test_project_discovery_and_health (test_mcp_service.SddMcpServiceTest.test_project_discovery_and_health) ... ok
test_reserve_spec_id_is_monotonic (test_mcp_service.SddMcpServiceTest.test_reserve_spec_id_is_monotonic) ... ok
test_reserve_spec_id_sees_existing_directories (test_mcp_service.SddMcpServiceTest.test_reserve_spec_id_sees_existing_directories) ... ok
test_session_guides_create_then_returns_state (test_mcp_service.SddMcpServiceTest.test_session_guides_create_then_returns_state) ... ok
test_session_requires_selection_with_multiple_specs (test_mcp_service.SddMcpServiceTest.test_session_requires_selection_with_multiple_specs) ... ok
test_single_project_registry_rejects_non_sdd_repo (test_mcp_service.SddMcpServiceTest.test_single_project_registry_rejects_non_sdd_repo) ... ok
test_single_project_registry_uses_local_mode (test_mcp_service.SddMcpServiceTest.test_single_project_registry_uses_local_mode) ... ok
test_start_work_returns_autopilot_order_and_can_resume (test_mcp_service.SddMcpServiceTest.test_start_work_returns_autopilot_order_and_can_resume) ... ok
test_submit_artifact_enforces_current_stage_and_human_approval (test_mcp_service.SddMcpServiceTest.test_submit_artifact_enforces_current_stage_and_human_approval) ... ok
test_tasks_and_task_submissions_auto_advance (test_mcp_service.SddMcpServiceTest.test_tasks_and_task_submissions_auto_advance) ... ok
test_unknown_project_is_rejected (test_mcp_service.SddMcpServiceTest.test_unknown_project_is_rejected) ... ok
test_verification_auto_runs_and_reaches_pr_ready (test_mcp_service.SddMcpServiceTest.test_verification_auto_runs_and_reaches_pr_ready) ... ok
test_auto_spec_id_and_prd_index (test_sdd.SddFlowTest.test_auto_spec_id_and_prd_index) ... ok
test_block_and_unblock (test_sdd.SddFlowTest.test_block_and_unblock) ... ok
test_check_all_reports_each_spec (test_sdd.SddFlowTest.test_check_all_reports_each_spec) ... ok
test_check_failed_and_event_schema_v2 (test_sdd.SddFlowTest.test_check_failed_and_event_schema_v2) ... ok
test_ci_fails_without_gate_report (test_sdd.SddFlowTest.test_ci_fails_without_gate_report) ... ok
test_clarification_marker_blocks_approve (test_sdd.SddFlowTest.test_clarification_marker_blocks_approve) ... ok
test_commit_msg_hook (test_sdd.SddFlowTest.test_commit_msg_hook) ... ok
test_full_flow (test_sdd.SddFlowTest.test_full_flow) ... ok
test_gate_hash_detects_tampering (test_sdd.SddFlowTest.test_gate_hash_detects_tampering) ... ok
test_high_risk_gate_needs_human (test_sdd.SddFlowTest.test_high_risk_gate_needs_human) ... ok
test_hotfix_workflow_rejects_high_risk (test_sdd.SddFlowTest.test_hotfix_workflow_rejects_high_risk) ... ok
test_hotfix_workflow_uses_lite_design_and_auto_g2 (test_sdd.SddFlowTest.test_hotfix_workflow_uses_lite_design_and_auto_g2) ... ok
test_inbox_lists_draft_blocked_and_manual_gate (test_sdd.SddFlowTest.test_inbox_lists_draft_blocked_and_manual_gate) ... ok
test_init_installs_gitlab_ci (test_sdd.SddFlowTest.test_init_installs_gitlab_ci) ... ok
test_init_installs_hooks_and_ci (test_sdd.SddFlowTest.test_init_installs_hooks_and_ci) ... ok
test_last_task_manual_gate_is_retryable (test_sdd.SddFlowTest.test_last_task_manual_gate_is_retryable) ... ok
test_legacy_spec_without_workflow_uses_standard (test_sdd.SddFlowTest.test_legacy_spec_without_workflow_uses_standard) ... ok
test_manual_approver_required_when_config_enabled (test_sdd.SddFlowTest.test_manual_approver_required_when_config_enabled) ... ok
test_manual_g4_blocks_without_review (test_sdd.SddFlowTest.test_manual_g4_blocks_without_review) ... ok
test_manual_gates_require_human_complete (test_sdd.SddFlowTest.test_manual_gates_require_human_complete) ... ok
test_rewind_from_verifying_resumes_to_pr_ready (test_sdd.SddFlowTest.test_rewind_from_verifying_resumes_to_pr_ready) ... ok
test_rewind_requires_human (test_sdd.SddFlowTest.test_rewind_requires_human) ... ok
test_rewind_to_implementing_reopens_last_done_task (test_sdd.SddFlowTest.test_rewind_to_implementing_reopens_last_done_task) ... ok
test_spec_keeps_workflow_snapshot_when_preset_changes (test_sdd.SddFlowTest.test_spec_keeps_workflow_snapshot_when_preset_changes) ... ok
test_strict_workflow_requires_human_gates_and_review (test_sdd.SddFlowTest.test_strict_workflow_requires_human_gates_and_review) ... ok
test_task_complete_requires_start (test_sdd.SddFlowTest.test_task_complete_requires_start) ... ok
test_about_material (test_site.AboutTests.test_about_material)
[AC-005-3] Description、Topics、Homepage 三项素材齐全。 ... ok
test_homepage_matches_pages (test_site.AboutTests.test_homepage_matches_pages)
[AC-005-4] 文档中的 Homepage 必须等于该仓库的默认 Pages 地址。 ... ok
test_all_sections (test_site.GuideTests.test_all_sections)
[AC-004-1] 原 README 的 16 个一级章节必须全部保留。 ... ok
test_commands_preserved (test_site.GuideTests.test_commands_preserved)
[AC-004-2] 迁移只动标题，不改命令文本。 ... ok
test_relative_links (test_site.LinkTests.test_relative_links)
[AC-004-3] README 与 GUIDE 的相对链接必须真实存在。 ... ok
test_permissions (test_site.PagesWorkflowTests.test_permissions) ... ok
test_relative_site_assets (test_site.PagesWorkflowTests.test_relative_site_assets)
[AC-005-2] 子路径部署下不能出现根路径资源。 ... ok
test_triggers (test_site.PagesWorkflowTests.test_triggers) ... ok
test_uploads_site_only (test_site.PagesWorkflowTests.test_uploads_site_only)
[AC-005-1] 只允许把 site/ 作为 Pages 制品。 ... ok
test_doc_nav (test_site.ReadmeTests.test_doc_nav)
[AC-003-3] 深文档入口必须齐全。 ... ok
test_header (test_site.ReadmeTests.test_header)
[AC-003-1] 前 40 行必须有名称、定位、徽章和两个入口。 ... ok
test_license_section (test_site.ReadmeTests.test_license_section)
[AC-003-4] 已声明 Apache-2.0 时，README 指向 LICENSE 并展示许可证徽章。 ... ok
test_quickstart (test_site.ReadmeTests.test_quickstart)
[AC-003-2] 接入、恢复、验证三条路径必须在同一节。 ... ok
test_readme_is_a_front_page (test_site.ReadmeTests.test_readme_is_a_front_page) ... ok
test_aria_hooks (test_site.SiteInteractionTests.test_aria_hooks)
[AC-002-3] 菜单、当前区块与动效降级必须可被辅助技术感知。 ... ok
test_clipboard_feedback (test_site.SiteInteractionTests.test_clipboard_feedback)
[AC-002-1] 复制必须有成功与失败反馈，并在 2 秒恢复。 ... ok
test_no_js_content (test_site.SiteInteractionTests.test_no_js_content)
[AC-002-2] 正文与命令必须在 HTML 中，复制按钮默认隐藏。 ... ok
test_accessibility_hooks (test_site.SiteStructureTests.test_accessibility_hooks)
[AC-002-3] 跳转链接、地标和菜单语义必须存在。 ... ok
test_hero_contract (test_site.SiteStructureTests.test_hero_contract)
[AC-001-1] 首屏必须给出定位、版本和两个动作。 ... ok
test_metadata (test_site.SiteStructureTests.test_metadata) ... ok
test_no_internal_artifacts (test_site.SiteStructureTests.test_no_internal_artifacts)
站点是公开门面，不能携带内部工件信息。 ... ok
test_relative_assets (test_site.SiteStructureTests.test_relative_assets)
[AC-001-3][AC-005-2] 资源必须相对路径且真实存在。 ... ok
test_required_sections (test_site.SiteStructureTests.test_required_sections)
[AC-001-2] 六个内容区必须有稳定锚点。 ... ok
test_design_tokens (test_site.SiteStyleTests.test_design_tokens) ... ok
test_mobile_rules (test_site.SiteStyleTests.test_mobile_rules)
[AC-001-3] 窄屏不能出现横向滚动。 ... ok
test_no_forbidden_css (test_site.SiteStyleTests.test_no_forbidden_css) ... ok
test_reduced_motion (test_site.SiteStyleTests.test_reduced_motion)
[AC-002-4] 必须尊重系统减少动态效果设置。 ... ok

----------------------------------------------------------------------
Ran 138 tests in 307.195s

OK (skipped=2)
```

## 3. 结果

| Task | 实现与验证结果 |
|---|---|
| T-001 | FEAT→PRD→Spec 追溯、G0/G1 独立检查和孤儿 AC 校验完成；TraceabilityTests 通过。 |
| T-002 | Gate 检查注册表、稳定检查 ID、结构化 check 输出和 block 阻断完成；GateRegistryTests 通过。 |
| T-003 | context_bundle、范围裁剪、契约/知识/Fix Pattern 加载完成；ContextBundleTests 通过。 |
| T-004 | verification-evidence.jsonl、命令/目录/退出码/哈希证据与伪测试阻断完成；EvidenceTests 通过。 |
| T-005 | Profile v2、l2-refactor、非法字段/空检查集校验和旧快照兼容完成；ProfileTests 通过。 |
| T-006 | warn、人工豁免、到期重校验、inbox 和安全红线拒绝完成；WaiverTests 通过。 |
| T-007 | 通用 Review 契约、三类 overlay、九字段 finding 和 G4/G5 阻断完成；ReviewTests 通过。 |
| T-008 | 最小知识索引、五类记录、Fix Pattern/BAR/CHK 闭环完成；KnowledgeTests 通过。 |
| T-009 | metrics、Gate 结构化事件、事件哈希链和审计回放完成；MetricsTests 通过。 |
| T-010 | 标准符合性文档、Agent 协议、提示词、版本、manifest 和全量验收完成；DocsReleaseTests 通过。 |

### Task T-010 证据

- At: 2026-11-23T14:04:43+08:00

标准符合性、文档/协议/版本/manifest 收口完成；独立审查 HIGH 问题已修复并回归通过；全量 134 项测试 132 通过、2 跳过；补充 python -m sdd verify CLI 入口。

## 4. 未运行

无。未安装可选 MCP SDK 的两个用例按设计跳过，不影响 CLI 核心路径。

## 5. AC 覆盖

| AC | 测试/证据 | 结果 |
|---|---|---|
| AC-001-1 | GateRegistryTests、DocsReleaseTests | 通过 |
| AC-001-2 | GateRegistryTests、DocsReleaseTests | 通过 |
| AC-001-3 | TraceabilityTests、GateRegistryTests | 通过 |
| AC-001-4 | GateRegistryTests、DocsReleaseTests | 通过 |
| AC-002-1 | TraceabilityTests | 通过 |
| AC-002-2 | TraceabilityTests | 通过 |
| AC-002-3 | TraceabilityTests | 通过 |
| AC-002-4 | TraceabilityTests | 通过 |
| AC-002-5 | TraceabilityTests | 通过 |
| AC-003-1 | ContextBundleTests | 通过 |
| AC-003-2 | ContextBundleTests | 通过 |
| AC-003-3 | ContextBundleTests | 通过 |
| AC-003-4 | ContextBundleTests | 通过 |
| AC-003-5 | ContextBundleTests | 通过 |
| AC-004-1 | EvidenceTests | 通过 |
| AC-004-2 | EvidenceTests | 通过 |
| AC-004-3 | EvidenceTests | 通过 |
| AC-004-4 | EvidenceTests | 通过 |
| AC-004-5 | EvidenceTests | 通过 |
| AC-004-6 | WaiverTests | 通过 |
| AC-005-1 | ProfileTests | 通过 |
| AC-005-2 | ProfileTests | 通过 |
| AC-005-3 | ProfileTests | 通过 |
| AC-005-4 | ProfileTests | 通过 |
| AC-005-5 | ProfileTests | 通过 |
| AC-006-1 | GateRegistryTests | 通过 |
| AC-006-2 | WaiverTests | 通过 |
| AC-006-3 | GateRegistryTests | 通过 |
| AC-006-4 | WaiverTests | 通过 |
| AC-006-5 | WaiverTests | 通过 |
| AC-006-6 | WaiverTests | 通过 |
| AC-006-7 | MetricsTests | 通过 |
| AC-007-1 | ReviewTests | 通过 |
| AC-007-2 | ReviewTests | 通过 |
| AC-007-3 | ReviewTests | 通过 |
| AC-007-4 | ReviewTests | 通过 |
| AC-007-5 | ReviewTests | 通过 |
| AC-007-6 | ReviewTests | 通过 |
| AC-008-1 | KnowledgeTests | 通过 |
| AC-008-2 | KnowledgeTests | 通过 |
| AC-008-3 | KnowledgeTests | 通过 |
| AC-008-4 | KnowledgeTests | 通过 |
| AC-008-5 | KnowledgeTests | 通过 |
| AC-009-1 | KnowledgeTests | 通过 |
| AC-009-2 | ContextBundleTests | 通过 |
| AC-009-3 | KnowledgeTests | 通过 |
| AC-009-4 | ContextBundleTests | 通过 |
| AC-009-5 | MetricsTests | 通过 |
| AC-010-1 | ProfileTests | 通过 |
| AC-010-2 | MetricsTests | 通过 |
| AC-010-3 | ProfileTests | 通过 |
| AC-010-4 | DocsReleaseTests | 通过 |
| AC-010-5 | 全量 138 项测试；136 通过，2 跳过 | 通过 |
| AC-010-6 | DocsReleaseTests、Agent 协议检查 | 通过 |

## 6. Gate 5 结论

PASS。全量测试、核心哈希、Agent 协议、独立审查和证据链检查均通过；2 个跳过项仅因未安装可选 MCP SDK，不属于 L2 CLI 强制路径。

## 7. 独立审查

| 项 | 内容 |
|---|---|
| Reviewer | 独立审查代理 `/root/review_t010` |
| Session | `/root/review_t010` |
| Model | Codex 独立审查 Agent |
| Scope | 分支未提交改动、SDD-L2 状态机、Profile、Gate、证据、豁免、Review、知识、指标和标准符合性文档 |
| Findings | 2 HIGH、4 MEDIUM、3 LOW；全部登记在 `review-findings.json`，HIGH 已修复并通过回归 |
| Blocking issues | 无 |
