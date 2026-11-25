# Jaga web app (Next.js). Built and started by `docker compose up`.
# Three stages so the final image only holds what's needed to run.

# 1) Install dependencies (cached until package.json / pnpm-lock.yaml change)
FROM node:24-alpine AS deps
WORKDIR /app
RUN npm install -g pnpm@12.21.0
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# 2) Build the app
FROM node:24-alpine AS build
WORKDIR /app
RUN npm install -g pnpm@12.21.0
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1 NEXT_OUTPUT=standalone
RUN pnpm build

# 3) Run: just the standalone server + static files (small image)
FROM node:24-alpine AS run
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3010
RUN addgroup -S jaga && adduser -S jaga -G jaga
COPY --from=build --chown=jaga:jaga /app/.next/standalone ./
COPY --from=build --chown=jaga:jaga /app/.next/static ./.next/static
COPY --from=build --chown=jaga:jaga /app/public ./public
USER jaga
EXPOSE 3010
CMD ["node", "server.js"]
