#!/bin/bash

cd /app/backend
uv run app.py &
cd /app/frontend
PORT=3001 bunx serve@latest out &
nginx -g "daemon off;" &
wait
