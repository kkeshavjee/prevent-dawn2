# Contributing to PREVENT Dawn

Welcome! This guide outlines our development workflow and standards to help us build a secure, personalized diabetes prevention platform.

## Branching Strategy

We follow a **Feature Branching** model. Always branch from `main` and use descriptive prefixes:

- `feature/`: New features
- `fix/`: Bug fixes
- `docs/`: Documentation updates
- `chore/`: Maintenance tasks
- `main`: The stable baseline. All code here should be production-ready and clinical-grade. **Direct pushes are disabled; changes require an authorized Pull Request and Review.**

## Development Standard: Task Decoupled Planning (TDP)

We follow the **TDP Protocol** to ensure reliability.
*   **Read the Protocol:** [docs/process/TDP_DEV_PROTOCOL.md](docs/process/TDP_DEV_PROTOCOL.md)
*   **Core Rule:** Never stick to a "Think & Act" loop. Always **Plan** (create `implementation_plan.md`) -> **Execute** -> **Verify**.

## Development Workflow

1.  **Requirement Review**: Check [PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md) and the corresponding GitHub Issue.
2.  **Implementation Plan**: For major features, draft an implementation plan (as an `.md` file) and get feedback.
3.  **Branching**: Create your feature branch from `main`.
4.  **Commits**: Use clear, concise commit messages.
    - Example: `feat: add Q-learning service to motivation agent`
    - Example: `docs: update deployment instructions in README`
5.  **Pull Requests**: Open a Draft PR if work is in progress. Link the PR to relevant GitHub Issues.

## Communication

- **Supervisor Graph**: Use `docs/ROADMAP.md` to track dependencies and select the next task.
- **Session Continuity**: Use `docs/active_context.md` to save/restore context. See [Session Workflow](docs/guides/SESSION_WORKFLOW.md).
    - **Note**: Do not commit the populated `active_context.md` file. It is local-only and ignored by git to keep the repo clean.
- **Project Tasks**: See the `docs/ROADMAP.md` file for a project‑wide task board.
- **Specifications**: High-level vision lives in the PRD. Granular technical discussions happen within GitHub Issues.
- **Reviews**: All code must be reviewed via Pull Request before merging to `main`.

## Security & Privacy by Design (PbD)

As a digital health intervention, **privacy and security are core design pillars**. We follow the **7 Principles of Privacy by Design**:

1. **Proactive not Reactive**: Read the full spec in [docs/concepts/CONCEPT_005_PRIVACY_BY_DESIGN.md](docs/concepts/CONCEPT_005_PRIVACY_BY_DESIGN.md).
2. **Pseudonymity Rule**: Never design features that require or ingest real names, emails, or phone numbers from external health networks (OHN). Use the `PREVENT_ID` and user-provided nicknames only.
3. **Data Minimization**: Only process the clinical variables necessary for the user's current stage of change.
4. **Transparency**: All AI agents must disclose their nature as an AI assistant.
