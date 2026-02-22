# CoAgent Studio — Frontend

Vue 3 SPA providing a collaborative, real-time workspace for interacting with and designing AI agents, including an interactive **Knowledge Graph** view powered by the GraphRAG Analytics Agent.

## Tech Stack

| Concern | Technology |
|---|---|
| Framework | Vue 3 (Composition API + `<script setup>`) + TypeScript |
| Build | Vite 7 |
| Styling | Tailwind CSS + DaisyUI |
| State | Pinia (global) + Composables (local logic) |
| Routing | Vue Router 4 (with auth + role guards) |
| Rich Text | Tiptap |
| Process Diagrams | Vue Flow |
| Knowledge Graph | Native Canvas (force-directed, no external graph lib) |
| HTTP Client | Axios (with auto-retry on 401) |
| Real-time | Native WebSockets (`useWebSocket` composable) |
| Type Check | vue-tsc (strict mode) |
| Lint/Format | ESLint + Prettier |

---

## Project Structure

```
src/
├── api.ts               # Axios instance + global interceptors (401 refresh, 403/500 toast)
├── router/
│   └── index.ts         # All routes with requiresAuth / requiresAdmin / requiresNonStudent guards
├── stores/
│   ├── auth.ts          # User session, impersonation state
│   ├── workspace.ts     # Artifacts (kanban tasks, docs, processes) with optimistic updates
│   └── toast.ts         # Global notification store
├── composables/
│   ├── useWebSocket.ts  # WS lifecycle with exponential-backoff reconnect + auto-cleanup
│   ├── useRoomChat.ts   # Chat messages, WS connection, A2A trace handling
│   ├── useAuth.ts       # Login, logout, impersonation actions
│   ├── useDesignAgent.ts    # Agent version control + design state
│   └── usePermissions.ts    # Per-component RBAC helper functions
├── services/
│   ├── graphService.ts  # GraphRAG API wrapper (build, query, graph data, communities, status)
│   └── …               # One file per resource (agents, courses, rooms, …)
├── types/
│   ├── graph.ts         # GraphRAG types: GraphNode, GraphEdge, GraphData, CommunityReport, NODE_COLORS
│   └── …               # agent.ts, chat.ts, artifact.ts, enums.ts
├── components/
│   ├── chat/            # MessageBubble, ChatInput
│   ├── room/
│   │   ├── RoomChat.vue         # Chat panel with A2A trace toggle
│   │   ├── RoomDocs.vue         # Document viewer
│   │   ├── RoomProcess.vue      # Process diagram viewer
│   │   ├── RoomGraphView.vue    # Canvas force-directed knowledge graph visualization
│   │   └── GraphQueryPanel.vue  # Analytics Agent Q&A + graph build trigger + community browser
│   ├── workspace/       # KanbanBoard, KanbanColumn, AgentSandbox
│   └── common/          # ResizableSplitPane, ConfirmModal, Toast
├── views/
│   ├── RoomView.vue         # Room tabs: Chat | Board | Docs | Process | 🧠 Knowledge Graph
│   ├── AgentView.vue        # Agent design IDE + sandbox
│   ├── CourseDetailView.vue # Course homepage
│   └── …
├── constants/           # API endpoint paths, HTTP status codes
└── utils/               # Pure helpers (cookies, sanitize)
```

---

## Getting Started

### Prerequisites
- Node.js ≥ 18
- npm ≥ 9
- Backend running at `localhost:8000` (see root README)

### Install & Run
```bash
npm install
npm run dev
```
→ App available at http://localhost:5173

Vite proxies all `/api` requests to the backend (`http://localhost:8000`) — no CORS setup needed in dev.

---

## Architecture Patterns

### 1. Composable-first Logic
Business logic lives in `src/composables/`, not in components or Pinia stores.

- **`useWebSocket`** — Handles connection lifecycle, reconnect, cleanup on `onUnmounted`.
- **`useRoomChat`** — Wraps `useWebSocket` + chat state, A2A trace parsing, and workspace artifact dispatch.
- **`useDesignAgent`** — Agent config state + version control API calls.

### 2. Pinia for Global Shared State
Only truly shared state lives in stores:
- **`useAuthStore`** — Current user + impersonation flag.
- **`useWorkspaceStore`** — Artifacts with optimistic updates + WebSocket-driven real-time sync.

### 3. Route Guards
All routes under `/` require `requiresAuth`. Role-specific routes use `requiresAdmin` or `requiresNonStudent`. On 403/404 API responses, views redirect to `/courses` rather than showing broken UI.

### 4. Knowledge Graph Visualization (`RoomGraphView.vue`)
The graph view uses a **custom canvas-based force-directed layout** with:
- Center gravity + node repulsion + edge attraction forces
- Color-coded nodes by entity type (via `NODE_COLORS` in `types/graph.ts`)
- Click-to-inspect sidebar showing entity details, community membership, and all related edges
- Entity type filter dropdown and text search (client-side filtering with opacity dimming)
- Separate detail panel for selected node's relationships

### 5. GraphRAG Query Panel (`GraphQueryPanel.vue`)
- **Build Graph**: Triggers `POST /graph/{room_id}/build` → ARQ background job
- **Natural Language Q&A**: Posts to `POST /graph/{room_id}/query`; displays intent badge (Global / Local) and cited sources
- **Community Browser**: Fetches `GET /graph/{room_id}/communities`; collapsible accordion per cluster

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
3. **No `idx` as v-for key** — Use unique IDs or stable composite keys.
4. **Redirect on errors** — Catch 403/404 in views and call `router.push()`.
5. **Graph API always checks room access** — Never skip the `_verify_room_access` dependency on graph endpoints.

---

## License

> ⚠️ **License not yet specified.** Please consult the project owner before use, redistribution, or contribution.
