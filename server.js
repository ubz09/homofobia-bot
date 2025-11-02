import express from "express";
import fetch from "node-fetch";
import dotenv from "dotenv";
import { Client, GatewayIntentBits } from "discord.js";

dotenv.config();

const app = express();
app.use(express.json());

// Discord Client (para aparecer en línea)
const client = new Client({ intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMembers] });
client.once("ready", () => console.log(`✅ Bot conectado como ${client.user.tag}`));
client.login(process.env.DISCORD_BOT_TOKEN);

// Config
const BOT_TOKEN = process.env.DISCORD_BOT_TOKEN;
const GUILD_ID = process.env.GUILD_ID;
const PAYMENT_SECRET = process.env.PAYMENT_SECRET || null;
const ROLES = {
  "1mes": process.env.ROLE_ID_1MES || "1434549017638993970",
  "3meses": process.env.ROLE_ID_3MESES || "1434549017638993970",
  "6meses": process.env.ROLE_ID_6MESES || "1434549017638993970",
  "permanente": process.env.ROLE_ID_PERMANENTE || "1434549017638993970"
};

// Asignar rol usando API REST
async function assignRoleToUser(discordUserId, roleId) {
  const url = `https://discord.com/api/v10/guilds/${GUILD_ID}/members/${discordUserId}/roles/${roleId}`;
  const res = await fetch(url, {
    method: "PUT",
    headers: { Authorization: `Bot ${BOT_TOKEN}`, "Content-Type": "application/json" }
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Discord API error ${res.status}: ${text}`);
  }
  return true;
}

// Endpoint principal
app.post("/assign-role", async (req, res) => {
  try {
    const { discordId, paquete, signature } = req.body;
    if (!discordId || !paquete) return res.status(400).json({ error: "Faltan datos" });

    if (PAYMENT_SECRET && signature !== PAYMENT_SECRET)
      return res.status(401).json({ error: "Firma inválida" });

    const roleId = ROLES[paquete];
    if (!roleId) return res.status(400).json({ error: "Paquete no válido" });

    await assignRoleToUser(discordId, roleId);
    res.json({ ok: true, message: "Rol asignado ✅", roleId });
  } catch (err) {
    console.error("Error:", err);
    res.status(500).json({ error: err.message });
  }
});

// Health check
app.get("/health", (_, res) => res.json({ ok: true, ts: Date.now() }));

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server listening on port ${PORT}`));
