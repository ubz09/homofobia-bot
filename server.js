import express from "express";
import fetch from "node-fetch";
import { Client, GatewayIntentBits } from "discord.js";
import dotenv from "dotenv";
import cors from "cors";

dotenv.config();
const app = express();
app.use(express.json());
app.use(cors());

// --- Configuración del bot ---
const client = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMembers],
});

const DISCORD_CLIENT_ID = process.env.DISCORD_CLIENT_ID;
const DISCORD_CLIENT_SECRET = process.env.DISCORD_CLIENT_SECRET;
const DISCORD_REDIRECT_URI = process.env.DISCORD_REDIRECT_URI || "https://hmfb-production.up.railway.app/auth/discord/callback";
const GUILD_ID = process.env.GUILD_ID; // ID del servidor Discord
const ROLE_1MES = process.env.ROLE_1MES;
const ROLE_3MESES = process.env.ROLE_3MESES;
const ROLE_6MESES = process.env.ROLE_6MESES;
const ROLE_PERM = process.env.ROLE_PERM;

// --- Endpoint: Redirección al login de Discord ---
app.get("/auth/discord", (req, res) => {
  const redirect = `https://discord.com/api/oauth2/authorize?client_id=${DISCORD_CLIENT_ID}&redirect_uri=${encodeURIComponent(
    DISCORD_REDIRECT_URI
  )}&response_type=code&scope=identify`;
  res.redirect(redirect);
});

// --- Endpoint: Callback de Discord OAuth2 ---
app.get("/auth/discord/callback", async (req, res) => {
  const code = req.query.code;
  if (!code) return res.json({ error: "Falta el código de autorización." });

  try {
    const params = new URLSearchParams();
    params.append("client_id", DISCORD_CLIENT_ID);
    params.append("client_secret", DISCORD_CLIENT_SECRET);
    params.append("grant_type", "authorization_code");
    params.append("code", code);
    params.append("redirect_uri", DISCORD_REDIRECT_URI);

    const tokenResponse = await fetch("https://discord.com/api/oauth2/token", {
      method: "POST",
      body: params,
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });

    const tokenData = await tokenResponse.json();
    if (!tokenData.access_token)
      return res.json({ error: "No se pudo obtener token de acceso." });

    const userResponse = await fetch("https://discord.com/api/users/@me", {
      headers: { Authorization: `Bearer ${tokenData.access_token}` },
    });
    const userData = await userResponse.json();

    res.json({ id: userData.id, username: userData.username });
  } catch (err) {
    console.error("Error OAuth2:", err);
    res.json({ error: "Error al conectar con Discord." });
  }
});

// --- Endpoint: Asignar rol ---
app.post("/assign-role", async (req, res) => {
  const { discordId, paquete } = req.body;
  if (!discordId || !paquete)
    return res.json({ ok: false, error: "Datos incompletos." });

  try {
    const guild = await client.guilds.fetch(GUILD_ID);
    const member = await guild.members.fetch(discordId);

    let roleId;
    if (paquete === "1mes") roleId = ROLE_1MES;
    else if (paquete === "3meses") roleId = ROLE_3MESES;
    else if (paquete === "6meses") roleId = ROLE_6MESES;
    else if (paquete === "permanente") roleId = ROLE_PERM;

    if (!roleId) return res.json({ ok: false, error: "Rol no encontrado." });

    await member.roles.add(roleId);
    console.log(`✅ Rol ${paquete} asignado a ${discordId}`);
    res.json({ ok: true });
  } catch (err) {
    console.error("Error asignando rol:", err);
    res.json({ ok: false, error: err.message });
  }
});

// --- Login del bot ---
client.login(process.env.DISCORD_TOKEN)
  .then(() => console.log("🤖 Bot conectado correctamente a Discord."))
  .catch(err => console.error("❌ Error al conectar el bot:", err));

// --- Inicio del servidor ---
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`🚀 Servidor corriendo en puerto ${PORT}`));
