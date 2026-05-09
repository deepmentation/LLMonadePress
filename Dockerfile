FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# Install Typst (from GitHub release) plus a portable set of fonts so the
# default profile typography renders out of the box. DejaVu covers Latin /
# Cyrillic / Greek; Noto adds wider Unicode fallback (CJK fragments, symbols).
ARG TYPST_VERSION=0.12.0
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates xz-utils \
        fonts-dejavu-core fonts-dejavu-extra fonts-noto-core \
        ffmpeg && \
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

# Copy project sources before install so hatchling can find the package
COPY pyproject.toml README.md ./
COPY llmonadepress/ ./llmonadepress/
COPY device_profiles/ ./device_profiles/
COPY templates/ ./templates/
COPY alembic/ ./alembic/
COPY alembic.ini ./

RUN pip install --no-cache-dir .

ENTRYPOINT ["lemonade"]
CMD ["--help"]
