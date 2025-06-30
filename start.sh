#!/bin/bash
cd /frontend
bun start &
cd ../backend
uv run app.py
wait
