"use client";

import { useEffect, useRef } from "react";

import { RideSocket, type ServerMessage } from "@/lib/ws";

/** Opens a ride WebSocket for the lifetime of the component. The handler
 * ref is kept fresh so callers can close over changing state safely.
 * Returns the socket ref for driver dispatch subscribe/unsubscribe. */
export function useRideSocket(handler: (message: ServerMessage) => void) {
  const handlerRef = useRef(handler);
  handlerRef.current = handler;
  const socketRef = useRef<RideSocket | null>(null);

  useEffect(() => {
    const socket = new RideSocket();
    socketRef.current = socket;
    const off = socket.on((message) => handlerRef.current(message));
    socket.connect();
    return () => {
      off();
      socket.close();
      socketRef.current = null;
    };
  }, []);

  return socketRef;
}
