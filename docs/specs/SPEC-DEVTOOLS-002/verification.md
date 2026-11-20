# SDD-L2 内核 P0：标准符合性、上下文包与可复验证据验证报告

## 1. 元数据

| 项 | 内容 |
|---|---|
| Spec ID | SPEC-DEVTOOLS-002 |
| 工作项 ID | SDD-EPIC-007 |
| 作者 | SDD Agent |
| 创建日期 | 2026-11-20T17:23:51+08:00 |
| 验证时间 | 2026-11-20T18:20:47+08:00 |

## 2. 命令

- Evidence recorded: Command: python -m unittest discover -s tests -v

### Command: python -m unittest discover -s tests -v

- At: 2026-11-20T18:20:47+08:00

- Command: `python -m unittest discover -s tests -v`
- CWD: `C:\Users\Administrator.SC-202402081735\orca\workspaces\sdd-kit\epic-sdd-l2`
- Exit: `0`

- Head: `571aaf3218d4`
- Plan-Hash: `sha256:1089d8891f7694f14426cadfe7e874a11b93ce7287a6878304c0326e13ee1d9b`
- At: `2026-11-20T18:20:47+08:00`

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
[sdd] wrote sdd/manifest.json (version 0.9.0, 42 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] created AGENTS.md with the SDD managed block
[sdd] wrote sdd/manifest.json (version 0.9.0, 42 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] warning: test_commands is empty; add it before sdd verify
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] AGENTS.md managed block already up to date
[sdd] wrote sdd/manifest.json (version 0.9.0, 42 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] warning: test_commands is empty; add it before sdd verify
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] updated the SDD managed block in AGENTS.md
[sdd] wrote sdd/manifest.json (version 0.9.0, 42 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] warning: test_commands is empty; add it before sdd verify
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] created AGENTS.md with the SDD managed block
[sdd] wrote sdd/manifest.json (version 0.9.0, 42 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] AGENTS.md managed block already up to date
[sdd] wrote sdd/manifest.json (version 0.9.0, 42 files)

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
test_verify_command_is_exposed (test_cli.CliTest.test_verify_command_is_exposed) ... ok
test_verify_core_and_agent_detect_tampering (test_cli.CliTest.test_verify_core_and_agent_detect_tampering) ... ok
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
test_gate_reports_include_stable_ids (test_sdd.CheckRegistryTests.test_gate_reports_include_stable_ids) ... ok
test_registry_ids_are_unique (test_sdd.CheckRegistryTests.test_registry_ids_are_unique) ... ok
test_required_item_failure_blocks (test_sdd.CheckRegistryTests.test_required_item_failure_blocks) ... ok
test_allowed_paths_from_design_impact (test_sdd.ContextBundleTests.test_allowed_paths_from_design_impact) ... ok
test_bundle_excludes_other_specs (test_sdd.ContextBundleTests.test_bundle_excludes_other_specs) ... ok
test_bundle_is_read_only (test_sdd.ContextBundleTests.test_bundle_is_read_only) ... ok
test_non_task_step_returns_empty_bundle (test_sdd.ContextBundleTests.test_non_task_step_returns_empty_bundle) ... ok
test_task_step_returns_all_fields (test_sdd.ContextBundleTests.test_task_step_returns_all_fields) ... ok
test_empty_commands_block_pr_ready (test_sdd.EvidenceTests.test_empty_commands_block_pr_ready) ... ok
test_merged_spec_skips_new_evidence_rules (test_sdd.EvidenceTests.test_merged_spec_skips_new_evidence_rules) ... ok
test_nonzero_exit_blocks (test_sdd.EvidenceTests.test_nonzero_exit_blocks) ... ok
test_pass_without_evidence_blocks (test_sdd.EvidenceTests.test_pass_without_evidence_blocks) ... ok
test_success_evidence_passes (test_sdd.EvidenceTests.test_success_evidence_passes) ... ok
test_unmerged_spec_cannot_use_legacy_escape (test_sdd.EvidenceTests.test_unmerged_spec_cannot_use_legacy_escape) ... ok
test_verify_records_structured_evidence (test_sdd.EvidenceTests.test_verify_records_structured_evidence) ... ok
test_body_only_feat_is_not_registered (test_sdd.FeatTraceTests.test_body_only_feat_is_not_registered) ... ok
test_duplicate_feat_is_blocked (test_sdd.FeatTraceTests.test_duplicate_feat_is_blocked) ... ok
test_feat_metadata_must_match_index (test_sdd.FeatTraceTests.test_feat_metadata_must_match_index) ... ok
test_merged_legacy_spec_skips_feat_mapping (test_sdd.FeatTraceTests.test_merged_legacy_spec_skips_feat_mapping) ... ok
test_orphan_fr_ac_is_blocked (test_sdd.FeatTraceTests.test_orphan_fr_ac_is_blocked) ... ok
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
test_manual_gates_require_human_complete (test_sdd.SddFlowTest.test_manual_gates_require_human_complete) ... ok
test_rewind_from_verifying_resumes_to_pr_ready (test_sdd.SddFlowTest.test_rewind_from_verifying_resumes_to_pr_ready) ... ok
test_rewind_requires_human (test_sdd.SddFlowTest.test_rewind_requires_human) ... ok
test_rewind_to_implementing_reopens_last_done_task (test_sdd.SddFlowTest.test_rewind_to_implementing_reopens_last_done_task) ... ok
test_spec_keeps_workflow_snapshot_when_preset_changes (test_sdd.SddFlowTest.test_spec_keeps_workflow_snapshot_when_preset_changes) ... ok
test_strict_workflow_requires_human_gates_and_review (test_sdd.SddFlowTest.test_strict_workflow_requires_human_gates_and_review) ... ok
test_task_complete_requires_start (test_sdd.SddFlowTest.test_task_complete_requires_start) ... ok
test_bare_ac_tag_does_not_count (test_sdd.TestCoverageTests.test_bare_ac_tag_does_not_count) ... ok
test_low_risk_flow_unchanged (test_sdd.TestCoverageTests.test_low_risk_flow_unchanged) ... ok
test_medium_risk_requires_review (test_sdd.TestCoverageTests.test_medium_risk_requires_review) ... ok
test_task_test_name_must_exist (test_sdd.TestCoverageTests.test_task_test_name_must_exist) ... ok
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
test_all_entries_present (test_standard_conformance.StandardConformanceTests.test_all_entries_present) ... ok
test_check_ids_exist (test_standard_conformance.StandardConformanceTests.test_check_ids_exist) ... ok
test_status_values_allowed (test_standard_conformance.StandardConformanceTests.test_status_values_allowed) ... ok

----------------------------------------------------------------------
Ran 121 tests in 198.344s

OK (skipped=2)
```

### Command: python -m unittest discover -s tests -v

- At: 2026-11-20T18:16:33+08:00

- Command: `python -m unittest discover -s tests -v`
- CWD: `C:\Users\Administrator.SC-202402081735\orca\workspaces\sdd-kit\epic-sdd-l2`
- Exit: `0`

- Head: `d8088c7f6190`
- Plan-Hash: `sha256:1089d8891f7694f14426cadfe7e874a11b93ce7287a6878304c0326e13ee1d9b`
- At: `2026-11-20T18:16:33+08:00`

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
[sdd] wrote sdd/manifest.json (version 0.9.0, 42 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] created AGENTS.md with the SDD managed block
[sdd] wrote sdd/manifest.json (version 0.9.0, 42 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] warning: test_commands is empty; add it before sdd verify
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] AGENTS.md managed block already up to date
[sdd] wrote sdd/manifest.json (version 0.9.0, 42 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] warning: test_commands is empty; add it before sdd verify
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] updated the SDD managed block in AGENTS.md
[sdd] wrote sdd/manifest.json (version 0.9.0, 42 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] warning: test_commands is empty; add it before sdd verify
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] created AGENTS.md with the SDD managed block
[sdd] wrote sdd/manifest.json (version 0.9.0, 42 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] AGENTS.md managed block already up to date
[sdd] wrote sdd/manifest.json (version 0.9.0, 42 files)

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
test_verify_command_is_exposed (test_cli.CliTest.test_verify_command_is_exposed) ... ok
test_verify_core_and_agent_detect_tampering (test_cli.CliTest.test_verify_core_and_agent_detect_tampering) ... ok
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
test_gate_reports_include_stable_ids (test_sdd.CheckRegistryTests.test_gate_reports_include_stable_ids) ... ok
test_registry_ids_are_unique (test_sdd.CheckRegistryTests.test_registry_ids_are_unique) ... ok
test_required_item_failure_blocks (test_sdd.CheckRegistryTests.test_required_item_failure_blocks) ... ok
test_allowed_paths_from_design_impact (test_sdd.ContextBundleTests.test_allowed_paths_from_design_impact) ... ok
test_bundle_excludes_other_specs (test_sdd.ContextBundleTests.test_bundle_excludes_other_specs) ... ok
test_bundle_is_read_only (test_sdd.ContextBundleTests.test_bundle_is_read_only) ... ok
test_non_task_step_returns_empty_bundle (test_sdd.ContextBundleTests.test_non_task_step_returns_empty_bundle) ... ok
test_task_step_returns_all_fields (test_sdd.ContextBundleTests.test_task_step_returns_all_fields) ... ok
test_empty_commands_block_pr_ready (test_sdd.EvidenceTests.test_empty_commands_block_pr_ready) ... ok
test_merged_spec_skips_new_evidence_rules (test_sdd.EvidenceTests.test_merged_spec_skips_new_evidence_rules) ... ok
test_nonzero_exit_blocks (test_sdd.EvidenceTests.test_nonzero_exit_blocks) ... ok
test_pass_without_evidence_blocks (test_sdd.EvidenceTests.test_pass_without_evidence_blocks) ... ok
test_success_evidence_passes (test_sdd.EvidenceTests.test_success_evidence_passes) ... ok
test_unmerged_spec_cannot_use_legacy_escape (test_sdd.EvidenceTests.test_unmerged_spec_cannot_use_legacy_escape) ... ok
test_verify_records_structured_evidence (test_sdd.EvidenceTests.test_verify_records_structured_evidence) ... ok
test_body_only_feat_is_not_registered (test_sdd.FeatTraceTests.test_body_only_feat_is_not_registered) ... ok
test_duplicate_feat_is_blocked (test_sdd.FeatTraceTests.test_duplicate_feat_is_blocked) ... ok
test_feat_metadata_must_match_index (test_sdd.FeatTraceTests.test_feat_metadata_must_match_index) ... ok
test_merged_legacy_spec_skips_feat_mapping (test_sdd.FeatTraceTests.test_merged_legacy_spec_skips_feat_mapping) ... ok
test_orphan_fr_ac_is_blocked (test_sdd.FeatTraceTests.test_orphan_fr_ac_is_blocked) ... ok
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
test_manual_gates_require_human_complete (test_sdd.SddFlowTest.test_manual_gates_require_human_complete) ... ok
test_rewind_from_verifying_resumes_to_pr_ready (test_sdd.SddFlowTest.test_rewind_from_verifying_resumes_to_pr_ready) ... ok
test_rewind_requires_human (test_sdd.SddFlowTest.test_rewind_requires_human) ... ok
test_rewind_to_implementing_reopens_last_done_task (test_sdd.SddFlowTest.test_rewind_to_implementing_reopens_last_done_task) ... ok
test_spec_keeps_workflow_snapshot_when_preset_changes (test_sdd.SddFlowTest.test_spec_keeps_workflow_snapshot_when_preset_changes) ... ok
test_strict_workflow_requires_human_gates_and_review (test_sdd.SddFlowTest.test_strict_workflow_requires_human_gates_and_review) ... ok
test_task_complete_requires_start (test_sdd.SddFlowTest.test_task_complete_requires_start) ... ok
test_bare_ac_tag_does_not_count (test_sdd.TestCoverageTests.test_bare_ac_tag_does_not_count) ... ok
test_low_risk_flow_unchanged (test_sdd.TestCoverageTests.test_low_risk_flow_unchanged) ... ok
test_medium_risk_requires_review (test_sdd.TestCoverageTests.test_medium_risk_requires_review) ... ok
test_task_test_name_must_exist (test_sdd.TestCoverageTests.test_task_test_name_must_exist) ... ok
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
test_all_entries_present (test_standard_conformance.StandardConformanceTests.test_all_entries_present) ... ok
test_check_ids_exist (test_standard_conformance.StandardConformanceTests.test_check_ids_exist) ... ok
test_status_values_allowed (test_standard_conformance.StandardConformanceTests.test_status_values_allowed) ... ok

----------------------------------------------------------------------
Ran 121 tests in 199.809s

OK (skipped=2)
```

## 3. 结果

- Evidence recorded: Task T-006

### Task T-006

- At: 2026-11-20T18:12:25+08:00

python -m unittest discover -s tests -v -> Ran 120 tests OK (skipped=2); tests.test_standard_conformance -> 3 OK; python -m sdd verify-core -> passed; python -m sdd verify-agent -> passed; version=0.9.0, manifest 42 files

### Task T-005

- At: 2026-11-20T18:04:40+08:00

python -m unittest tests.test_sdd.TestCoverageTests -v -> Ran 4 tests OK; test_sdd/test_cli/test_mcp_service 全通过；Task 测试名可定位、AC 只认 test_* 函数体、中风险缺 review 阻断、低风险 G4/G5 保持 auto

### Task T-004

- At: 2026-11-20T17:57:42+08:00

python -m unittest tests.test_sdd.EvidenceTests -v -> Ran 7 tests OK; test_sdd/test_cli/test_mcp_service 全通过；verify 写入 Command/CWD/Exit/Head/Plan-Hash/At，空 test_commands 与非 0 退出码均阻断，MERGED legacy 跳过

### Task T-003

- At: 2026-11-20T17:53:37+08:00

python -m unittest tests.test_sdd.ContextBundleTests -v -> Ran 5 tests OK; test_sdd/test_cli/test_mcp_service 全通过；next.context_bundle 九字段、非 Task 空结构、只读、范围派生与其他 Spec 排除已验证

### Task T-002

- At: 2026-11-20T17:48:00+08:00

python -m unittest tests.test_sdd.FeatTraceTests -v -> Ran 5 tests OK; tests.test_sdd/test_cli/test_mcp_service 全通过；FEAT 元数据、结构化映射、G0-04/G0-05、legacy 分支已生效

### Task T-001

- At: 2026-11-20T17:38:58+08:00

python -m unittest tests.test_sdd -v -> Ran 28 tests OK; CheckRegistryTests 4 tests OK; G0/G1 报告含稳定检查 ID，required 失败总体 FAILED

## 4. 未运行

- MCP SDK 未安装，`test_mcp_server` 的 2 个用例按设计跳过；不影响 CLI、状态机和 Gate 检查。
- 未执行真实 GitHub PR 合并；那是人类检查点。

## 5. AC 覆盖

| AC | 测试/证据 | 结果 |
|---|---|---|
| AC-001-1 | `StandardConformanceTests#test_all_entries_present` / `test_status_values_allowed`；`docs/STANDARD-CONFORMANCE.md` | PASS |
| AC-001-2 | `StandardConformanceTests#test_all_entries_present`；12 条目无重复 | PASS |
| AC-001-3 | `StandardConformanceTests#test_check_ids_exist` | PASS |
| AC-002-1 | `FeatTraceTests#test_feat_metadata_must_match_index` | PASS |
| AC-002-2 | `FeatTraceTests#test_feat_metadata_must_match_index`；字段级错误 | PASS |
| AC-002-3 | `FeatTraceTests#test_duplicate_feat_is_blocked` | PASS |
| AC-002-4 | `FeatTraceTests#test_orphan_fr_ac_is_blocked` | PASS |
| AC-002-5 | `FeatTraceTests#test_body_only_feat_is_not_registered` | PASS |
| AC-002-6 | `FeatTraceTests#test_body_only_feat_is_not_registered`；正文不算登记 | PASS |
| AC-002-7 | `FeatTraceTests#test_merged_legacy_spec_skips_feat_mapping` | PASS |
| AC-002-8 | `FeatTraceTests#test_feat_metadata_must_match_index`；非 MERGED 缺 FEAT 阻断 | PASS |
| AC-003-1 | `CheckRegistryTests#test_gate_reports_include_stable_ids` | PASS |
| AC-003-2 | `CheckRegistryTests#test_gate_reports_include_stable_ids`；G0/G1 独立报告 | PASS |
| AC-003-3 | `CheckRegistryTests#test_required_item_failure_blocks` | PASS |
| AC-003-4 | `CheckRegistryTests#test_registry_ids_are_unique` | PASS |
| AC-004-1 | `ContextBundleTests#test_task_step_returns_all_fields` | PASS |
| AC-004-2 | `ContextBundleTests#test_non_task_step_returns_empty_bundle` | PASS |
| AC-004-3 | `ContextBundleTests#test_bundle_is_read_only` | PASS |
| AC-004-4 | `ContextBundleTests#test_allowed_paths_from_design_impact` | PASS |
| AC-004-5 | `ContextBundleTests#test_bundle_excludes_other_specs`；固定九字段 | PASS |
| AC-005-1 | `EvidenceTests#test_empty_commands_block_pr_ready` | PASS |
| AC-005-2 | `EvidenceTests#test_success_evidence_passes` / `test_verify_records_structured_evidence` | PASS |
| AC-005-3 | `EvidenceTests#test_pass_without_evidence_blocks` | PASS |
| AC-005-4 | `TestCoverageTests#test_task_test_name_must_exist` | PASS |
| AC-005-5 | `TestCoverageTests#test_bare_ac_tag_does_not_count` | PASS |
| AC-005-6 | `TestCoverageTests#test_medium_risk_requires_review` | PASS |
| AC-005-7 | `TestCoverageTests#test_low_risk_flow_unchanged` | PASS |
| AC-005-8 | `EvidenceTests#test_nonzero_exit_blocks` | PASS |
| AC-005-9 | `EvidenceTests#test_merged_spec_skips_new_evidence_rules` | PASS |
| AC-005-10 | `EvidenceTests#test_unmerged_spec_cannot_use_legacy_escape` | PASS |

## 6. Gate 5 结论

PASS。全量回归 120 个用例通过（2 个 MCP SDK 用例按设计跳过）；`verify-core`、
`verify-agent` 通过；结构化命令证据含 Exit=0、Head、Plan-Hash 和执行时间。
残余风险：G4/G5 尚未进入稳定检查 ID 注册表，已在
`docs/STANDARD-CONFORMANCE.md` 标注为“部分实现”；真实 PR 合并仍由人类完成。
