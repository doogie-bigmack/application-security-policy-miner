# Multi-stage build for frontend
FROM oven/bun:1.1-alpine AS base

WORKDIR /app

# Development stage
FROM base AS development
COPY package.json bun.lockb* ./
RUN bun install
COPY . .
CMD ["bun", "run", "dev", "--host"]

# Build stage
FROM base AS build
COPY package.json bun.lockb* ./
RUN bun install
COPY . .
RUN bun run build

# Production stage with nginx
FROM nginx:alpine AS production
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
