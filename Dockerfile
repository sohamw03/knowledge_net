# Read the doc: https://huggingface.co/docs/hub/spaces-sdks-docker
# you will also find guides on how best to write your Dockerfile

FROM python:3.12

RUN --mount=type=secret,id=GOOGLE_API_KEY,mode=0444,required=true
RUN --mount=type=secret,id=ALLOWED_ORIGINS,mode=0444,required=true
RUN --mount=type=secret,id=NEXT_PUBLIC_BACKEND_URL,mode=0444,required=true

RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

WORKDIR /app

RUN pip install uv
COPY --chown=user . /app

# ---------- Backend ----------
WORKDIR /app/backend
RUN uv sync
RUN uv run playwright install chromium

USER root
RUN apt update
RUN apt install -y libnss3\
 libnspr4\
 libdbus-1-3\
 libatk1.0-0\
 libatk-bridge2.0-0\
 libcups2\
 libxcomposite1\
 libxdamage1\
 libxfixes3\
 libxrandr2\
 libgbm1\
 libxkbcommon0\
 libasound2\
 libatspi2.0-0\
 nginx
USER user
RUN mkdir -p /var/lib/nginx/body && chown -R user:user /var/lib/nginx

# ---------- Frontend ----------
WORKDIR /app/frontend

# Install system dependencies
USER root
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    bash \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (LTS)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs
USER user

# Install Bun
RUN curl -fsSL https://bun.sh/install | bash
ENV PATH="/home/user/.bun/bin:${PATH}"

RUN bun install
RUN bun run build

WORKDIR /app

# ---------- Nginx ----------
USER root
COPY nginx.conf /etc/nginx/nginx.conf
USER user

RUN chmod +x /app/start.sh
CMD ["/app/start.sh"]
