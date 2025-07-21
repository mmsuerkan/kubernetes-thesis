# Go Pod Watcher Dockerfile
FROM golang:1.24-alpine AS builder

# Install build dependencies
RUN apk add --no-cache git ca-certificates curl

# Set working directory
WORKDIR /app

# Copy go mod files
COPY go.mod go.sum ./

# Download dependencies
RUN go mod download

# Copy source code
COPY . .

# Build the application
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o main main.go

# Final stage
FROM alpine:latest

# Install runtime dependencies and kubectl
RUN apk add --no-cache ca-certificates curl tzdata \
    && update-ca-certificates \
    && curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl \
    && rm kubectl

# Create non-root user
RUN adduser -D -s /bin/sh appuser

# Set working directory
WORKDIR /home/appuser

# Copy binary from builder
COPY --from=builder /app/main .

# Create .kube directory for kubernetes config
RUN mkdir -p .kube && chown -R appuser:appuser .kube

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Command to run the application
CMD ["./main"]