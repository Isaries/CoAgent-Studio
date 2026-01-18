# CoAgent Studio Frontend

## Project Overview
CoAgent Studio is a modern web application built with **Vue 3**, **TypeScript**, and **Vite**. It provides an intelligent agent workspace where users can configure, test, and manage AI agents for educational and system automation scenarios. The frontend implements a clean component architecture, strict type safety, and a professional UI design.

## Tech Stack
- **Framework**: Vue 3 (Composition API, `<script setup>`)
- **Language**: TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS (utility‑first) with custom design tokens
- **State Management**: Pinia stores (`auth`, `agent`, etc.)
- **Routing**: Vue Router 4
- **Linting & Formatting**: ESLint, Prettier, `vue-tsc`
- **Testing**: Vitest (unit) and Playwright (e2e) – not included in this repo but recommended.

## Prerequisites
- Node.js (>= 18)
- npm (>= 9) or Yarn
- Git

## Getting Started
```bash
# Clone the repository
git clone https://github.com/Isaries/CoAgent-Studio.git
cd CoAgent-Studio/frontend

# Install dependencies
npm install

# Run the development server
npm run dev
```
The application will be available at `http://localhost:5173`.

## Development Workflow
1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature
   ```
2. **Make changes** – all Vue components use `<script setup lang="ts">` and follow the strict type contracts defined in `src/types`.
3. **Run lint and type checks**
   ```bash
   npm run lint:check   # ESLint with zero warnings
   npx vue-tsc --noEmit # TypeScript compilation check
   ```
4. **Commit and push**
   ```bash
   git add .
   git commit -m "feat: description"
   git push origin feature/your-feature
   ```
5. **Open a Pull Request** – CI will run the lint and type checks automatically.

## Build for Production
```bash
npm run build
# The production bundle is generated in the `dist/` directory.
```
Deploy the contents of `dist/` to any static web host (e.g., Vercel, Netlify, GitHub Pages).

## Testing
- **Unit Tests**: `npm run test:unit`
- **End‑to‑End Tests**: `npm run test:e2e`
(These scripts are placeholders; configure Vitest or Playwright as needed.)

## Linting & Formatting
- **ESLint**: `npm run lint` – fixes automatically where possible.
- **Prettier**: Integrated via ESLint; run `npm run format` to format the whole codebase.
- **Type Checking**: `npx vue-tsc --noEmit` – ensures strict type safety across all Vue components.

## Code Structure Overview
```
src/
├─ api.ts                     # Centralized API client with interceptors
├─ assets/                    # Static assets (images, icons)
├─ components/                # Reusable UI components (icons, common widgets)
│   └─ common/                # Shared components like ResizableSplitPane
├─ composables/               # Vue composables (useAuth, useAgentSandbox, etc.)
├─ constants/                 # API endpoint and provider constants
├─ layouts/                   # Layout components (BaseLayout.vue)
├─ services/                  # Service layer for API calls (agentService, authService)
├─ stores/                    # Pinia stores (auth, agent)
├─ types/                     # TypeScript interfaces and enums
├─ utils/                     # Utility functions (cookies, etc.)
├─ views/                     # Page‑level components (DashboardView, CourseSettingsView, SystemAgentIDE, UserListView)
│   └─ course-settings/       # Sub‑views and components for course settings
│   └─ system/                # System agent IDE and related components
└─ main.ts                    # Application entry point
```
Key components:
- **CourseBrainEditor.vue** – Core editor for configuring an agent’s system prompt, model, triggers, and schedule.
- **DesignAgentConfig.vue** – UI for sandbox configuration and custom API keys.
- **SystemAgentIDE.vue** – Full‑screen IDE‑like environment for prompt engineering.
- **ResizableSplitPane.vue** – Flexible split‑pane component used throughout the UI.

## Contributing
1. Fork the repository.
2. Create a feature branch.
3. Follow the development workflow above.
4. Ensure all lint and type checks pass before submitting a PR.
5. Write clear commit messages and update documentation when adding new features.

## License
This project is licensed under the MIT License.
