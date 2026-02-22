# CoAgent Studio — Frontend

Vue 3 SPA providing a collaborative, real-time workspace for interacting with and designing AI agents.

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
├── services/            # API wrappers (one file per resource)
├── components/
│   ├── chat/            # MessageBubble, ChatInput
│   ├── room/            # RoomChat, RoomDocs, RoomProcess
│   ├── workspace/       # KanbanBoard, KanbanColumn, AgentSandbox
│   └── common/          # ResizableSplitPane, ConfirmModal, Toast
├── views/               # Page-level components (one per route)
│   ├── RoomView.vue         # Main collaborative room (chat + board + docs + process)
│   ├── AgentView.vue        # Agent design IDE + sandbox
│   ├── CourseDetailView.vue # Course homepage
│   └── ...
├── types/               # TypeScript interfaces (agent.ts, chat.ts, artifact.ts, enums.ts)
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

## License
MIT
