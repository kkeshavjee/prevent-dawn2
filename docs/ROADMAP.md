# Supervisor Dependency Graph

> **Role:** Supervisor (Global Context)
> **Purpose:** Tracking all project tasks and their dependencies.
> **Rule:** Select "leaf nodes" (tasks with no un-met dependencies) for execution.

## Active Feature: Integration Tests
*   [/] **Plan & Design**
    *   [x] Select Task & Create Branch
    *   [x] Create refined implementation plan: [docs/plans/implementation_plan_integration_tests.md](docs/plans/implementation_plan_integration_tests.md)
    *   [ ] Read PRD Testing Requirements
*   [ ] **Implementation**
    *   [x] Create `tests/integration/` (Initial stubs completed)
    *   [x] Implement End-to-End API tests

## Completed Features
*   [x] **Integrate MCP Server**: [Issue #3](https://github.com/kkeshavjee/prevent-antigravity/issues/3)
*   [x] **State Machine**: [Issue #6](https://github.com/kkeshavjee/prevent-antigravity/issues/6)
*   [x] **State Machine**: [Issue #6](https://github.com/kkeshavjee/prevent-antigravity/issues/6) - Define Patient Journey states.
*   [x] **Refactor Project Structure**
*   [x] **Task Decoupled Planning (TDP)**
    *   [x] Protocol Definition & Verification
    *   [x] Supervisor Graph Published
*   [x] **Session Context System**
    *   [x] `docs/active_context.md` template
    *   [x] Workflow Guide
*   [x] **Multi-API Key Support**
    *   [x] Backend Config (`llm_config.py`, `main.py`)
    *   [x] Documentation (`Agent.md`, `README.md`)
*   [x] **Backend Fixes**
    *   [x] Startup Error (`aiosqlite`)
    *   [x] DB Initialization (`no such table`)
    *   [x] Data Validation (`current_agent=None`)

## Backlog / Future
## Backlog / Future Features

## Backlog / Future Features (Phased Graph)

> **Execution Rule:** Complete all tasks in Phase 1 before moving to Phase 2.

### Phase 1: Foundation (Infrastructure)
*   [x] **Integration Tests**: Comprehensive backend testing to ensure stability before adding agents.
*   [x] **Frontend Refactor**: Global "Prismatic" theme applied for UI consistency across all pages.
*   [ ] **Authentication & RBAC**: Secure the app before adding "Patient Matching".
*   [x] **Repository Pattern**: [Issue #7](https://github.com/kkeshavjee/prevent-antigravity/issues/7) - Abstract data access.
*   [x] **State Machine**: [Issue #6](https://github.com/kkeshavjee/prevent-antigravity/issues/6) - Define Patient Journey states.
*   [ ] **Orchestrator Mediator**: [Issue #5](https://github.com/kkeshavjee/prevent-antigravity/issues/5) - Decouple agent interactions.

### Phase 2: Core Interventions (The "Engage" Loop)
*   *Depends on: Phase 1 (Auth, State Machine)*
*   [ ] **Patient Matching**: [Issue #4](https://github.com/kkeshavjee/prevent-antigravity/issues/4) - Invitation codes for profile linking.
*   [ ] **API to Backend**: [Issue #15](https://github.com/kkeshavjee/prevent-antigravity/issues/15) - Expose DB safely.
*   [ ] **Reinforcement Learning**: Dynamically adapt motivation strategy based on user history.
*   [ ] **Gamified Education**: "Save a Character" scenarios.

### Phase 3: Advanced Agents (Specialization)
*   *Depends on: Phase 2 (Patient Matching)*
*   [ ] **Nutrition Agent**: Dietary advice and meal planning.
*   [ ] **Physical Activity Agent**: Exercise routines.
*   [ ] **Sleep & Stress Agents**: Specialized support.

### Phase 4: Expansion (Community & Intelligence)
*   *Depends on: Phase 3 (Agents)*
*   [ ] **Prescriptive Analytics**: Integration with external recommendation engine (The "Mall").
*   [ ] **Peer-to-Peer Agent**: Facilitate virtual support groups.
*   [ ] **Program Selection UI**: "Mall" interface.
*   [ ] **Mobile Application**: [Issue #14](https://github.com/kkeshavjee/prevent-antigravity/issues/14) - Capacitor/Native distribution.

### Phase 5: Advanced Engineering (Reliability & Patterns)
*   *Depends on: Phase 2 (Core)* - *Can run parallel to Phase 3/4*
*   [ ] **Circuit Breaker**: [Issue #8](https://github.com/kkeshavjee/prevent-antigravity/issues/8) - AI resilience.
*   [ ] **OpenTelemetry**: [Issue #9](https://github.com/kkeshavjee/prevent-antigravity/issues/9) - Distributed tracing.
*   [ ] **The Receipt**: [Issue #10](https://github.com/kkeshavjee/prevent-antigravity/issues/10) - Audit trail.
*   [ ] **The Bouncer**: [Issue #11](https://github.com/kkeshavjee/prevent-antigravity/issues/11) - Safety guardrail.
*   [ ] **The Fix Button**: [Issue #12](https://github.com/kkeshavjee/prevent-antigravity/issues/12) - User-driven correction.
*   [ ] **Privacy Scrubbing**: [MCP-PH-1] Ensure no PII is sent to cloud LLM.
*   [ ] **Audit Trail (The Receipt)**: [MCP-AT-1] Permanent record of all AI interactions.
*   [ ] **Observability Dashboard**: [Issue #16] Real-time visualization of system health, latency, and agent states.

### Phase 6: Clinical Validation
*   *Depends on: Phase 4 (Expansion)*
*   [ ] **Randomized Controlled Trials**: [Issue #13](https://github.com/kkeshavjee/prevent-antigravity/issues/13) - Validate feature efficacy.
