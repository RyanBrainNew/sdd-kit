# 外部 runner 接入契约验证报告

## 1. 元数据

| 项 | 内容 |
|---|---|
| Spec ID | SPEC-REQ-006 |
| 工作项 ID | SDD-RUNNER-001 |
| 作者 | SDD Agent |
| 创建日期 | 2026-11-24 |
| 验证时间 | 2026-11-24T12:00:19+08:00 |
| 验证范围 | 契约文档、入口链接、MCP 边界、发布元数据 |

## 2. 命令

- 全量测试命令：`python -m unittest discover -s tests -v`
- 核心与 Agent 校验：`python -m sdd verify-core`、`python -m sdd verify-agent`
- 结构化证据：`docs/specs/SPEC-REQ-006/verification-evidence.jsonl`

- Evidence recorded: Command: python -m unittest discover -s tests -v

### Command: python -m unittest discover -s tests -v

- At: 2026-11-24T12:10:19+08:00

- Command: `python -m unittest discover -s tests -v`
- CWD: `C:\Users\Administrator.SC-202402081735\orca\workspaces\sdd-kit\epic-sdd-l2`
- Exit: `0`

- Head: `eba230ad5f50`
- Plan-Hash: `sha256:1161b63d17aae3856a19ea97ca19614603f431b4651b1ba4307bb02ac82158a6`
- At: `2026-11-24T12:10:19+08:00`

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
[sdd] wrote sdd/manifest.json (version 0.9.6, 49 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] created AGENTS.md with the SDD managed block
[sdd] wrote sdd/manifest.json (version 0.9.6, 49 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] test commands: python -m unittest discover -s tests -v (override with --test-command)
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] AGENTS.md managed block already up to date
[sdd] wrote sdd/manifest.json (version 0.9.6, 49 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] test commands: python -m unittest discover -s tests -v (override with --test-command)
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] created AGENTS.md with the SDD managed block
[sdd] wrote sdd/manifest.json (version 0.9.6, 49 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] test commands: python -m unittest discover -s tests -v (override with --test-command)
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] updated the SDD managed block in AGENTS.md
[sdd] wrote sdd/manifest.json (version 0.9.6, 49 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] test commands: python -m unittest discover -s tests -v (override with --test-command)
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] created AGENTS.md with the SDD managed block
[sdd] wrote sdd/manifest.json (version 0.9.6, 49 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] test commands: python -m unittest discover -s tests -v (override with --test-command)
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] AGENTS.md managed block already up to date
[sdd] wrote sdd/manifest.json (version 0.9.6, 49 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] test commands: python -m unittest discover -s tests -v (override with --test-command)
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] created AGENTS.md with the SDD managed block
[sdd] wrote sdd/manifest.json (version 0.9.6, 49 files)

[sdd] bootstrap complete
[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)
[sdd] first spec: python -m sdd start-work --work-item srdcloud-123 --title "..." --json
[sdd] AGENTS.md managed block already up to date
[sdd] wrote sdd/manifest.json (version 0.9.6, 49 files)

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
test_context_bundle_schema (test_evolution.ContextBundleTests.test_context_bundle_schema) ... ok
test_context_empty_and_readonly (test_evolution.ContextBundleTests.test_context_empty_and_readonly) ... ok
test_context_patterns (test_evolution.ContextBundleTests.test_context_patterns)
[AC-009-2] [AC-009-4] 适用 Fix Pattern 自动带入，未验证模式只作参考。 ... ok
test_context_scope_guard (test_evolution.ContextBundleTests.test_context_scope_guard)
[AC-003-5] 超出允许范围时必须停止并扩大范围。 ... ok
test_agent_loop_and_version (test_evolution.DocsReleaseTests.test_agent_loop_and_version)
[AC-010-4] [AC-010-5] [AC-010-6] 版本、manifest、全量验收与单动作协议。 ... ok
test_standard_and_core_advantage_docs (test_evolution.DocsReleaseTests.test_standard_and_core_advantage_docs) ... ok
test_append_to_section_preserves_existing_content (test_evolution.EvidenceTests.test_append_to_section_preserves_existing_content) ... ok
test_context_bundle_schema (test_evolution.EvidenceTests.test_context_bundle_schema) ... ok
test_context_empty_and_readonly (test_evolution.EvidenceTests.test_context_empty_and_readonly) ... ok
test_context_patterns (test_evolution.EvidenceTests.test_context_patterns)
[AC-009-2] [AC-009-4] 适用 Fix Pattern 自动带入，未验证模式只作参考。 ... ok
test_context_scope_guard (test_evolution.EvidenceTests.test_context_scope_guard)
[AC-003-5] 超出允许范围时必须停止并扩大范围。 ... ok
test_fake_test_and_ac_tag (test_evolution.EvidenceTests.test_fake_test_and_ac_tag)
[AC-004-4] 注释或空测试中的 AC 标签不计为覆盖。 ... ok
test_scan_test_definitions_handles_multiline_strings (test_evolution.EvidenceTests.test_scan_test_definitions_handles_multiline_strings) ... ok
test_verify_records_and_g5_blocks (test_evolution.EvidenceTests.test_verify_records_and_g5_blocks)
[AC-004-5] 非零退出码或未执行命令不能作为 PASS 证据。 ... ok
test_block_cannot_complete (test_evolution.GateRegistryTests.test_block_cannot_complete)
[AC-006-3] 强制项失败时阻断状态迁移。 ... ok
test_registry_and_gate_output (test_evolution.GateRegistryTests.test_registry_and_gate_output)
[AC-001-4] [AC-006-1] Gate 注册表、报告分组与稳定检查 ID。 ... ok
test_conflict_blocks (test_evolution.KnowledgeTests.test_conflict_blocks)
[AC-008-4] 未解决冲突阻断相关任务。 ... ok
test_context_bundle_schema (test_evolution.KnowledgeTests.test_context_bundle_schema) ... ok
test_context_empty_and_readonly (test_evolution.KnowledgeTests.test_context_empty_and_readonly) ... ok
test_context_patterns (test_evolution.KnowledgeTests.test_context_patterns)
[AC-009-2] [AC-009-4] 适用 Fix Pattern 自动带入，未验证模式只作参考。 ... ok
test_context_scope_guard (test_evolution.KnowledgeTests.test_context_scope_guard)
[AC-003-5] 超出允许范围时必须停止并扩大范围。 ... ok
test_knowledge_index_and_pattern (test_evolution.KnowledgeTests.test_knowledge_index_and_pattern)
[AC-008-1] [AC-008-2] [AC-008-3] [AC-008-5] [AC-009-3] 知识记录与 Pattern 闭环。 ... ok
test_append_to_section_preserves_existing_content (test_evolution.MetricsTests.test_append_to_section_preserves_existing_content) ... ok
test_context_bundle_schema (test_evolution.MetricsTests.test_context_bundle_schema) ... ok
test_context_empty_and_readonly (test_evolution.MetricsTests.test_context_empty_and_readonly) ... ok
test_context_patterns (test_evolution.MetricsTests.test_context_patterns)
[AC-009-2] [AC-009-4] 适用 Fix Pattern 自动带入，未验证模式只作参考。 ... ok
test_context_scope_guard (test_evolution.MetricsTests.test_context_scope_guard)
[AC-003-5] 超出允许范围时必须停止并扩大范围。 ... ok
test_fake_test_and_ac_tag (test_evolution.MetricsTests.test_fake_test_and_ac_tag)
[AC-004-4] 注释或空测试中的 AC 标签不计为覆盖。 ... ok
test_metrics_and_audit (test_evolution.MetricsTests.test_metrics_and_audit)
[AC-006-7] [AC-009-5] [AC-010-2] 指标、审计回放与迁移事件。 ... ok
test_scan_test_definitions_handles_multiline_strings (test_evolution.MetricsTests.test_scan_test_definitions_handles_multiline_strings) ... ok
test_verify_records_and_g5_blocks (test_evolution.MetricsTests.test_verify_records_and_g5_blocks)
[AC-004-5] 非零退出码或未执行命令不能作为 PASS 证据。 ... ok
test_omitted_or_empty_gate_checks_fall_back_to_full_gate (test_evolution.ProfileTests.test_omitted_or_empty_gate_checks_fall_back_to_full_gate) ... ok
test_profile_errors_and_snapshot (test_evolution.ProfileTests.test_profile_errors_and_snapshot)
[AC-005-5] [AC-010-1] 安全必需检查不可移除，旧快照继续运行。 ... ok
test_profile_v2_and_refactor (test_evolution.ProfileTests.test_profile_v2_and_refactor)
[AC-010-3] 旧 JSON 字段兼容与新 Profile 预设生效。 ... ok
test_overlays_and_review_policy (test_evolution.ReviewTests.test_overlays_and_review_policy)
[AC-007-1] [AC-007-4] [AC-007-6] overlay 选择、无 finding 声明与边界。 ... ok
test_review_findings_and_overlays (test_evolution.ReviewTests.test_review_findings_and_overlays)
[AC-007-2] [AC-007-5] finding 九字段校验与三类 overlay 结构。 ... ok
test_review_required (test_evolution.ReviewTests.test_review_required)
[AC-007-3] [AC-007-4] medium/high 风险强制独立 Review。 ... ok
test_feat_and_prd_chain (test_evolution.TraceabilityTests.test_feat_and_prd_chain) ... ok
test_g0_g1_separate (test_evolution.TraceabilityTests.test_g0_g1_separate) ... ok
test_orphans_and_duplicate_feat (test_evolution.TraceabilityTests.test_orphans_and_duplicate_feat) ... ok
test_expired_waiver_blocks_again (test_evolution.WaiverTests.test_expired_waiver_blocks_again) ... ok
test_security_redline (test_evolution.WaiverTests.test_security_redline)
[AC-006-6] 安全红线检查拒绝人工豁免。 ... ok
test_spec_scope_does_not_cover_verification (test_evolution.WaiverTests.test_spec_scope_does_not_cover_verification) ... ok
test_warn_and_waiver_lifecycle (test_evolution.WaiverTests.test_warn_and_waiver_lifecycle)
[AC-004-6] [AC-006-2] [AC-006-4] [AC-006-5] warn、豁免字段、到期与范围。 ... ok
test_approve_records_digest_and_gate_report (test_governance.ApprovalBindingTests.test_approve_records_digest_and_gate_report)
[AC-001-1] approve 写入审批摘要，并同步到 G0/G1 报告。 ... ok
test_legacy_active_spec_without_digest_blocks (test_governance.ApprovalBindingTests.test_legacy_active_spec_without_digest_blocks)
[AC-001-4] 活跃 Spec 缺审批摘要时给出迁移命令。 ... ok
test_reapprove_requires_human_and_reason (test_governance.ApprovalBindingTests.test_reapprove_requires_human_and_reason)
[AC-001-4] reapprove 缺 human 或理由为空时拒绝。 ... ok
test_spec_change_blocks_until_reapprove (test_governance.ApprovalBindingTests.test_spec_change_blocks_until_reapprove)
[AC-001-2] [AC-001-3] 审批后修改 Spec 触发 G1-08，reapprove 后恢复。 ... ok
test_ci_blocks_pending_change (test_governance.ChangeEnforcementTests.test_ci_blocks_pending_change)
[AC-003-3] 普通 stage 检查同样报告 G1-09。 ... ok
test_docs_only_allows_docs_but_blocks_code (test_governance.ChangeEnforcementTests.test_docs_only_allows_docs_but_blocks_code)
[AC-003-4] docs-only 放行文档提交但阻断代码提交。 ... ok
test_pending_change_blocks_code_commit (test_governance.ChangeEnforcementTests.test_pending_change_blocks_code_commit)
[AC-003-3] pending change-set 阻断暂存代码的 pre-commit。 ... ok
test_change_writes_required_fields (test_governance.ChangeSetTests.test_change_writes_required_fields)
[AC-003-1] change 生成完整 change-set 记录。 ... ok
test_docs_only_change_is_explicit_exemption (test_governance.ChangeSetTests.test_docs_only_change_is_explicit_exemption)
[AC-003-4] docs-only 显式豁免且不要求 reapprove。 ... ok
test_invalid_change_reference_fails (test_governance.ChangeSetTests.test_invalid_change_reference_fails)
[AC-003-5] change-set 引用不存在 AC 时失败且不落盘。 ... ok
test_reapprove_marks_change_approved (test_governance.ChangeSetTests.test_reapprove_marks_change_approved)
[AC-003-2] reapprove 将 pending change-set 标记为 approved。 ... ok
test_separator_rows_are_not_treated_as_data (test_governance.FeatMapSyncTests.test_separator_rows_are_not_treated_as_data)
[AC-004-2] FEAT 映射重复同步不能累积分隔行。 ... ok
test_merged_legacy_spec_is_compatible (test_governance.GovernanceBoundaryTests.test_merged_legacy_spec_is_compatible)
[AC-004-2] MERGED 历史 Spec 缺摘要时不阻断。 ... ok
test_reapprove_is_cli_only_human_action (test_governance.GovernanceBoundaryTests.test_reapprove_is_cli_only_human_action)
[AC-004-1] reapprove 只允许 CLI 人工动作。 ... ok
test_release_metadata_matches_package_version (test_governance.GovernanceBoundaryTests.test_release_metadata_matches_package_version)
[AC-004-3] 发布版本文件与核心版本常量一致。 ... ok
test_approval_required_combinations (test_governance.ImpactTests.test_approval_required_combinations)
[AC-002-3] pending change-set 或摘要变化时要求审批。 ... ok
test_impact_lists_links_and_paths (test_governance.ImpactTests.test_impact_lists_links_and_paths)
[AC-002-1] impact 输出 FEAT/FR/AC/Task/测试/路径。 ... ok
test_impact_reports_missing_links (test_governance.ImpactTests.test_impact_reports_missing_links)
[AC-002-2] change-set 引用不存在 AC 时 impact 输出 missing。 ... ok
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
test_contract_assigns_runtime_to_runner (test_runner_contract.ContractDocumentTests.test_contract_assigns_runtime_to_runner) ... ok
test_contract_covers_result_states (test_runner_contract.ContractDocumentTests.test_contract_covers_result_states) ... ok
test_contract_forbids_human_actions (test_runner_contract.ContractDocumentTests.test_contract_forbids_human_actions) ... ok
test_contract_has_required_phases (test_runner_contract.ContractDocumentTests.test_contract_has_required_phases) ... ok
test_contract_maps_each_phase_to_cli (test_runner_contract.ContractDocumentTests.test_contract_maps_each_phase_to_cli) ... ok
test_examples_use_public_cli_only (test_runner_contract.ContractDocumentTests.test_examples_use_public_cli_only) ... ok
test_readme_links_runner_contract (test_runner_contract.EntryPointTests.test_readme_links_runner_contract) ... ok
test_mcp_exposes_no_human_actions (test_runner_contract.ReleaseBoundaryTests.test_mcp_exposes_no_human_actions) ... ok
test_check_accepts_legacy_crlf_hash (test_sdd.ArtifactHashTests.test_check_accepts_legacy_crlf_hash) ... ok
test_check_ignores_line_ending_only_change (test_sdd.ArtifactHashTests.test_check_ignores_line_ending_only_change) ... ok
test_
... (truncated)
```

### Command: python -m unittest discover -s tests -v

- Command: `python -m unittest discover -s tests -v`
- CWD: `C:\Users\Administrator.SC-202402081735\orca\workspaces\sdd-kit\epic-sdd-l2`
- Exit: `0`
- Head: `eba230ad5f50`
- Plan-Hash: `sha256:1161b63d17aae3856a19ea97ca19614603f431b4651b1ba4307bb02ac82158a6`
- At: `2026-11-24T12:00:19+08:00`
- Timed out: `false`

```text
[sdd] run: python -m unittest discover -s tests -v
[sdd] SPEC-REQ-006 verify passed
```

完整 stdout/stderr 与退出码记录在
`docs/specs/SPEC-REQ-006/verification-evidence.jsonl`，run_id 与上方时间对应。

## 3. 结果

本轮验证覆盖契约结构、失败语义、人工边界、入口链接和 MCP 暴露面。

### Task 证据

- T-001：`python -m unittest tests.test_runner_contract.ContractDocumentTests -v`，6 passed。
- T-002：`python -m unittest tests.test_runner_contract.EntryPointTests -v`，1 passed。
- T-003：`python -m unittest tests.test_runner_contract.ReleaseBoundaryTests tests.test_sdd.GateBoundaryTests -v`，3 passed。

### 全量结果

- `python -m unittest discover -s tests -v`：237 项通过，2 个 MCP SDK 用例按既有约定跳过。
- `python -m sdd verify-core`：passed。
- `python -m sdd verify-agent`：passed。
- LF 检出工作区（detached `eba230a`，`.gitattributes` 强制 `eol=lf`）复核：
  `verify-core` 与 `verify-agent` 均通过，`git status -s` 为空。

## 4. 未运行

None。未执行容器化 runner、外部 CI 厂商接入或客户端浏览器人工评审，
这些均不在本 Spec 范围内。

## 5. AC 覆盖

| AC | 测试/证据 | 结果 |
|---|---|---|
| AC-001-1 | `ContractDocumentTests#test_contract_has_required_phases` | PASS |
| AC-001-2 | `ContractDocumentTests#test_contract_maps_each_phase_to_cli` | PASS |
| AC-001-3 | `ContractDocumentTests#test_examples_use_public_cli_only` | PASS |
| AC-002-1 | `ContractDocumentTests#test_contract_covers_result_states` | PASS |
| AC-002-2 | `ContractDocumentTests#test_contract_forbids_human_actions` | PASS |
| AC-002-3 | `ContractDocumentTests#test_contract_assigns_runtime_to_runner` | PASS |
| AC-003-1 | `EntryPointTests#test_readme_links_runner_contract` | PASS |
| AC-003-2 | `ReleaseBoundaryTests#test_mcp_exposes_no_human_actions` + `verify-core` | PASS |
| AC-003-3 | `GateBoundaryTests#test_release_metadata_and_ci_contract` + `verify-core` | PASS |

## 6. Gate 5 结论

PASS。契约文档覆盖七阶段生命周期、四类返回语义、六个人工动作禁止清单和
runner 自有容器职责，入口链接与结构测试齐全；未修改状态机、MCP 实现或
受保护发布文件。残余风险是契约属于文档约束，实际 runner 的容器编排与
重试策略仍需由接入方自行实现并评审。
