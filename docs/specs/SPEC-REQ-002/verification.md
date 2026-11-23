# 工作流 Profile v2：可声明扩展与 workflow validate验证报告

## 1. 元数据

| 项 | 内容 |
|---|---|
| Spec ID | SPEC-REQ-002 |
| 工作项 ID | SDD-PROFILE-001 |
| 作者 | SDD Agent |
| 创建日期 | 2026-11-23T14:33:04+08:00 |
| 验证时间 | 2026-11-23T15:50:00+08:00 |

## 2. 命令

- Evidence recorded: Command: python -m unittest discover -s tests -v

### Command: python -m unittest discover -s tests -v

- At: 2026-11-23T15:58:23+08:00

- Command: `python -m unittest discover -s tests -v`
- CWD: `C:\Users\Administrator.SC-202402081735\orca\workspaces\sdd-kit\epic-sdd-l2`
- Exit: `0`

- Head: `25b5303d3ab0`
- Plan-Hash: `sha256:8fc08539b2e828881746c6826fd185fc256e9546b5717f2bf2723fc9b26425e3`
- At: `2026-11-23T15:58:23+08:00`

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
[sdd] wrote sdd/manifest.json (version 0.9.4, 44 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] created AGENTS.md with the SDD managed block
[sdd] wrote sdd/manifest.json (version 0.9.4, 44 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] test commands: python -m unittest discover -s tests -v (override with --test-command)
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] AGENTS.md managed block already up to date
[sdd] wrote sdd/manifest.json (version 0.9.4, 44 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] test commands: python -m unittest discover -s tests -v (override with --test-command)
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] created AGENTS.md with the SDD managed block
[sdd] wrote sdd/manifest.json (version 0.9.4, 44 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] test commands: python -m unittest discover -s tests -v (override with --test-command)
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] updated the SDD managed block in AGENTS.md
[sdd] wrote sdd/manifest.json (version 0.9.4, 44 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] test commands: python -m unittest discover -s tests -v (override with --test-command)
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] created AGENTS.md with the SDD managed block
[sdd] wrote sdd/manifest.json (version 0.9.4, 44 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] test commands: python -m unittest discover -s tests -v (override with --test-command)
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] AGENTS.md managed block already up to date
[sdd] wrote sdd/manifest.json (version 0.9.4, 44 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] test commands: python -m unittest discover -s tests -v (override with --test-command)
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] created AGENTS.md with the SDD managed block
[sdd] wrote sdd/manifest.json (version 0.9.4, 44 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] AGENTS.md managed block already up to date
[sdd] wrote sdd/manifest.json (version 0.9.4, 44 files)

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
test_permissions (test_site.PagesWorkflowTests.test_permissions) ... ok
test_relative_site_assets (test_site.PagesWorkflowTests.test_relative_site_assets)
[AC-005-2] 子路径部署下不能出现根路径资源。 ... ok
test_triggers (test_site.PagesWorkflowTests.test_triggers) ... ok
test_uploads_site_only (test_site.PagesWorkflowTests.test_uploads_site_only)
[AC-005-1] 只允许把 site/ 作为 Pages 制品。 ... ok
test_doc_nav (test_site.ReadmeTests.test_doc_nav)
[AC-003-3] 深文档入口必须齐全。 ... ok
test_docs_directory_map (test_site.ReadmeTests.test_docs_directory_map)
README 必须解释 docs/ 与生成工件的位置。 ... ok
test_header (test_site.ReadmeTests.test_header)
[AC-003-1] 前 40 行必须有名称、定位、徽章和两个入口。 ... ok
test_issue_roadmap (test_site.ReadmeTests.test_issue_roadmap)
未开发能力必须能从 README 跳到对应 Issue。 ... ok
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
test_relative_assets (t
... (truncated)
```

## 3. 结果

- schema 2 校验、阶段子序列、运行时规则、CLI 与 l2-refactor 预设的单元测试全部通过。
- 全量单元测试见第 2 节 `sdd verify` 的退出码与输出。
- `python -m sdd verify-core`、`python -m sdd verify-agent`、
  `python -m sdd check --all --stage ci --check-git` 在 LF 工作区通过。
- 历史 `SPEC-DEVTOOLS-002`、`SPEC-REQ-001` 的 workflow 快照 digest 未变化。

## 4. 未运行

- 本地未安装 `mcp` SDK 时，2 个 MCP 相关用例会跳过；GitHub Actions 安装
  `sdd/mcp/requirements.txt` 后执行。
- 未执行 `upgrade-workflow`；本 Spec Out-of-Scope。
- 未实现 warn/waiver、Review overlay、知识索引和 BAR/Fix Pattern；属于 issue #7
  的后续 P1/P2 工作。

## 5. AC 覆盖

| AC | 测试/证据 | 结果 |
|---|---|---|
| AC-001-1 | `WorkflowProfileTests#test_valid_v2_profile`：合法 v2 profile 校验通过并返回稳定 digest | PASS |
| AC-001-2 | `WorkflowProfileTests#test_unknown_fields_report_paths`、`WorkflowCliTests#test_workflow_validate_errors`：未知字段带路径报错 | PASS |
| AC-001-3 | `WorkflowProfileTests#test_schema1_snapshot_unchanged`、`test_old_specs_stay_stable`：schema 1 校验与 digest 不变 | PASS |
| AC-002-1 | `WorkflowStageTests#test_skip_design_stage`：省略 `DESIGN_READY` 后直接进入 `TASKS_READY` | PASS |
| AC-002-2 | `WorkflowStageTests#test_gate_or_checkpoint_conflict_rejected`：删除强制 Gate 或 approve/merge 被拒绝 | PASS |
| AC-002-3 | `WorkflowStageTests#test_invalid_stage_order_rejected`：重复、逆序、缺首尾阶段带索引报错 | PASS |
| AC-003-1 | `WorkflowRuntimeTests#test_gate_checks_filter_advisory`：裁剪 advisory、保留 required | PASS |
| AC-003-2 | `WorkflowRuntimeTests#test_extra_human_checkpoint`：额外 G3 人工检查点阻止自动完成 | PASS |
| AC-003-3 | `WorkflowRuntimeTests#test_risk_and_context_rules`：risk_stop 并集与 context_rules 裁剪/越界拒绝 | PASS |
| AC-004-1 | `WorkflowCliTests#test_workflow_validate_json`：合法 profile 返回 0 与 name/version/digest | PASS |
| AC-004-2 | `WorkflowCliTests#test_workflow_validate_errors`：缺失/非 JSON/未知字段返回非 0 且不写状态 | PASS |
| AC-005-1 | `WorkflowProfileTests#test_l2_refactor_flow`：l2-refactor 快照正确并可到 `PR_READY` | PASS |
| AC-005-2 | `WorkflowProfileTests#test_old_specs_stay_stable` + `check --all`：旧 Spec 快照与 Gate 结果不变 | PASS |
| AC-005-3 | `CiWorkflowTests#test_ci_workflow_runs_sdd_checks` + LF 工作区三项门禁 | PASS |

## 6. Gate 5 结论

PASS。schema 2 能力、CLI 和 l2-refactor 预设均有可复验测试；旧 schema 1 快照
保持兼容。残余风险是 `upgrade-workflow` 与 warn/waiver 等后续能力尚未实现，
已明确排除在本 Spec 范围外。

## 7. 独立审查

| 项 | 内容 |
|---|---|
| Reviewer | 独立审查会话（只读复核，非实现会话） |
| Session | review-spec-req-002 |
| Model | Codex 独立会话 |
| Findings | 复核 schema 2 校验、阶段跳过、gate_checks、human_checkpoints、risk_stop 与 context_rules。发现并修复四处问题：站点与 README 版本徽章仍停留在 0.9.3、验证报告残留失败命令证据、`sdd/scripts/sdd.py` 的 `VERSION` 常量落后于 `sdd/VERSION`、legacy Spec 无 workflow 时 `resolve_workflow` 引用未定义的 `config`。修复后重新执行全量验证，未发现新的阻断项。 |
| Blocking issues | none |
