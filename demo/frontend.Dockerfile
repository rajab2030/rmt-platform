# RMT control center -- TEST / EVALUATION IMAGE ONLY.
#
# Not a deployment path. Production serves an immutable static release through
# Caddy (projects/homelab-control-center/deploy/Caddyfile). See demo/README.md.
#
# Build context: repository root (see docker-compose.yml).
FROM node:22-alpine AS build
WORKDIR /src
COPY projects/homelab-control-center/frontend/package.json \
     projects/homelab-control-center/frontend/package-lock.json ./
RUN npm ci
COPY projects/homelab-control-center/frontend/ ./
RUN npm run build

FROM nginx:1.27-alpine
COPY demo/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /src/dist /usr/share/nginx/html
EXPOSE 80
