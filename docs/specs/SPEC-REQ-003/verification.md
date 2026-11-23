# SDD-GATE-002验证报告

## 1. 元数据

| 项 | 内容 |
|---|---|
| Spec ID | SPEC-REQ-003 |
| 工作项 ID | SDD-GATE-002 |
| 作者 | SDD Agent |
| 创建日期 | 2026-11-23T16:37:41+08:00 |
| 验证时间 | 2026-11-23T16:37:41+08:00 |

## 2. 命令

- Evidence recorded: Command: python -m unittest discover -s tests -v

### Command: python -m unittest discover -s tests -v

- At: 2026-11-23T18:28:15+08:00

- Command: `python -m unittest discover -s tests -v`
- CWD: `C:\Users\Administrator.SC-202402081735\orca\workspaces\sdd-kit\epic-sdd-l2`
- Exit: `0`

- Head: `de3aec901378`
- Plan-Hash: `sha256:a07ed26d62620058c69eea359069cebeb9954cb1c511aeaeaa28f5353f717d9e`
- At: `2026-11-23T18:28:15+08:00`

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
[sdd] created docs\prd-index.md
[sdd] init done
[sdd] next: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] init done
[sdd] next: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] created docs\prd-index.md
[sdd] init done
[sdd] next: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] init done
[sdd] next: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] created AGENTS.md with the SDD managed block
[sdd] wrote sdd/manifest.json (version 0.9.5, 44 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] created AGENTS.md with the SDD managed block
[sdd] wrote sdd/manifest.json (version 0.9.5, 44 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] test commands: python -m unittest discover -s tests -v (override with --test-command)
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] AGENTS.md managed block already up to date
[sdd] wrote sdd/manifest.json (version 0.9.5, 44 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] test commands: python -m unittest discover -s tests -v (override with --test-command)
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] created AGENTS.md with the SDD managed block
[sdd] wrote sdd/manifest.json (version 0.9.5, 44 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] test commands: python -m unittest discover -s tests -v (override with --test-command)
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] updated the SDD managed block in AGENTS.md
[sdd] wrote sdd/manifest.json (version 0.9.5, 44 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] test commands: python -m unittest discover -s tests -v (override with --test-command)
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] created AGENTS.md with the SDD managed block
[sdd] wrote sdd/manifest.json (version 0.9.5, 44 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] test commands: python -m unittest discover -s tests -v (override with --test-command)
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] AGENTS.md managed block already up to date
[sdd] wrote sdd/manifest.json (version 0.9.5, 44 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] test commands: python -m unittest discover -s tests -v (override with --test-command)
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] created AGENTS.md with the SDD managed block
[sdd] wrote sdd/manifest.json (version 0.9.5, 44 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] AGENTS.md managed block already up to date
[sdd] wrote sdd/manifest.json (version 0.9.5, 44 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] test commands: make test (override with --test-command)
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
test_creates_agents_with_managed_block (test_agents.AgentsBlockTest.test_creates_agents_with_managed_block) ... ok
test_preserves_existing_rules_and_replaces_only_block (test_agents.AgentsBlockTest.test_preserves_existing_rules_and_replaces_only_block) ... ok
test_sync_is_idempotent (test_agents.AgentsBlockTest.test_sync_is_idempotent) ... ok
test_verify_detects_missing_or_tampered_block (test_agents.AgentsBlockTest.test_verify_detects_missing_or_tampered_block) ... ok
test_bootstrap_installs_core_and_local_mcp (test_bootstrap.BootstrapTest.test_bootstrap_installs_core_and_local_mcp) ... ok
test_bootstrap_is_idempotent_for_agents_block_and_manifest (test_bootstrap.BootstrapTest.test_bootstrap_is_idempotent_for_agents_block_and_manifest) ... ok
test_defaults_target_to_cwd_and_project_to_folder_name (test_bootstrap.BootstrapTest.test_defaults_target_to_cwd_and_project_to_folder_name) ... ok
test_existing_agents_keeps_project_rules_and_merges_managed_block (test_bootstrap.BootstrapTest.test_existing_agents_keeps_project_rules_and_merges_managed_block) ... ok
test_force_keeps_project_id_when_not_passed (test_bootstrap.BootstrapTest.test_force_keeps_project_id_when_not_passed) ... ok
test_force_preserves_existing_test_commands (test_bootstrap.BootstrapTest.test_force_preserves_existing_test_commands) ... ok
test_refuses_to_bootstrap_the_kit_source_repository (test_bootstrap.BootstrapTest.test_refuses_to_bootstrap_the_kit_source_repository) ... ok
test_ci_workflow_runs_sdd_checks (test_ci_contract.CiWorkflowTests.test_ci_workflow_runs_sdd_checks) ... ok
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
test_workflow_validate_errors (test_cli.WorkflowCliTests.test_workflow_validate_errors) ... ok
test_workflow_validate_json (test_cli.WorkflowCliTests.test_workflow_validate_json) ... ok
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
test_check_accepts_legacy_crlf_hash (test_sdd.ArtifactHashTests.test_check_accepts_legacy_crlf_hash) ... ok
test_check_ignores_line_ending_only_change (test_sdd.ArtifactHashTests.test_check_ignores_line_ending_only_change) ... ok
test_check_rejects_content_change_with_legacy_hash (test_sdd.ArtifactHashTests.test_check_rejects_content_change_with_legacy_hash) ... ok
test_check_rejects_text_change (test_sdd.ArtifactHashTests.test_check_rejects_text_change) ... ok
test_new_gate_hash_uses_lf (test_sdd.ArtifactHashTests.test_new_gate_hash_uses_lf) ... ok
test_text_hash_is_line_ending_stable (test_sdd.ArtifactHashTests.test_text_hash_is_line_ending_stable) ... ok
test_gate_reports_include_stable_ids (test_sdd.CheckRegistryTests.test_gate_reports_include_stable_ids) ... ok
test_registry_ids_are_unique (test_sdd.CheckRegistryTests.test_registry_ids_are_unique) ... ok
test_required_item_failure_blocks (test_sdd.CheckRegistryTests.test_required_item_failure_blocks) ... ok
test_allowed_paths_from_design_impact (test_sdd.ContextBundleTests.test_allowed_paths_from_design_impact) ... ok
test_bundle_excludes_other_specs (test_sdd.ContextBundleTests.test_bundle_excludes_other_specs) ... ok
test_bundle_is_read_only (test_sdd.ContextBundleTests.test_bundle_is_read_only) ... ok
test_non_task_step_returns_empty_bundle (test_sdd.ContextBundleTests.test_non_task_step_returns_empty_bundle) ... ok
test_task_step_returns_all_fields (test_sdd.ContextBundleTests.test_task_step_returns_all_fields) ... ok
test_delivery_confirmed_merged_spec_keeps_evidence_rules (test_sdd.EvidenceTests.test_delivery_confirmed_merged_spec_keeps_evidence_rules) ... ok
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
test_release_metadata_and_ci_contract (test_sdd.GateBoundaryTests.test_release_metadata_and_ci_contract) ... ok
test_waive_is_cli_only_human_action (test_sdd.GateBoundaryTests.test_waive_is_cli_only_human_action) ... ok
test_advisory_failure_warns (test_sdd.GateClassificationTests.test_advisory_failure_warns) ... ok
test_gate_report_renders_warn_and_block (test_sdd.GateClassificationTests.test_gate_report_renders_warn_and_block) ... ok
test_redline_cannot_be_waived (test_sdd.GateClassificationTests.test_redline_cannot_be_waived) ... ok
test_required_failure_blocks (test_sdd.GateClassificationTests.test_required_failure_blocks) ... ok
test_inbox_surfaces_gate_warnings (test_sdd.GateInboxMetricsTests.test_inbox_surfaces_gate_warnings) ... ok
test_legacy_report_rows_are_compatible (test_sdd.GateInboxMetricsTests.test_legacy_report_rows_are_compatible) ... ok
test_metrics_group_by_check_id (test_sdd.GateInboxMetricsTests.test_metrics_group_by_check_id) ... ok
test_invalid_registry_metadata_rejected (test_sdd.GateRegistryTests.test_invalid_registry_metadata_rejected) ... ok
test_legacy_ids_and_reports_supported (test_sdd.GateRegistryTests.test_legacy_ids_and_reports_supported) ... ok
test_registry_covers_all_gates (test_sdd.GateRegistryTests.test_registry_covers_all_gates) ... ok
test_active_waiver_downgrades_required_to_warn (test_sdd.GateWaiverTests.test_active_waiver_downgrades_required_to_warn) ... ok
test_expired_or_changed_artifact_revalidates (test_sdd.GateWaiverTests.test_expired_or_changed_artifact_revalidates) ... ok
test_waive_records_scope_and_approver (test_sdd.GateWaiverTests.test_waive_records_scope_and_approver) ... ok
test_waive_rejects_invalid_check_or_human (test_sdd.GateWaiverTests.test_waive_rejects_invalid_check_or_human) ... ok
test_recent_trailer_only_applies_to_active_specs (test_sdd.GitTrailerTests.test_recent_trailer_only_applies_to_active_specs) ... ok
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
test_pr_url_requires_delivery_confirmation (test_sdd.SddFlowTest.test_pr_url_requires_delivery_confirmation) ... ok
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
test_l2_refactor_flow (test_sdd.WorkflowProfileTests.test_l2_refactor_flow) ... ok
test_old_specs_stay_stable (test_sdd.WorkflowProfileTests.test_old_specs_stay_stable) ... ok
test_schema1_snapshot_unchanged (test_sdd.WorkflowProfileTests.test_schema1_snapshot_unchanged) ... ok
test_unknown_fields_report_paths (test_sdd.WorkflowProfileTests.test_unknown_fields_report_paths) ... ok
test_valid_v2_profile (test_sdd.WorkflowProfileTests.test_valid_v2_profile) ... ok
test_extra_human_checkpoint (test_sdd.WorkflowRuntimeTests.test_extra_human_checkpoint) ... ok
test_gate_checks_filter_advisory (test_sdd.WorkflowRuntimeTests.test_gate_checks_filter_advisory) ... ok
test_risk_and_context_rules (test_sdd.WorkflowRuntimeTests.test_risk_and_context_rules) ... ok
test_gate_or_checkpoint_conflict_rejected (test_sdd.WorkflowStageTests.test_gate_or_checkpoint_conflict_rejected) ... ok
test_invalid_stage_order_rejected (test_sdd.WorkflowStageTests.test_invalid_stage_order_rejected) ... ok
test_skip_design_stage (test_sdd.WorkflowStageTests.test_skip_design_stage) ... ok
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
test_permissions (test_site.PagesWorkflowTests.tes
... (truncated)
```

### Command: python -m unittest discover -s tests -v

- At: 2026-11-23T18:21:18+08:00

- Command: `python -m unittest discover -s tests -v`
- CWD: `C:\Users\Administrator.SC-202402081735\orca\workspaces\sdd-kit\epic-sdd-l2`
- Exit: `0`

- Head: `de3aec901378`
- Plan-Hash: `sha256:a07ed26d62620058c69eea359069cebeb9954cb1c511aeaeaa28f5353f717d9e`
- At: `2026-11-23T18:21:18+08:00`

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
[sdd] created docs\prd-index.md
[sdd] init done
[sdd] next: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] init done
[sdd] next: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] created docs\prd-index.md
[sdd] init done
[sdd] next: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] init done
[sdd] next: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] created AGENTS.md with the SDD managed block
[sdd] wrote sdd/manifest.json (version 0.9.5, 44 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] created AGENTS.md with the SDD managed block
[sdd] wrote sdd/manifest.json (version 0.9.5, 44 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] test commands: python -m unittest discover -s tests -v (override with --test-command)
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] AGENTS.md managed block already up to date
[sdd] wrote sdd/manifest.json (version 0.9.5, 44 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] test commands: python -m unittest discover -s tests -v (override with --test-command)
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] created AGENTS.md with the SDD managed block
[sdd] wrote sdd/manifest.json (version 0.9.5, 44 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] test commands: python -m unittest discover -s tests -v (override with --test-command)
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] updated the SDD managed block in AGENTS.md
[sdd] wrote sdd/manifest.json (version 0.9.5, 44 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] test commands: python -m unittest discover -s tests -v (override with --test-command)
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] created AGENTS.md with the SDD managed block
[sdd] wrote sdd/manifest.json (version 0.9.5, 44 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] test commands: python -m unittest discover -s tests -v (override with --test-command)
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] AGENTS.md managed block already up to date
[sdd] wrote sdd/manifest.json (version 0.9.5, 44 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] test commands: python -m unittest discover -s tests -v (override with --test-command)
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] created AGENTS.md with the SDD managed block
[sdd] wrote sdd/manifest.json (version 0.9.5, 44 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] AGENTS.md managed block already up to date
[sdd] wrote sdd/manifest.json (version 0.9.5, 44 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] test commands: make test (override with --test-command)
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
test_creates_agents_with_managed_block (test_agents.AgentsBlockTest.test_creates_agents_with_managed_block) ... ok
test_preserves_existing_rules_and_replaces_only_block (test_agents.AgentsBlockTest.test_preserves_existing_rules_and_replaces_only_block) ... ok
test_sync_is_idempotent (test_agents.AgentsBlockTest.test_sync_is_idempotent) ... ok
test_verify_detects_missing_or_tampered_block (test_agents.AgentsBlockTest.test_verify_detects_missing_or_tampered_block) ... ok
test_bootstrap_installs_core_and_local_mcp (test_bootstrap.BootstrapTest.test_bootstrap_installs_core_and_local_mcp) ... ok
test_bootstrap_is_idempotent_for_agents_block_and_manifest (test_bootstrap.BootstrapTest.test_bootstrap_is_idempotent_for_agents_block_and_manifest) ... ok
test_defaults_target_to_cwd_and_project_to_folder_name (test_bootstrap.BootstrapTest.test_defaults_target_to_cwd_and_project_to_folder_name) ... ok
test_existing_agents_keeps_project_rules_and_merges_managed_block (test_bootstrap.BootstrapTest.test_existing_agents_keeps_project_rules_and_merges_managed_block) ... ok
test_force_keeps_project_id_when_not_passed (test_bootstrap.BootstrapTest.test_force_keeps_project_id_when_not_passed) ... ok
test_force_preserves_existing_test_commands (test_bootstrap.BootstrapTest.test_force_preserves_existing_test_commands) ... ok
test_refuses_to_bootstrap_the_kit_source_repository (test_bootstrap.BootstrapTest.test_refuses_to_bootstrap_the_kit_source_repository) ... ok
test_ci_workflow_runs_sdd_checks (test_ci_contract.CiWorkflowTests.test_ci_workflow_runs_sdd_checks) ... ok
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
test_workflow_validate_errors (test_cli.WorkflowCliTests.test_workflow_validate_errors) ... ok
test_workflow_validate_json (test_cli.WorkflowCliTests.test_workflow_validate_json) ... ok
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
test_check_accepts_legacy_crlf_hash (test_sdd.ArtifactHashTests.test_check_accepts_legacy_crlf_hash) ... ok
test_check_ignores_line_ending_only_change (test_sdd.ArtifactHashTests.test_check_ignores_line_ending_only_change) ... ok
test_check_rejects_content_change_with_legacy_hash (test_sdd.ArtifactHashTests.test_check_rejects_content_change_with_legacy_hash) ... ok
test_check_rejects_text_change (test_sdd.ArtifactHashTests.test_check_rejects_text_change) ... ok
test_new_gate_hash_uses_lf (test_sdd.ArtifactHashTests.test_new_gate_hash_uses_lf) ... ok
test_text_hash_is_line_ending_stable (test_sdd.ArtifactHashTests.test_text_hash_is_line_ending_stable) ... ok
test_gate_reports_include_stable_ids (test_sdd.CheckRegistryTests.test_gate_reports_include_stable_ids) ... ok
test_registry_ids_are_unique (test_sdd.CheckRegistryTests.test_registry_ids_are_unique) ... ok
test_required_item_failure_blocks (test_sdd.CheckRegistryTests.test_required_item_failure_blocks) ... ok
test_allowed_paths_from_design_impact (test_sdd.ContextBundleTests.test_allowed_paths_from_design_impact) ... ok
test_bundle_excludes_other_specs (test_sdd.ContextBundleTests.test_bundle_excludes_other_specs) ... ok
test_bundle_is_read_only (test_sdd.ContextBundleTests.test_bundle_is_read_only) ... ok
test_non_task_step_returns_empty_bundle (test_sdd.ContextBundleTests.test_non_task_step_returns_empty_bundle) ... ok
test_task_step_returns_all_fields (test_sdd.ContextBundleTests.test_task_step_returns_all_fields) ... ok
test_delivery_confirmed_merged_spec_keeps_evidence_rules (test_sdd.EvidenceTests.test_delivery_confirmed_merged_spec_keeps_evidence_rules) ... ok
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
test_release_metadata_and_ci_contract (test_sdd.GateBoundaryTests.test_release_metadata_and_ci_contract) ... ok
test_waive_is_cli_only_human_action (test_sdd.GateBoundaryTests.test_waive_is_cli_only_human_action) ... ok
test_advisory_failure_warns (test_sdd.GateClassificationTests.test_advisory_failure_warns) ... ok
test_gate_report_renders_warn_and_block (test_sdd.GateClassificationTests.test_gate_report_renders_warn_and_block) ... ok
test_redline_cannot_be_waived (test_sdd.GateClassificationTests.test_redline_cannot_be_waived) ... ok
test_required_failure_blocks (test_sdd.GateClassificationTests.test_required_failure_blocks) ... ok
test_inbox_surfaces_gate_warnings (test_sdd.GateInboxMetricsTests.test_inbox_surfaces_gate_warnings) ... ok
test_legacy_report_rows_are_compatible (test_sdd.GateInboxMetricsTests.test_legacy_report_rows_are_compatible) ... ok
test_metrics_group_by_check_id (test_sdd.GateInboxMetricsTests.test_metrics_group_by_check_id) ... ok
test_invalid_registry_metadata_rejected (test_sdd.GateRegistryTests.test_invalid_registry_metadata_rejected) ... ok
test_legacy_ids_and_reports_supported (test_sdd.GateRegistryTests.test_legacy_ids_and_reports_supported) ... ok
test_registry_covers_all_gates (test_sdd.GateRegistryTests.test_registry_covers_all_gates) ... ok
test_active_waiver_downgrades_required_to_warn (test_sdd.GateWaiverTests.test_active_waiver_downgrades_required_to_warn) ... ok
test_expired_or_changed_artifact_revalidates (test_sdd.GateWaiverTests.test_expired_or_changed_artifact_revalidates) ... ok
test_waive_records_scope_and_approver (test_sdd.GateWaiverTests.test_waive_records_scope_and_approver) ... ok
test_waive_rejects_invalid_check_or_human (test_sdd.GateWaiverTests.test_waive_rejects_invalid_check_or_human) ... ok
test_recent_trailer_only_applies_to_active_specs (test_sdd.GitTrailerTests.test_recent_trailer_only_applies_to_active_specs) ... ok
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
test_pr_url_requires_delivery_confirmation (test_sdd.SddFlowTest.test_pr_url_requires_delivery_confirmation) ... ok
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
test_l2_refactor_flow (test_sdd.WorkflowProfileTests.test_l2_refactor_flow) ... ok
test_old_specs_stay_stable (test_sdd.WorkflowProfileTests.test_old_specs_stay_stable) ... ok
test_schema1_snapshot_unchanged (test_sdd.WorkflowProfileTests.test_schema1_snapshot_unchanged) ... ok
test_unknown_fields_report_paths (test_sdd.WorkflowProfileTests.test_unknown_fields_report_paths) ... ok
test_valid_v2_profile (test_sdd.WorkflowProfileTests.test_valid_v2_profile) ... ok
test_extra_human_checkpoint (test_sdd.WorkflowRuntimeTests.test_extra_human_checkpoint) ... ok
test_gate_checks_filter_advisory (test_sdd.WorkflowRuntimeTests.test_gate_checks_filter_advisory) ... ok
test_risk_and_context_rules (test_sdd.WorkflowRuntimeTests.test_risk_and_context_rules) ... ok
test_gate_or_checkpoint_conflict_rejected (test_sdd.WorkflowStageTests.test_gate_or_checkpoint_conflict_rejected) ... ok
test_invalid_stage_order_rejected (test_sdd.WorkflowStageTests.test_invalid_stage_order_rejected) ... ok
test_skip_design_stage (test_sdd.WorkflowStageTests.test_skip_design_stage) ... ok
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
test_permissions (test_site.PagesWorkflowTests.tes
... (truncated)
```

## 3. 结果

- 全量单元测试：166 passed，2 skipped（MCP SDK 未安装）。
- `python -m sdd verify-core`：passed。
- `python -m sdd verify-agent`：passed。
- Gate 分级、豁免、inbox 告警、按检查 ID 指标和 CLI/MCP 边界均有对应单元测试。
- `check --all --stage ci --check-git` 在进入 PR_READY 后作为最终 CI 门禁执行。

- Evidence recorded: Task T-005

### Task T-005

- At: 2026-11-23T18:16:36+08:00

GateBoundaryTests 2 passed; CiWorkflowTests 1 passed; full unittest 166 passed, 2 MCP SDK skipped; verify-core and verify-agent passed; version 0.9.5 with 44-file manifest

### Task T-004

- At: 2026-11-23T18:04:31+08:00

GateInboxMetricsTests: 3 passed; inbox/manual gate/metrics regressions and Gate suites: 17 passed total

### Task T-003

- At: 2026-11-23T17:57:02+08:00

python -m unittest tests.test_sdd.GateRegistryTests tests.test_sdd.GateClassificationTests tests.test_sdd.GateWaiverTests -v: 11 passed; py_compile and waive --help passed

### Task T-002

- At: 2026-11-23T17:37:08+08:00

GateClassificationTests: 4 passed; full-flow, delivery and strict workflow regressions: 3 passed

### Task T-001

- At: 2026-11-23T17:25:12+08:00

python -m unittest tests.test_sdd.GateRegistryTests -v: 3 passed; CheckRegistryTests regression 3 passed

## 4. 未运行

None。

## 5. AC 覆盖

| AC | 测试/证据 | 结果 |
|---|---|---|
| AC-001-1 | `GateRegistryTests#test_registry_covers_all_gates` | PASS |
| AC-001-2 | `GateRegistryTests#test_invalid_registry_metadata_rejected` | PASS |
| AC-001-3 | `GateRegistryTests#test_legacy_ids_and_reports_supported` | PASS |
| AC-002-1 | `GateClassificationTests#test_required_failure_blocks` | PASS |
| AC-002-2 | `GateClassificationTests#test_advisory_failure_warns` | PASS |
| AC-002-3 | `GateClassificationTests#test_redline_cannot_be_waived` | PASS |
| AC-002-4 | `GateClassificationTests#test_gate_report_renders_warn_and_block` | PASS |
| AC-003-1 | `GateWaiverTests#test_waive_records_scope_and_approver` | PASS |
| AC-003-2 | `GateWaiverTests#test_active_waiver_downgrades_required_to_warn` | PASS |
| AC-003-3 | `GateWaiverTests#test_expired_or_changed_artifact_revalidates` | PASS |
| AC-003-4 | `GateWaiverTests#test_waive_rejects_invalid_check_or_human` | PASS |
| AC-004-1 | `GateInboxMetricsTests#test_inbox_surfaces_gate_warnings` | PASS |
| AC-004-2 | `GateInboxMetricsTests#test_metrics_group_by_check_id` | PASS |
| AC-004-3 | `GateInboxMetricsTests#test_legacy_report_rows_are_compatible` | PASS |
| AC-005-1 | `GateBoundaryTests#test_waive_is_cli_only_human_action` | PASS |
| AC-005-2 | `GateBoundaryTests#test_release_metadata_and_ci_contract`；全量测试与核心/Agent 校验 | PASS |

## 6. Gate 5 结论

PASS。16 条 AC 均有通过的自动化测试或结构化命令证据；全量测试 166 passed，
2 个需要 MCP SDK 的用例因环境未安装而跳过。`verify-core`、`verify-agent`
和 `sdd verify` 均通过。

残余风险：Plan-Hash 仍只记录、尚未用于 G5 比对；Review overlay、知识索引和
BAR/Fix Pattern 属于后续 P1/P2 范围，不在本 Spec 内。
