FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# Install Typst from official GitHub release
ARG TYPST_VERSION=0.12.0
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates xz-utils && \
    ARCH="$(dpkg --print-architecture)" && \
    case "$ARCH" in \
        amd64) TYPST_ARCH="x86_64-unknown-linux-musl" ;; \
        arm64) TYPST_ARCH="aarch64-unknown-linux-musl" ;; \
        *) echo "Unsupported architecture: $ARCH" && exit 1 ;; \
    esac && \
    curl -fsSL "https://github.com/typst/typst/releases/download/v${TYPST_VERSION}/typst-${TYPST_ARCH}.tar.xz" \
        | tar -xJ -C /tmp && \
    mv "/tmp/typst-${TYPST_ARCH}/typst" /usr/local/bin/typst && \
    rm -rf "/tmp/typst-${TYPST_ARCH}" && \
    apt-get purge -y curl xz-utils && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

FROM base AS builder
COPY pyproject.toml .
RUN pip install --no-cache-dir .

FROM base AS runtime
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . .
ENTRYPOINT ["lemonade"]
CMD ["run"]
