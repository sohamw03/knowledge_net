import { io, Socket } from "socket.io-client";

let socket: Socket | null = null;

export const initializeSocket = (url: string = process.env.NEXT_PUBLIC_KNET_BACKEND!) => {
  url = process.env.NEXT_PUBLIC_KNET_BACKEND || "http://127.0.0.1:5000";
  if (!socket) {
    socket = io(url, {
      transports: ["websocket"],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
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
