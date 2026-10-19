# Private frontend (Next.js production build). API_URL is baked into the /api rewrite at build time
# and used at runtime for server-side requests.
FROM node:22-bookworm-slim AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY frontend-private/package.json frontend-private/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend-private/ ./
ARG API_URL=http://api:8000
ENV API_URL=$API_URL
# no "npm prune --omit=dev": next start needs TypeScript to load next.config.ts
RUN npm run build

FROM node:22-bookworm-slim
WORKDIR /app
ARG API_URL=http://api:8000
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 API_URL=$API_URL
COPY --from=build /app ./
USER node
EXPOSE 3000
CMD ["node", "node_modules/next/dist/bin/next", "start", "-H", "0.0.0.0", "-p", "3000"]
