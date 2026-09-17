import { createRoom, joinRoom, RoomError, roomStoreReady } from "../relay/room-store.js";

const MAX_BODY_BYTES = 4096;

function cors(res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  res.setHeader("Cache-Control", "no-store");
}

function send(res, status, body) {
  cors(res);
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.end(JSON.stringify(body));
}

function readJson(req) {
  return new Promise((resolve, reject) => {
    let size = 0;
    let raw = "";
    req.setEncoding("utf8");
    req.on("data", (chunk) => {
      size += Buffer.byteLength(chunk);
      if (size > MAX_BODY_BYTES) {
        reject(new RoomError(413, "request is too large"));
        req.destroy();
        return;
      }
      raw += chunk;
    });
    req.on("end", () => {
      try {
        resolve(raw ? JSON.parse(raw) : {});
      } catch {
        reject(new RoomError(400, "request must be valid JSON"));
      }
    });
    req.on("error", () => reject(new RoomError(400, "request could not be read")));
  });
}

function relayUrl(req, room) {
  // Prefer a dedicated long-lived WebSocket host (Render/Fly/VPS) because
  // Vercel serverless functions cannot hold a match-long WebSocket.
  // Set RELAY_WS_URL=wss://<relay-host> alongside REDIS_URL.
  const override = (process.env.RELAY_WS_URL || "").trim().replace(/\/$/, "");
  if (override) {
    return `${override}/api/relay?room=${encodeURIComponent(room)}`;
  }
  const host = req.headers["x-forwarded-host"] || req.headers.host;
  const proto = req.headers["x-forwarded-proto"] || "https";
  const wsProto = proto === "http" ? "ws" : "wss";
  return `${wsProto}://${host}/api/relay?room=${encodeURIComponent(room)}`;
}

export default async function handler(req, res) {
  if (req.method === "OPTIONS") {
    cors(res);
    res.statusCode = 204;
    res.end();
    return;
  }

  if (req.method === "GET") {
    send(res, roomStoreReady() ? 200 : 503, {
      status: roomStoreReady() ? "ok" : "not_configured",
      service: "riftbreak-online",
      transport: "websocket",
    });
    return;
  }

  if (req.method !== "POST") {
    send(res, 405, { error: "method not allowed" });
    return;
  }

  try {
    const body = await readJson(req);
    let reservation;
    if (body.op === "create") {
      reservation = await createRoom();
    } else if (body.op === "join") {
      reservation = await joinRoom(body.room);
    } else {
      throw new RoomError(400, "op must be create or join");
    }
    send(res, 200, { ...reservation, relayUrl: relayUrl(req, reservation.room) });
  } catch (error) {
    if (error instanceof RoomError) {
      send(res, error.status, { error: error.message });
      return;
    }
    console.error("[rooms] request failed", error);
    send(res, 503, { error: "online rooms are temporarily unavailable" });
  }
}
