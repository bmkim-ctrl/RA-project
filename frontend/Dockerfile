FROM node:20-alpine AS deps
WORKDIR /workspace/RA/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

FROM node:20-alpine AS builder
WORKDIR /workspace/RA/frontend
COPY --from=deps /workspace/RA/frontend/node_modules ./node_modules
COPY frontend/ ./
ENV NEXT_PUBLIC_API_URL=http://localhost:8000
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /workspace/RA/frontend
ENV NODE_ENV=production
ENV PORT=3000
ENV NEXT_PUBLIC_API_URL=http://localhost:8000
COPY --from=builder /workspace/RA/frontend ./
EXPOSE 3000
CMD ["npm", "run", "start"]
