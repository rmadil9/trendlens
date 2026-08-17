# syntax=docker/dockerfile:1
#
# The web tier: nginx, with the React build compiled in.
#
# There is deliberately no separate frontend container. The SPA does no
# per-request work — `npm run build` emits immutable files — so it's a build
# artifact, not a service. Giving it its own container would add a process to
# supervise, a health check, and a network hop, in exchange for nothing.
#
# Build context is the REPO ROOT, not frontend/, because this image needs both
# the frontend source and the nginx config.
#   docker build -f nginx/Dockerfile .

# ──────────────────────────────────────────────────────────────────────────────
# Stage 1 — compile the SPA
# ──────────────────────────────────────────────────────────────────────────────
FROM node:24-alpine AS build

WORKDIR /app

# Manifests first: npm ci is the slow step and shouldn't rerun when only
# component source changes.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./

# No VITE_API_URL. Same-origin deployment means the client calls the relative
# path /api — nginx routes it to the backend on the same host and port, so
# there is no base URL to configure and no per-environment image.
RUN npm run build


# ──────────────────────────────────────────────────────────────────────────────
# Stage 2 — nginx
# ──────────────────────────────────────────────────────────────────────────────
FROM nginx:1.27-alpine

# openssl is needed only by the placeholder-certificate entrypoint below.
RUN apk add --no-cache openssl

# The stock config defines its own `listen 80; server_name localhost;` server.
# Left in place it loads alongside ours and, being first alphabetically in
# conf.d/, becomes the default server for :80 — so any request whose Host
# doesn't match ${DOMAIN} gets the nginx welcome page instead of the app.
RUN rm /etc/nginx/conf.d/default.conf

# Static assets. Node, npm, and node_modules stay behind in stage 1 — the
# runtime image carries only the compiled output.
COPY --from=build /app/dist /usr/share/nginx/html

# The official image runs envsubst over /etc/nginx/templates/*.template at
# startup and writes the result into /etc/nginx/conf.d/ — that's how ${DOMAIN}
# reaches the config without baking the hostname into the image.
COPY nginx/templates/ /etc/nginx/templates/

# Scripts in /docker-entrypoint.d/ run before nginx starts, in filename order.
COPY nginx/docker-entrypoint.d/ /docker-entrypoint.d/
RUN chmod +x /docker-entrypoint.d/*.sh

EXPOSE 80 443
