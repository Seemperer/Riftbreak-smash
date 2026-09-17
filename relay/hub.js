import crypto from "node:crypto";
import Redis from "ioredis";
import { getRoom, normalizeRoom, redis, roomStoreReady, tokenHash } from "./room-store.js";

const CHANNEL = "riftsmash:relay:v1";
const AUTH_TIMEOUT_MS = 8000;
const MAX_MESSAGE_BYTES = 48 * 1024;
const MAX_MESSAGES_PER_SECOND = 180;
const HOST_TYPES = new Set(["hello", "lobby", "snap", "pong", "bye"]);
const GUEST_TYPES = new Set(["pick", "in", "pause", "ping", "bye"]);
const connections = new Map();
const instanceId = crypto.randomUUID();
let subscriber;
let listening = false;

function send(socket, payload) {
  if (socket.readyState === socket.OPEN) {
    try {
      socket.send(JSON.stringify(payload));
    } catch {
      // The close handler performs cleanup.
    }
  }
}

function close(socket, code, reason) {
  try {
    socket.close(code, reason);
  } catch {
    // Closing a socket is best effort.
  }
}

function forwardLocal(event) {
  for (const [socket, connection] of connections) {
    if (connection.authenticated && connection.room === event.room && connection.role === event.target) {
      send(socket, event.payload);
    }
  }
}

async function ensureSubscriber() {
  if (listening || !roomStoreReady()) return;
  listening = true;
  try {
    subscriber = new Redis(process.env.REDIS_URL, {
      connectTimeout: 5000,
      maxRetriesPerRequest: null,
      retryStrategy: (attempt) => Math.min(attempt * 200, 2000),
    });
    subscriber.on("error", (error) => console.error("[relay subscriber]", error.message));
    subscriber.on("message", (_, raw) => {
      try {
        const event = JSON.parse(raw);
        if (event.origin !== instanceId && event.room && event.target && event.payload) {
          forwardLocal(event);
        }
      } catch {
        // Invalid cross-instance events are ignored.
      }
    });
    await subscriber.subscribe(CHANNEL);
  } catch (error) {
    listening = false;
    console.error("[relay] subscriber unavailable", error);
  }
}

export function register(socket, rawRoom) {
  const room = normalizeRoom(rawRoom);
  if (!room || !roomStoreReady()) {
    close(socket, 1013, "online service unavailable");
    return;
  }
  const timer = setTimeout(() => {
    const connection = connections.get(socket);
    if (connection && !connection.authenticated) close(socket, 1008, "authentication timed out");
  }, AUTH_TIMEOUT_MS);
  connections.set(socket, {
    room,
    role: null,
    authenticated: false,
    timer,
    windowAt: Date.now(),
    messages: 0,
  });
  void ensureSubscriber();
}

async function authenticate(socket, connection, message) {
  if (!message || message.t !== "_auth" || typeof message.ticket !== "string" || message.ticket.length > 128) {
    close(socket, 1008, "authenticate first");
    return;
  }
  const room = await getRoom(connection.room);
  const hash = tokenHash(message.ticket);
  const role = room?.host === hash ? "host" : room?.guest === hash ? "guest" : null;
  if (!role) {
    close(socket, 1008, "invalid room ticket");
    return;
  }
  connection.authenticated = true;
  connection.role = role;
  clearTimeout(connection.timer);
  send(socket, { t: "_ready", role });
}

function acceptRate(connection) {
  const now = Date.now();
  if (now - connection.windowAt >= 1000) {
    connection.windowAt = now;
    connection.messages = 0;
  }
  connection.messages += 1;
  return connection.messages <= MAX_MESSAGES_PER_SECOND;
}

export async function receive(socket, raw) {
  const connection = connections.get(socket);
  if (!connection || Buffer.byteLength(raw) > MAX_MESSAGE_BYTES) {
    close(socket, 1009, "message too large");
    return;
  }
  let message;
  try {
    message = JSON.parse(raw);
  } catch {
    return;
  }
  if (!connection.authenticated) {
    try {
      await authenticate(socket, connection, message);
    } catch {
      close(socket, 1013, "online service unavailable");
    }
    return;
  }
  if (!message || typeof message !== "object" || !acceptRate(connection)) {
    close(socket, 1008, "rate limit exceeded");
    return;
  }
  const allowed = connection.role === "host" ? HOST_TYPES : GUEST_TYPES;
  if (!allowed.has(message.t)) {
    close(socket, 1008, "message is not allowed for this player");
    return;
  }
  const event = {
    origin: instanceId,
    room: connection.room,
    target: connection.role === "host" ? "guest" : "host",
    payload: message,
  };
  forwardLocal(event);
  try {
    await redis().publish(CHANNEL, JSON.stringify(event));
  } catch {
    close(socket, 1013, "relay unavailable");
  }
}

export function unregister(socket) {
  const connection = connections.get(socket);
  if (!connection) return;
  clearTimeout(connection.timer);
  connections.delete(socket);
}
