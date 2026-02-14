# Agent Knowledge Base (`Agent.md`)

This document serves as a persistent memory for the AI agent to store learnings, architectural decisions, and common pitfalls encountered during the development of **Antigravity**.

## Foundation Phase: Lessons Learned (Issues #6 & #3)
- **Architectural Decoupling**: 
    - **State Machine**: Flow logic belongs in a dedicated model (`state_machine.py`), not the Orchestrator. This makes logic testable and prevents "AI progress hallucinations."
    - **MCP Server**: Context management is a system-level concern. Centralizing it in `mcp_server.py` reduces agent complexity and ensures a "Single Source of Truth."
- **Reliability principle**: Designing for failure (exponential backoff/retries) is as critical as designing for success.
- **Production Mindset**: 
    - **Pseudonymity**: The app operates on a "Zero-external-PII" baseline. No real names or contact info are ingested. Identification relies on anonymous IDs and user-chosen nicknames.
    - **Observability**: Always track latency for external calls (LLMs/Databases).
    - **Guardrails**: Validate AI output "shape" against strictly defined Signatures before processing.

## 0. Prime Directive: Task Decoupled Planning
**Protocol:** [docs/process/TDP_DEV_PROTOCOL.md](file:///c:/Users/Karim%20Keshavjee/Documents/Antigravity/docs/process/TDP_DEV_PROTOCOL.md)
*   **Isolate Context:** Do not rely on deep chat history. Use `active_context.md`.
*   **Plan First:** Never write code without an `implementation_plan.md` for the specific task node.
*   **Local Repair:** If execution fails, fix it within the scope of the current node. Do not hallucinate global changes.

## 1. Backend Architecture & Stability
- **Response Handling**: The backend `chat` endpoint must *always* defensively handle the response from the Orchestrator/Agents. `dspy` or the underlying LLM can sometimes return complex objects (like `Prediction` or streaming chunks) instead of plain strings.
    - **Fix**: Logic was added to `backend/main.py` to check types and explicitly convert non-string responses to strings before returning to the frontend.
- **Model Selection & Rate Limits**: 
    - The `gemini-2.5-flash` (and `2.0` variants like `lite`, `exp`) have very strict free tier quotas (often 10-20 requests/day or low token limits).
    - **Learnings**: 
        - `gemini-1.5-flash` (or `gemini-1.5-flash-latest`) is often more stable for free tiers, but finding the exact string identifier is critical to avoid 404s.
    - **Solution**: Experiment to find the stable legacy model string (e.g., `gemini-1.5-flash-latest`).
    - **Error Handling**: The backend should catch `429` errors and return a user-friendly "System is busy" message rather than crashing or showing a 500 error.
- **Data Models**: 
    - Endpoints like `/api/patient/lookup` must return the data model expected by the frontend (e.g., `PatientProfile`), not the generic `OrchestratorResponse`. Mismatches cause 500 errors.

## 2. Frontend Patterns
- **API Error Handling**: The frontend `Chat.tsx` handles API errors by displaying them as "System Messages" in the chat. This is good for debugging but should be made more user-friendly for production (e.g., "The assistant is momentarily unavailable").

## 3. Development Workflow
- **Verification**: Always verify backend changes with a standalone script (e.g., `test_backend_full.py`) independent of the frontend to isolate issues.
- **Logs**: Backend logs (`uvicorn`) are the source of truth for 500 errors. Always check them first.
- **Documentation Persistence**: Important architectural plans (e.g., Task Decoupled Planning) and decisions must be saved in this `Agent.md` file or clearly referenced in `docs/ROADMAP.md` to prevent loss. Do not rely on ephemeral chat history.

## 4. Session Context Management
- **The Context Gap**: Without a persistent context file, the agent loses track of "where we left off" between sessions, leading to redundant explanations or loss of architectural intent.
- **The Solution**: Use `docs/active_context.md` as a volatile but persistent memory slot.
    - **Workflow**: 
        - **Shutdown**: Assistant summarizes state into `active_context.md` (overwriting it).
        - **Startup**: Assistant reads `active_context.md` to prime its context window.
    - **Repo Hygiene**: This file is `.gitignore`'d to prevent constant churn in the git history. Only the *template* and *workflow guide* should be committed.
- **4.3. Session Recovery Pitfalls**:
    - **Gitignore Tool Block**: Standard file-viewing tools (`view_file`) respect `.gitignore`. If `active_context.md` is ignored, the agent *cannot* read it with standard tools. 
        - **Resolution**: Use `run_command` (`type` or `Get-Content`) to read ignored context files.
    - **Atomic Housekeeping**: "Deleting" a file in a conversation is not the same as deleting it on disk. If a session ends abruptly, housekeeping tasks (like removing `project_tasks.md`) might be lost.
        - **Resolution**: Always verify filesystem state at the start of a session, regardless of what the chat history or `ROADMAP.md` claims.

## 5. Troubleshooting Guides

### 5.1. Network Error Diagnosis Tree
If you see "Error: Network Error" in the chat, follow this flow:

```mermaid
graph TD
    A[Error: Network Error] --> B{Is Vite Proxy Configured?}
    B -- No --> C[CRITICAL: Enable Proxy in vite.config.ts]
    B -- Yes --> D{Is Backend Running?}
    D -- No --> E[Start Backend via start_app.bat]
    D -- Yes --> F{Is Error Constant?}
    
    F -- Intermittent --> G[Auto-Reload (Wait 5s)]
    F -- Constant --> H{Check Console for CORS/IP Issues}
    H --> I[Fix: Use Relative Paths in client.ts]
```

### 4.2. Root Cause & Solution Patterns
1.  **The "Localhost" Trap**: Hardcoding `http://127.0.0.1:8000` in the frontend client fails on mobile devices...
2.  **The Proxy Solution**: Always configure `vite.config.ts` to proxy `/api` requests...
3.  **Auto-Reload**: While `uvicorn` reloads do cause momentary outages...
4.  **Missing Dependencies**: If backend fails with `ModuleNotFoundError: No module named 'aiosqlite'`, it means `backend/requirements.txt` was updated but the venv is stale. Run `pip install -r backend/requirements.txt` (or specifically `pip install aiosqlite`).

## 5. Operational Commands
These commands are stored here for the Agent to execute upon request.

### 5.1. API Key Switching
*   **Switch to Secondary Key**:
    ```bash
    curl.exe -X POST "http://127.0.0.1:8000/api/config/key" -H "Content-Type: application/json" -d "{ \"key_type\": \"secondary\" }"
    ```
*   **Switch to Primary Key**:
    ```bash
    curl.exe -X POST "http://127.0.0.1:8000/api/config/key" -H "Content-Type: application/json" -d "{ \"key_type\": \"primary\" }"
    ```

## 6. Patient Journey State Machine
- **Role**: Externalizes the flow logic from the Orchestrator. 
- **Implementation**: `backend/models/state_machine.py`.
- **Constraint**: All state transitions *must* pass through `JourneyManager.transition()`.
- **Principle**: The bot cannot "hallucinate" progress. If a move is illegal (e.g., from Inform to Sustain), the code blocks it and raises an `InvalidStateTransitionError`.

## 7. MCP Server (Model Context Protocol)
- **Role**: A centralized gateway for all LLM calls.
- **Implementation**: `backend/mcp_server/mcp_server.py`.
- **Key Features**:
    - **Context Injection**: Automatically injects `PatientProfile` and `history` into every call.
    - **Resilience**: Uses `tenacity` for exponential backoff (retries) on API failure or rate limits (429).
    - **Observability**: Logs latency for every request to monitor system health.
- **Signature Support**: Supports mapping `user_profile`, `user_context`, and `history` fields automatically.

## 8. Testing Statefull Singletons
- **The Issue**: Singleton objects (like the `Orchestrator`) that hold state (like database locks or user sessions) persist across `pytest` tests, even though `pytest` creates a new event loop for each test. This causes `RuntimeError: Lock bound to different loop`.
- **The Solution**:
    1.  **Lazy Locking**: Do not initialize `asyncio.Lock` in `__init__`. Use a `@property` that creates it on first access.
    2.  **Fixture Reset**: In `conftest.py`, explicitly clear the singleton's state (`orchestrator.states = {}`) AND nullify the lock (`orchestrator.persistence._lock = None`) before every test. This forces the lazy property to create a *new* lock bound to the *current* test's event loop.
- **Mocking**: When mocking methods on a singleton, do not patch the class or module if the instance already exists. Patch the *instance method* directly (e.g., `patch.object(orchestrator.mcp_server, 'predict')`). If the method is `async`, ensure the mock returns an awaitable or use `AsyncMock`.

## 9. Agent Logic & Infinite Loops
- **The Trap**: An Agent (like the `IntakeAgent`) runs in a loop where it checks state, sends a response, and processes intent. If state flags (like "known name") are checked unconditionally (e.g., every time a user message is received), it can create an infinite loop of "Welcome Back" messages even in the middle of a conversation.
- **The Fix**:
    - **State Flags**: Use transient context variables (e.g., `greeting_completed`) to track if a specific logic block has already executed for the session.
    - **Guard Clauses**: Wraps logic blocks in checks like `if known_user and not greeting_completed`.
    - **Pre-seeding Tests**: Tests should pre-seed the database with valid state (including flags if necessary) to test "mid-stream" scenarios (e.g., Known User continues conversation) without triggering startup logic.
