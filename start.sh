#!/bin/bash

# Start backend
echo "Starting backend..."
cd /app/backend
uv run app.py &
BACKEND_PID=$!
echo "Backend started with PID: $BACKEND_PID"

# Wait for backend to be ready (port 5000)
echo "Waiting for backend (port 5000) to be ready..."
while ! nc -z 127.0.0.1 5000; do
  sleep 0.1
done
echo "Backend is ready."

# Start frontend
echo "Starting frontend..."
cd /app/frontend
npx serve@latest -l 3001 out &
FRONTEND_PID=$!
echo "Frontend started with PID: $FRONTEND_PID"

# Wait for frontend to be ready (port 3001)
echo "Waiting for frontend (port 3001) to be ready..."
while ! nc -z 127.0.0.1 3001; do
  sleep 0.1
done
echo "Frontend is ready."

# Start Nginx
echo "Starting Nginx..."
nginx -g "daemon off;" &
NGINX_PID=$!
echo "Nginx started with PID: $NGINX_PID"

# Wait for all background processes (backend, frontend, Nginx)
wait $BACKEND_PID $FRONTEND_PID $NGINX_PID
echo "All services exited."
