// Vercel route stub + backward-compatible long-lived server.
// Vercel serverless functions cannot hold a match-long WebSocket, so the real
// relay lives in relay/server.js (Render/Fly/VPS). Set RELAY_WS_URL on the
// rooms API to point there. This file stays so existing imports keep working
// in long-lived Node, and Vercel HTTP hits get a clear message.
import { createServer } from "node:http";
import { WebSocketServer } from "ws";
import { register, receive, unregister } from "../relay/hub.js";

const server = createServer((_, res) => {
  res.statusCode = 426;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.end(JSON.stringify({
    error: "use a WebSocket connection (deploy relay/server.js on a long-lived host; set RELAY_WS_URL)",
  }));
});

const wss = new WebSocketServer({ server, maxPayload: 65536 });

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

export default server;
