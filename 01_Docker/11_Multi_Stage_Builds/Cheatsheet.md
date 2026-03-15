# Multi-Stage Builds — Cheatsheet

## Basic Multi-Stage Syntax

```dockerfile
# Stage 1: Builder
FROM node:20 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: Runtime (only this becomes the image)
FROM nginx:1.25-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
```

---

## COPY --from Variants

```dockerfile
# Copy from a named stage
COPY --from=builder /app/dist ./dist

# Copy from a stage by index (0 = first FROM)
COPY --from=0 /app/server .

# Copy from an external image
COPY --from=alpine:3.19 /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

# Copy from a specific image digest
COPY --from=golang:1.22@sha256:abc123 /usr/local/go/bin/go /usr/local/bin/
```

---

## Build Commands

```bash
# Build the final (default) stage
docker build -t my-app:v1.0.0 .

# Build up to a specific stage (e.g., for testing)
docker build --target builder -t my-app:builder .
docker build --target tester -t my-app:test .

# Build with BuildKit enabled (default in Docker 23+)
DOCKER_BUILDKIT=1 docker build -t my-app .

# Build and inspect intermediate stage
docker build --target builder -t debug-build .
docker run --rm -it debug-build sh
```

---

## Language-Specific Patterns

### Go (smallest image — scratch)

```dockerfile
FROM golang:1.22 AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o server .

FROM scratch
COPY --from=builder /app/server /server
ENTRYPOINT ["/server"]
```

### Go (with shell — alpine)

```dockerfile
FROM golang:1.22 AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o server .

FROM alpine:3.19
RUN apk --no-cache add ca-certificates
WORKDIR /app
COPY --from=builder /app/server .
CMD ["./server"]
```

### Node.js → nginx (static frontend)

```dockerfile
FROM node:20 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.25-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
```

### Python (slim final image)

```dockerfile
FROM python:3.12 AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /install /usr/local
COPY src/ ./src/
CMD ["python", "src/app.py"]
```

### Java Spring Boot (JRE only)

```dockerfile
FROM maven:3.9-eclipse-temurin-21 AS builder
WORKDIR /app
COPY pom.xml .
RUN mvn dependency:go-offline
COPY src ./src
RUN mvn package -DskipTests

FROM eclipse-temurin:21-jre-alpine
WORKDIR /app
COPY --from=builder /app/target/*.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
```

---

## Cache Optimization Order

```dockerfile
# GOOD: dependency manifest first, source code second
COPY go.mod go.sum ./        # only changes when deps change
RUN go mod download           # stays cached on source-only changes
COPY . .                      # invalidates subsequent layers on any file change
RUN go build -o server .

# BAD: source code first, kills all caching
COPY . .
RUN go mod download           # re-runs on every source change
RUN go build -o server .
```

---

## Size Comparison Quick Reference

| Language | Single Stage | Multi-Stage | Base |
|----------|-------------|-------------|------|
| Go | ~1.1 GB | 5–15 MB | scratch |
| Go | ~1.1 GB | ~10–20 MB | alpine |
| Node.js (static) | ~600 MB | ~25 MB | nginx:alpine |
| Python | ~1 GB | ~120 MB | python:slim |
| Java | ~700 MB | ~280 MB | jre-alpine |

---

## Parallel Stages (BuildKit)

```dockerfile
# These two stages run in parallel
FROM node:20 AS frontend
RUN npm ci && npm run build

FROM python:3.12 AS backend
RUN pip install -r requirements.txt

# This stage waits for both
FROM nginx:alpine
COPY --from=frontend /app/dist /html
COPY --from=backend /app /backend
```

---

## 📂 Navigation

| | Link |
|---|---|
| Previous | [10 · Docker Registry](../10_Docker_Registry/Cheatsheet.md) |
| Theory | [Multi-Stage Theory](./Theory.md) |
| Interview Q&A | [Multi-Stage Interview Q&A](./Interview_QA.md) |
| Code Examples | [Multi-Stage Code Examples](./Code_Example.md) |
| Next | [12 · Docker Security](../12_Docker_Security/Cheatsheet.md) |
