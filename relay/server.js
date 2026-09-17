// Standalone long-lived relay server for Riftbreak Smash Internet Rooms.
// Deploy this on Render / Fly.io / a VPS — NOT as a Vercel serverless function
// (serverless functions cannot hold a match-long WebSocket).
//
//   npm install            # installs ws + ioredis
//   REDIS_URL=rediss://... PORT=8080 node relay/server.js
//
// The rooms API (api/rooms.js) can run on Vercel; point it at this host with:
//   RELAY_WS_URL=wss://<this-host>  (+ same REDIS_URL on both services)
//
// Protocol: GET /api/relay?room=XXXXXXXX -> WebSocket -> {"t":"_auth","ticket":...}
// Host sends: hello/lobby/snap/pong/bye. Guest sends: pick/in/pause/ping/bye.
// Real-time WebSocket JSON, host-authoritative snapshots at ~20Hz.

import { createServer } from "node:http";
import { WebSocketServer } from "ws";
import { register, receive, unregister } from "./hub.js";
import { roomStoreReady } from "./room-store.js";

const PORT = Number(process.env.PORT || 8080);

const server = createServer((req, res) => {
  const url = new URL(req.url || "/", "http://localhost");
  if (url.pathname === "/health" || url.pathname === "/api/health") {
    res.statusCode = roomStoreReady() ? 200 : 503;
    res.setHeader("Content-Type", "application/json; charset=utf-8");
    res.end(JSON.stringify({
      status: roomStoreReady() ? "ok" : "not_configured",
      service: "riftbreak-relay",
      transport: "websocket",
    }));
    return;
  }
  res.statusCode = 426;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.end(JSON.stringify({ error: "use a WebSocket connection at /api/relay?room=CODE" }));
});

const wss = new WebSocketServer({ server, path: "/api/relay", maxPayload: 65536 });

wss.on("connection", (socket, request) => {
  const url = new URL(request.url || "/", "http://localhost");
  const room = url.searchParams.get("room");
  register(socket, room);

  socket.on("message", (data, isBinary) => {
    if (!isBinary) {
      void receive(socket, data.toString());
    }
  });

  const close = () => void unregister(socket);
  socket.on("close", close);
  socket.on("error", close);
});

server.listen(PORT, "0.0.0.0", () => {
  console.log(`[riftbreak-relay] listening on :${PORT} (redis ${roomStoreReady() ? "configured" : "MISSING — set REDIS_URL"})`);
});
