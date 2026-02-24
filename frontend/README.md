# CoAgent Studio — Frontend

Vue 3 SPA providing a visual AI agent orchestration interface: a drag-and-drop Workflow Studio, a Trigger Policy manager, real-time collaborative rooms, and an interactive Knowledge Graph powered by the GraphRAG Analytics Agent.

## Tech Stack

| Concern | Technology |
|---|---|
| Framework | Vue 3 (Composition API + `<script setup>`) + TypeScript |
| Build | Vite 7 |
| Styling | Tailwind CSS + DaisyUI |
| State | Pinia (global) + Composables (local logic) |
| Routing | Vue Router 4 (with auth + role guards) |
| Workflow Canvas | Vue Flow (node-based graph editor) |
| Rich Text | Tiptap |
| Knowledge Graph | Native Canvas (force-directed, no external lib) |
| HTTP Client | Axios (with auto-retry on 401) |
| Real-time | Native WebSockets (`useWebSocket` composable) |
| Type Check | vue-tsc (strict mode) |
| Lint/Format | ESLint + Prettier |

---

## Project Structure

```
src/
├── api.ts                   # Axios instance + global interceptors (401 refresh, 403/500 toast)
├── router/
│   └── index.ts             # Routes: /studio/workflows, /studio/triggers, /rooms/:id/workflow, …
├── stores/
│   ├── auth.ts              # User session, impersonation state
│   ├── workspace.ts         # Artifacts (kanban, docs, processes) with optimistic updates
│   └── toast.ts             # Global notification store
├── composables/
│   ├── useWebSocket.ts      # WS lifecycle with exponential-backoff reconnect + auto-cleanup
│   ├── useRoomChat.ts       # Chat messages, WS connection, A2A trace handling
│   ├── useAuth.ts           # Login, logout, impersonation actions
│   ├── useDesignAgent.ts    # Agent version control + design state
│   └── usePermissions.ts    # Per-component RBAC helper functions
├── services/
│   ├── workflowService.ts   # Global /workflows CRUD + /triggers CRUD + legacy room API
│   ├── graphService.ts      # GraphRAG API wrapper
│   └── …                   # agentService, roomService, workspaceService, …
├── types/
│   ├── graph.ts             # GraphRAG: GraphNode, GraphEdge, GraphData, CommunityReport
│   └── …                   # agent.ts, chat.ts, artifact.ts, enums.ts
├── views/
│   ├── studio/
│   │   ├── WorkflowsView.vue   # Workflow list: create, open, delete global workflows
│   │   └── TriggersView.vue    # Trigger Policy manager: create/toggle/delete rules
│   ├── WorkflowEditorView.vue  # Dual-mode: Studio (/studio/workflows/:id) or Room legacy
│   ├── RoomSettingsView.vue    # Room config + agent assignment + attached_workflow_id picker
│   ├── RoomView.vue            # Room tabs: Chat | Board | Docs | Process | 🧠 Knowledge Graph
│   ├── AgentView.vue           # Agent design IDE + sandbox
│   └── …
├── components/
│   ├── workflow/
│   │   ├── WorkflowEditor.vue   # Vue Flow canvas (dual-mode: global / room-scoped)
│   │   ├── AgentNode.vue        # Custom node: agent icon, type badge, pulse when active
│   │   ├── LogicNode.vue        # Router / merge / action node
│   │   └── PropertiesPanel.vue  # Side panel: node label, linked agent, edge type config
│   ├── room/
│   │   ├── RoomChat.vue         # Chat panel with A2A trace toggle
│   │   ├── RoomGraphView.vue    # Canvas force-directed knowledge graph
│   │   └── GraphQueryPanel.vue  # Analytics Agent Q&A + community browser
│   ├── workspace/               # KanbanBoard, AgentSandbox
│   └── common/                  # ResizableSplitPane, ConfirmModal, Toast
├── layouts/
│   └── BaseLayout.vue           # Sidebar: Workspace | 🔀 Workflow Studio | ⚡ Triggers | Analytics
├── constants/                   # API endpoint paths
└── utils/                       # Pure helpers (cookies, sanitize)
```

---

## Getting Started

### Prerequisites
- Node.js ≥ 18 · npm ≥ 9
- Backend running at `localhost:8000` (see root README)

### Install & Run
```bash
npm install
npm run dev
```
→ App available at http://localhost:5173

Vite proxies all `/api` requests to the backend — no CORS setup needed in dev.

---

## Architecture Patterns

### 1. Workflow Studio (New)

Two new Studio views live at `/studio/workflows` and `/studio/triggers`.

`WorkflowEditor.vue` operates in **dual-mode**:
- **Studio mode** (`/studio/workflows/:workflowId`) — loads/saves via `/workflows/{id}`, fetches agents globally
- **Legacy Room mode** (`/rooms/:roomId/workflow`) — loads/saves via `/rooms/{id}/workflow`

The `workflowService.ts` provides:
```ts
workflowService.listWorkflows()          // GET /workflows
workflowService.createWorkflow(data)     // POST /workflows
workflowService.updateWorkflow(id, data) // PUT /workflows/{id}
workflowService.executeWorkflow(id, {})  // POST /workflows/{id}/execute

workflowService.listTriggers()           // GET /triggers
workflowService.createTrigger(data)      // POST /triggers
workflowService.updateTrigger(id, data)  // PUT /triggers/{id}
```

### 2. Trigger Policy UI

`TriggersView.vue` lets non-student users:
- View all active `TriggerPolicy` rules with event type labels and target workflow names
- Create new rules (event_type, conditions JSON, target workflow, optional scope session)
- Toggle active/inactive + delete

### 3. Composable-first Logic

Business logic lives in `src/composables/`, not in components or stores.
- **`useRoomChat`** — WebSocket + chat state + A2A trace parsing
- **`useDesignAgent`** — Agent config state + version control API calls

### 4. Pinia for Global Shared State

Only truly shared state lives in stores:
- **`useAuthStore`** — Current user + impersonation flag
- **`useWorkspaceStore`** — Artifacts with optimistic updates + WebSocket-driven sync

### 5. Route Guards

All routes under `/` require `requiresAuth`. Role-specific routes use `requiresAdmin` or `requiresNonStudent`.
Studio routes (`/studio/**`) are accessible to all non-student users.
On 403/404 API responses, views redirect to `/courses`.

### 6. Knowledge Graph Visualization (`RoomGraphView.vue`)

Custom canvas-based force-directed layout with center gravity, node repulsion, edge attraction, color-coded nodes by entity type, click-to-inspect sidebar, and entity type filter + text search.

---

## Code Quality

```bash
# Type check (must pass before PR)
npx vue-tsc --noEmit

# Lint + auto-fix
npm run lint

# Format
npm run format
```

> All `vue-tsc` errors must be zero. Avoid `any` — add types to `src/types/` instead.

---

## Key Rules for Contributors

1. **Types first** — Define data shapes in `src/types/` before writing components.
2. **Composable pattern** — Extract reusable logic into `src/composables/useXxx.ts`.
3. **Service layer** — All API calls go through `src/services/`; never call `api.get()` directly in a component.
4. **Dual-mode awareness** — When editing `WorkflowEditor.vue`, ensure both Studio and Room modes remain functional.
5. **No `idx` as v-for key** — Use unique IDs or stable composite keys.
6. **Redirect on errors** — Catch 403/404 in views and call `router.push()`.

---

## License

> ⚠️ **License not yet specified.** Please consult the project owner before use, redistribution, or contribution.
