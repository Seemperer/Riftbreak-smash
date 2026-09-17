import crypto from "node:crypto";
import Redis from "ioredis";

const ROOM_TTL_SECONDS = 2 * 60 * 60;
const CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789";
const CODE_LENGTH = 8;
const ROOM_PREFIX = "riftsmash:room:";

let client;

export class RoomError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

export function roomStoreReady() {
  return Boolean(process.env.REDIS_URL);
}

export function redis() {
  if (!process.env.REDIS_URL) {
    throw new RoomError(503, "online room storage has not been configured");
  }
  if (!client) {
    client = new Redis(process.env.REDIS_URL, {
      connectTimeout: 5000,
      maxRetriesPerRequest: 1,
      retryStrategy: (attempt) => Math.min(attempt * 200, 2000),
    });
    client.on("error", (error) => console.error("[redis]", error.message));
  }
  return client;
}

export function normalizeRoom(value) {
  const room = String(value || "").toUpperCase().replace(/[^A-Z0-9]/g, "");
  return new RegExp(`^[${CODE_ALPHABET}]{${CODE_LENGTH}}$`).test(room) ? room : null;
}

export function tokenHash(token) {
  return crypto.createHash("sha256").update(String(token)).digest("hex");
}

function ticket() {
  return crypto.randomBytes(32).toString("base64url");
}

function roomCode() {
  let code = "";
  for (let index = 0; index < CODE_LENGTH; index += 1) {
    code += CODE_ALPHABET[crypto.randomInt(CODE_ALPHABET.length)];
  }
  return code;
}

function key(room) {
  return `${ROOM_PREFIX}${room}`;
}

export async function createRoom() {
  const db = redis();
  for (let attempt = 0; attempt < 8; attempt += 1) {
    const room = roomCode();
    const rawTicket = ticket();
    const record = JSON.stringify({
      v: 1,
      host: tokenHash(rawTicket),
      guest: null,
      createdAt: Date.now(),
    });
    const created = await db.set(key(room), record, "EX", ROOM_TTL_SECONDS, "NX");
    if (created === "OK") {
      return { room, ticket: rawTicket, role: "host", expiresIn: ROOM_TTL_SECONDS };
    }
  }
  throw new RoomError(503, "could not reserve a room; please try again");
}

export async function joinRoom(value) {
  const room = normalizeRoom(value);
  if (!room) {
    throw new RoomError(400, "room code must be eight characters");
  }
  const rawTicket = ticket();
  const result = await redis().eval(
    "local raw = redis.call('GET', KEYS[1]) " +
      "if not raw then return 0 end " +
      "local item = cjson.decode(raw) " +
      "if item.guest then return 1 end " +
      "item.guest = ARGV[1] " +
      "redis.call('SET', KEYS[1], cjson.encode(item), 'KEEPTTL') " +
      "return 2",
    1,
    key(room),
    tokenHash(rawTicket),
  );
  if (Number(result) === 0) throw new RoomError(404, "room not found or expired");
  if (Number(result) === 1) throw new RoomError(409, "room is already full");
  return { room, ticket: rawTicket, role: "guest", expiresIn: ROOM_TTL_SECONDS };
}

export async function getRoom(value) {
  const room = normalizeRoom(value);
  if (!room) return null;
  const raw = await redis().get(key(room));
  if (!raw) return null;
  try {
    return { room, ...JSON.parse(raw) };
  } catch {
    return null;
  }
}
