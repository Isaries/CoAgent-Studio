# CoAgent Studio — Frontend

Vue 3 SPA providing a visual AI agent orchestration interface: a drag-and-drop Workflow Studio, a Trigger Policy manager, Space management, a Knowledge Engine, real-time collaborative rooms, and an interactive Knowledge Graph powered by GraphRAG.

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
|-- api.ts                   # Axios instance + global interceptors (401 refresh, 403/500 toast)
|-- router/
|   +-- index.ts             # Routes: /spaces, /platform/workflows, /platform/triggers, /platform/knowledge, ...
|-- stores/
|   |-- auth.ts              # User session, impersonation state
|   |-- workspace.ts         # Artifacts (kanban, docs, processes) with optimistic updates
|   +-- toast.ts             # Global notification store
|-- composables/
|   |-- useWebSocket.ts      # WS lifecycle with exponential-backoff reconnect + auto-cleanup
|   |-- useRoomChat.ts       # Chat messages, WS connection, A2A trace handling
|   |-- useAuth.ts           # Login, logout, impersonation actions
|   |-- useSpace.ts          # Space CRUD + member management state
|   |-- useKnowledgeBase.ts  # KnowledgeBase state + build polling
|   |-- useDesignAgent.ts    # Agent version control + design state
|   +-- usePermissions.ts    # Per-component RBAC helper functions
|-- services/
|   |-- spaceService.ts      # /spaces CRUD + members API
|   |-- knowledgeService.ts  # /knowledge CRUD + build/query/documents API
|   |-- workflowService.ts   # Global /workflows CRUD + /triggers CRUD + legacy room API
|   |-- graphService.ts      # GraphRAG API wrapper
|   +-- ...                  # agentService, roomService, workspaceService, announcementService, ...
|-- types/
|   |-- space.ts             # Space, UserSpaceLink, SpacePreset
|   |-- knowledge.ts         # KnowledgeBase, BuildStatus, KBQueryResult
|   |-- graph.ts             # GraphRAG: GraphNode, GraphEdge, GraphData, CommunityReport
|   +-- ...                  # agent.ts, chat.ts, artifact.ts, analytics.ts, enums.ts
|-- views/
|   |-- HomeView.vue             # Dual-mode: landing (unauthenticated) / dashboard (authenticated)
|   |-- SpaceListView.vue        # My Spaces grid + preset-based creation modal
|   |-- SpaceHubView.vue         # Space hub: Overview, Rooms, Members, Announcements, Knowledge, Analytics tabs
|   |-- SpaceSettingsView.vue    # Space title/description/preset configuration
|   |-- KnowledgeView.vue        # Knowledge Engine: list + detail + build polling + query console
|   |-- platform/
|   |   |-- WorkflowsView.vue    # Workflow list: create, open, delete global workflows
|   |   +-- TriggersView.vue     # Trigger Policy manager: create/toggle/delete rules
|   |-- WorkflowEditorView.vue   # Dual-mode: Platform (/platform/workflows/:id) or Room legacy
|   |-- RoomSettingsView.vue     # Room config + agent assignment + workflow picker + tab toggles
|   |-- RoomView.vue             # Room with dynamic tabs: Chat | Board | Docs | Process | Knowledge Graph
|   |-- AgentView.vue            # Agent design IDE + sandbox
|   +-- ...
|-- components/
|   |-- space/
|   |   |-- SpaceRoomList.vue          # Room list inside SpaceHubView
|   |   |-- SpaceMemberList.vue        # Member list with role badges
|   |   |-- SpaceAnnouncementList.vue  # Announcement feed
|   |   +-- modals/
|   |       |-- CreateRoomModal.vue    # New room form (sends space_id)
|   |       |-- InviteMemberModal.vue  # Invite by email or user ID
|   |       +-- AssignMemberModal.vue  # Assign/change member role
|   |-- knowledge/
|   |   |-- KnowledgeBaseCard.vue  # KB card with build status indicator
|   |   +-- CreateKBModal.vue      # New KB form (name, source_type, space_id)
|   |-- workflow/
|   |   |-- WorkflowEditor.vue   # Vue Flow canvas (dual-mode: platform / room-scoped)
|   |   |-- AgentNode.vue        # Custom node: agent icon, type badge, pulse when active
|   |   |-- LogicNode.vue        # Router / merge / action node
|   |   +-- PropertiesPanel.vue  # Side panel: node label, linked agent, edge type config
|   |-- room/
|   |   |-- RoomChat.vue         # Chat panel with A2A trace toggle
|   |   |-- RoomGraphView.vue    # Canvas force-directed knowledge graph
|   |   +-- GraphQueryPanel.vue  # Analytics Agent Q&A + community browser
|   |-- workspace/               # KanbanBoard, AgentSandbox
|   +-- common/                  # ResizableSplitPane, ConfirmModal, Toast
|-- layouts/
|   +-- BaseLayout.vue           # Sidebar with four sections: PLATFORM | SPACES | SYSTEM | ADMIN
|-- constants/                   # API endpoint paths
+-- utils/                       # Pure helpers (cookies, sanitize)
```

---

## Getting Started

### Prerequisites
- Node.js >= 18 · npm >= 9
- Backend running at `localhost:8000` (see root README)

### Install and Run
```bash
npm install
npm run dev
```
App available at http://localhost:5173

Vite proxies all `/api` requests to the backend — no CORS setup needed in dev.

---

## Architecture Patterns

### 1. Navigation Structure

The sidebar (`BaseLayout.vue`) is organized into four sections:

| Section | Routes | Audience |
|---|---|---|
| PLATFORM | Agent Lab, My Agents, Workflows, Triggers, Knowledge Engine | All authenticated users |
| SPACES | My Spaces | All authenticated users |
| SYSTEM | My API Keys, Analytics | All authenticated users |
| ADMIN | Dashboard, Users, System Agents, Database | Admin/Super Admin only |

### 2. Workflow Studio

Two platform views live at `/platform/workflows` and `/platform/triggers`.

`WorkflowEditor.vue` operates in **dual-mode**:
- **Platform mode** (`/platform/workflows/:workflowId`) — loads/saves via `/workflows/{id}`, fetches agents globally
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

### 3. Space Management

`SpaceHubView.vue` provides a six-tab interface for each space:
- **Overview** — real-time room activity cards (polls `/spaces/{id}/overview`)
- **Rooms** — room list with `CreateRoomModal`
- **Members** — member list with role management
- **Announcements** — announcement feed
- **Knowledge** — Knowledge Bases linked to this space
- **Analytics** — space-level analytics reports

### 4. Knowledge Engine

`KnowledgeView.vue` operates in list/detail mode:
- List: KnowledgeBaseCard grid with create button
- Detail: document upload, build trigger, build status polling (max 20 attempts, 3s interval), query console

The `knowledgeService.ts` provides:
```ts
knowledgeService.listKBs(spaceId)          // GET /knowledge?space_id=...
knowledgeService.createKB(data)            // POST /knowledge/
knowledgeService.buildKB(id)              // POST /knowledge/{id}/build
knowledgeService.getStatus(id)            // GET /knowledge/{id}/status
knowledgeService.queryKB(id, query)       // POST /knowledge/{id}/query
knowledgeService.uploadDocument(id, file)  // POST /knowledge/{id}/documents
knowledgeService.mergeKBs(targetId, sourceId)  // POST /knowledge/{id}/merge
```

### 5. Room Dynamic Tabs

Room tabs are driven by `room.enabled_tabs` (a JSONB array on the `Room` model). The default set is `["chat", "board", "docs", "process", "knowledge"]`. Users with edit permissions can toggle individual tabs in **Room Settings** — the updated `enabled_tabs` array is sent via `PUT /rooms/{id}`.

`RoomView.vue` computes visible tabs at runtime:
```ts
const visibleTabs = computed(() =>
  ALL_TABS.filter(t => room.value?.enabled_tabs?.includes(t.id) ?? true)
)
```

### 6. Trigger Policy UI

`TriggersView.vue` lets non-student users:
- View all active `TriggerPolicy` rules with event type labels and target workflow names
- Create new rules (event_type, conditions JSON, target workflow, optional scope session)
- Toggle active/inactive + delete

### 7. Composable-first Logic

Business logic lives in `src/composables/`, not in components or stores.
- **`useRoomChat`** — WebSocket + chat state + A2A trace parsing
- **`useDesignAgent`** — Agent config state + version control API calls
- **`useSpace`** — Space CRUD + member management
- **`useKnowledgeBase`** — KnowledgeBase state + build status polling

### 8. Pinia for Global Shared State

Only truly shared state lives in stores:
- **`useAuthStore`** — Current user + impersonation flag
- **`useWorkspaceStore`** — Artifacts with optimistic updates + WebSocket-driven sync

### 9. Route Guards

All routes under `/` require `requiresAuth`. Role-specific routes use `requiresAdmin` or `requiresNonStudent`.
Platform routes (`/platform/**`) are accessible to all non-student users.
On 403/404 API responses, views redirect to `/spaces`.

Backward-compatibility redirects are registered for old `/courses/**` paths, pointing to their `/spaces/**` equivalents.

### 10. Knowledge Graph Visualization (`RoomGraphView.vue`)

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
4. **Dual-mode awareness** — When editing `WorkflowEditor.vue`, ensure both Platform and Room modes remain functional.
5. **No `idx` as v-for key** — Use unique IDs or stable composite keys.
6. **Redirect on errors** — Catch 403/404 in views and call `router.push('/spaces')`.

---

## License

> License not yet specified. Please consult the project owner before use, redistribution, or contribution.
