# CoAgent Studio Frontend

## Project Overview
CoAgent Studio is a professional-grade intelligent agent workspace built with **Vue 3**, **TypeScript**, and **Vite**. It is designed to provide a robust "IDE-like" environment for configuring, testing, and managing AI agents (Teacher, Student, Design, Analytics).

The codebase follows a **"Perfect State"** philosophy: strict type safety, zero lint warnings, and a decoupled architecture to ensure maintainability and scalability.

## Tech Stack
- **Framework**: Vue 3 (Composition API, separate `<script setup>`)
- **Language**: TypeScript (Strict Mode)
- **Build Tool**: Vite
- **Styling**: Tailwind CSS + DaisyUI (with custom design tokens)
- **State Management**: Pinia (Stores) + Composables (Logic)
- **Routing**: Vue Router 4 (with Navigation Guards)
- **Quality Assurance**: ESLint, Prettier, `vue-tsc` (Type Check)

## Architecture & Design Patterns

### 1. Orchestrator Pattern
Complex views like `CourseSettingsView` act as **Orchestrators**. They manage high-level state (loading, error handling, saving) and delegate rendering to specialized "dumb" components:
- **`CourseBrainHeader`**: Manages navigation tabs and primary actions.
- **`CourseBrainEditor`**: Handles specific form inputs for prompts, models, and triggers.
- **`VersionSidebar`**: Manages history and restoration independently.

### 2. Composition over Inheritance
Logic is extracted into reusable **Composables** (`src/composables/`) rather than mixing it into components or large stores:
- **`useAuth`**: Centralizes login, logout, user roles, and impersonation logic.
- **`useAgentSandbox`**: Manages the chat simulation state and history.
- **`useVersionControl`**: Abstracts the complexity of fetching and restoring agent configuration versions.

### 3. Strict Type Safety
We avoid `any`. All data structures are strictly typed in `src/types/`:
- **`enums.ts`**: Centralized enums for `UserRole`, `AgentType`, `TriggerType`, `ModelProvider`.
- **`agent.ts`**: Comprehensive interfaces for Agent configurations.

## Key Features

### 🤖 System Agent IDE
A dedicated "Meta-Prompt Engineering Workbench" (`SystemAgentIDE.vue`) that allows admins to:
- Design the "Brain" of the system agents.
- **Simulate** conversations in real-time with a built-in sandbox.
- **Version Control**: Rollback to previous system prompts instantly.

### 👥 Role-Based Access Control (RBAC)
Deeply integrated permission system:
- **Super Admin**: Full system access (Database, System Agents).
- **Teacher**: Course creation and management.
- **Student**: Access to assigned courses and chat interface.
- **Impersonation**: Admins can "view as" other users for debugging.

### 🔄 Multi-Agent Orchestration
Support for diverse agent types with specific configurations:
- **Teacher/Student Agents**: Standard conversational agents.
- **Design Agents**: Specialized in creating content.
- **Analytics Agents**: Background processors for data insight.

## Getting Started

### Prerequisites
- Node.js (>= 18)
- npm (>= 9)

### Installation
```bash
git clone https://github.com/Isaries/CoAgent-Studio.git
cd CoAgent-Studio/frontend
npm install
```

### Development
```bash
npm run dev
```
Access the app at `http://localhost:5173`.

### Quality Checks
Before committing, ensure your code meets the quality standards:
```bash
# 1. Linting (Auto-fix)
npm run lint

# 2. Type Checking (Strict)
npx vue-tsc --noEmit
```

## Code Structure
```
src/
├─ api/                       # API definitions
├─ components/
│   ├─ common/                # Shared widgets (ResizableSplitPane, Toast)
│   └─ icons/                 # Atomic SVG components
├─ composables/               # Shared logic (useAuth, useVersionControl)
├─ constants/                 # App-wide constants
├─ layouts/                   # Layout wrappers (BaseLayout)
├─ stores/                    # Pinia State (Global user state)
├─ types/                     # TypeScript definitions (The Source of Truth)
├─ views/                     # Route Views
│   ├─ course-settings/       # Course Agent Logic
│   └─ system/                # System Agent IDE
└─ utils/                     # Pure utility functions
```

## Contributing
1. **Consistency**: Use the `useComposable` pattern for new logic.
2. **Types**: Add new types to `src/types/` before writing components.
3. **Icons**: Use `src/components/icons/` for SVGs.
4. **Commits**: Follow conventional commits (e.g., `feat:`, `fix:`, `refactor:`).

## Troubleshooting
- **`vue-tsc` errors?**: Check `src/types/enums.ts`. We do not allow implicit `any`.
- **401 Loop?**: The `api.ts` interceptor handles token expiration. Ensure backend cookies are set correctly.

## License
MIT
