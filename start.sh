#!/bin/bash
cd /app/frontend
bun start &
cd ../backend
uv run app.py
wait
