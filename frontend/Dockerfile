# ── builder ──────────────────────────────────────────────────────────────────
FROM node:22-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts

COPY . .
RUN npm run build

# ── runner ────────────────────────────────────────────────────────────────────
# Unprivileged variant: nginx runs as uid 101 and listens on 8080
FROM nginxinc/nginx-unprivileged:1.27-alpine AS runner

COPY --from=builder /app/dist  /usr/share/nginx/html

# The stock entrypoint envsubsts /etc/nginx/templates/*.template into
# /etc/nginx/conf.d/, substituting only variables that exist in the
# environment — nginx runtime vars like $host pass through untouched.
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

EXPOSE 8080
