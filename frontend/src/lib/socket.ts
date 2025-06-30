import { io, Socket } from "socket.io-client";

let socket: Socket | null = null;

export const initializeSocket = (url?: string) => {
  // In production (Docker), use the same host where the frontend is served
  // This will route through nginx proxy to the backend
  const socketUrl = url || process.env.NEXT_PUBLIC_KNET_BACKEND || (typeof window !== 'undefined' ? window.location.origin : "http://127.0.0.1:3000");

  if (!socket) {
    socket = io(socketUrl, {
      transports: ["websocket"],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
      path: "/socket.io/",
    });
  }
  return socket;
};

export const getSocket = () => {
  if (!socket) {
    throw new Error("Socket not initialized. Call initializeSocket first.");
  }
  return socket;
};

export const disconnectSocket = () => {
  if (socket) {
    socket.disconnect();
    socket = null;
  }
};
