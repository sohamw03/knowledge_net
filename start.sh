#!/bin/bash
cd backend
uv run app.py &
cd ../frontend
bun start
wait
