FROM node:24.21.0-bookworm-slim@sha256:2fe369e969550cde8e867afc3fe370b260140cab4a23d467074295b42163d553 AS builder

WORKDIR /workspace

COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/package.json
RUN npm ci --workspace @sochron1k/web --include-workspace-root=false

COPY apps/web apps/web
RUN npm run build --workspace @sochron1k/web

FROM nginx:1.30.5-alpine3.24@sha256:25820c39dba41369486df729ad6697de2fab631ca809e0503e1d1e0c73d9a232

COPY apps/web/nginx.conf /etc/nginx/nginx.conf
COPY --from=builder /workspace/apps/web/dist /usr/share/nginx/html

USER 101:101
EXPOSE 8080

ENTRYPOINT ["nginx"]
CMD ["-g", "daemon off;"]
