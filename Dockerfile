# Read the doc: https://huggingface.co/docs/hub/spaces-sdks-docker
# you will also find guides on how best to write your Dockerfile

FROM python:3.12

ARG GOOGLE_API_KEY
ARG ALLOWED_ORIGINS

RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

WORKDIR /app

RUN pip install uv
COPY --chown=user . /app
WORKDIR /app/backend
RUN uv sync
RUN uv run playwright install chromium

RUN apt-get install libnss3\
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
                    libatspi2.0-0

CMD ["uv", "run", "app.py"]
