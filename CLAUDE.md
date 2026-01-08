# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
Application Security Policy Miner - A tool for analyzing and mining security policies.

## Repository
https://github.com/doogie-bigmack/application-security-policy-miner

## AI Agent
- **Model**: Claude Opus 4.5
- **Claude Agent SDK**: Latest version
- **Mode**: Autonomous with `--dangerously-skip-permissions`

## Tech Stack

### Frontend
- Bun 1.1.x (runtime & package manager)
- React 18.x
- TailwindCSS 3.4.x
- TypeScript 5.x

### Backend
- Python 3.12.x
- FastAPI 0.115.x
- SQLAlchemy 2.0.x
- PostgreSQL 16.x
- Pydantic 2.x

### Linting & Formatting
- Frontend: ESLint 9.x, Prettier 3.x
- Backend: Ruff 0.8.x

### Deployment
- Docker 27.x with Docker Compose 2.x

## Rules

### Package Management
- **ONLY use Bun** - never use npm or yarn
- Use `bun install`, `bun run`, `bun add`, `bun remove`

### Logging
- **Never use print statements or console.log**
- Frontend: Use **pino** for all logging
- Backend: Use Python's `logging` module with **structlog**
- Include log levels: DEBUG, INFO, WARNING, ERROR
- Include timestamps and context in all logs

### Docker
- Use Alpine-based images for minimal size
- Use multi-stage builds
- Frontend served via nginx in production
- Target image sizes: Frontend < 25MB, Backend < 150MB

### Code Quality
- All code must pass linting before commit
- Type hints required for all Python functions
- TypeScript strict mode enabled
- No `any` types in TypeScript

### Git Workflow
- Feature branches for each task
- Squash merge PRs to main
- Conventional commit messages (feat:, fix:, chore:, etc.)

## Development Workflow

1. Pick a task from `prd.json` with `passes: false`
2. Create a feature branch
3. Implement the feature
4. Validate: linting, tests, Docker builds, browser verification
5. Update `prd.json` and `progress.txt`
6. Commit, push, create PR, merge to main

## UI/UX Design

### Philosophy
Clean, minimal, professional. Security tools have notoriously bad UIs - we're breaking that pattern. Think Linear, Vercel, or Stripe - not enterprise security software from 2010.

### Color Mode
- Support both light and dark mode
- Respect system preference by default
- Allow manual toggle
- Use Tailwind's `dark:` variant

### Color Palette

#### Light Mode
- Background: white (#ffffff)
- Surface: gray-50 (#f9fafb)
- Border: gray-200 (#e5e7eb)
- Text primary: gray-900 (#111827)
- Text secondary: gray-600 (#4b5563)

#### Dark Mode
- Background: gray-950 (#030712)
- Surface: gray-900 (#111827)
- Border: gray-800 (#1f2937)
- Text primary: gray-50 (#f9fafb)
- Text secondary: gray-400 (#9ca3af)

#### Accent Colors
- Primary: blue-600 (#2563eb) / dark: blue-500 (#3b82f6)
- Success: green-600 (#16a34a)
- Warning: amber-500 (#f59e0b)
- Error: red-600 (#dc2626)

### Typography
- Font: System font stack
- Headings: Semi-bold, tight tracking
- Body: Regular weight, relaxed line height
- Mono: For code, logs, technical data

### Components
- Rounded corners: rounded-lg (8px)
- Shadows: Subtle, use sparingly
- Buttons: Solid primary, outline secondary
- Cards: Subtle border, no heavy shadows
- Tables: Clean lines, alternating rows in dark mode only

### Spacing
- Consistent use of Tailwind spacing scale
- Generous whitespace - don't cram elements
- Card padding: p-6
- Section gaps: space-y-8

### Icons
- Use Lucide React
- Consistent size: 16px (sm), 20px (md), 24px (lg)
- Match text color

### Design Principles
1. **Clarity over decoration** - no gradients, no glows, no unnecessary visual noise
2. **Readable data** - security data must be scannable and clear
3. **Consistent** - same patterns everywhere
4. **Accessible** - proper contrast ratios, focus states
5. **Fast** - no heavy animations, instant feedback
