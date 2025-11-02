// server.js
import express from "express";
import fetch from "node-fetch";
import dotenv from "dotenv";
dotenv.config();

const app = express();
app.use(express.json());

const BOT_TOKEN = process.env.DISCORD_BOT_TOKEN || "TU_TOKEN_AQUI";
const GUILD_ID = process.env.GUILD_ID || "TU_GUILD_ID";
const PAYMENT_SECRET = process.env.PAYMENT_SECRET || null; // opcional para verificar firmas
// Mapear paquetes a role IDs (usa mismas IDs o distintas)
const ROLES = {
  "1mes": process.env.ROLE_ID_1MES || "ROLE_ID_1MES_PLACEHOLDER",
  "3meses": process.env.ROLE_ID_3MESES || "ROLE_ID_3MESES_PLACEHOLDER",
  "6meses": process.env.ROLE_ID_6MESES || "ROLE_ID_6MESES_PLACEHOLDER",
  "permanente": process.env.ROLE_ID_PERMANENTE || "ROLE_ID_PERMANENTE_PLACEHOLDER"
};

// Helper: asigna rol usando la API de Discord
async function assignRoleToUser(discordUserId, roleId) {
  const url = `https://discord.com/api/v10/guilds/${GUILD_ID}/members/${discordUserId}/roles/${roleId}`;
  const res = await fetch(url, {
    method: "PUT",
    headers: {
      Authorization: `Bot ${BOT_TOKEN}`,
      "Content-Type": "application/json"
    }
  });
  if (!res.ok) {
    const text = await res.text();
    const err = new Error(`Discord API error ${res.status}: ${text}`);
    err.status = res.status;
    throw err;
  }
  return true;
}

// Endpoint público pero se espera validación (usar webhook en producción)
// Payload esperado (ejemplo):
// { "discordId": "123456789012345678", "paquete": "3meses", "transactionId": "...", "signature": "..." }
app.post("/assign-role", async (req, res) => {
  try {
    const { discordId, paquete, transactionId, signature } = req.body;
    if (!discordId || !paquete) return res.status(400).json({ error: "discordId y paquete son obligatorios" });

    // Validación simple opcional con PAYMENT_SECRET
    if (PAYMENT_SECRET) {
      if (!signature || signature !== PAYMENT_SECRET) {
        return res.status(401).json({ error: "Firma inválida" });
      }
    }

    const roleId = ROLES[paquete];
    if (!roleId) return res.status(400).json({ error: "Paquete no válido" });

    await assignRoleToUser(discordId, roleId);

    // Aquí podrías guardar el evento en una DB (registro de la asignación)
    return res.json({ ok: true, message: "Rol asignado ✅", roleId });
  } catch (err) {
    console.error("Error assign-role:", err);
    return res.status(err.status || 500).json({ error: err.message });
  }
});

// Health check
app.get("/health", (req, res) => res.json({ ok: true, ts: Date.now() }));

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server listening on port ${PORT}`));
