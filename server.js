import express from "express";
import fetch from "node-fetch";
import { Client, GatewayIntentBits } from "discord.js";
import bodyParser from "body-parser";
import cors from "cors";
import dotenv from "dotenv";

dotenv.config();
const app = express();
app.use(cors());
app.use(bodyParser.json());

// --- Variables del entorno ---
const TOKEN = process.env.DISCORD_BOT_TOKEN;
const CLIENT_ID = process.env.DISCORD_CLIENT_ID;
const CLIENT_SECRET = process.env.DISCORD_CLIENT_SECRET;
const REDIRECT_URI = process.env.DISCORD_REDIRECT_URI;
const GUILD_ID = process.env.DISCORD_GUILD_ID;

// --- Bot de Discord ---
const bot = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMembers],
});

bot.once("ready", () => {
  console.log(`✅ Bot conectado como ${bot.user.tag}`);
});

bot.login(TOKEN);

// --- Endpoint base ---
app.get("/", (req, res) => {
  res.send("HMFB Role Assigner API está activa ✅");
});

// --- Ruta para iniciar sesión con Discord ---
app.get("/auth/discord", (req, res) => {
  if (!CLIENT_ID || !REDIRECT_URI) {
    return res.status(500).send("⚠️ Variables OAuth2 no configuradas.");
  }

  const redirect = `https://discord.com/api/oauth2/authorize?client_id=${CLIENT_ID}&redirect_uri=${encodeURIComponent(
    REDIRECT_URI
  )}&response_type=code&scope=identify`;
  res.redirect(redirect);
});

// --- Callback de Discord (cuando vuelve del login) ---
app.get("/auth/discord/callback", async (req, res) => {
  const code = req.query.code;
  if (!code) return res.status(400).send("Falta el código OAuth2.");

  try {
    // Intercambiamos el code por un token de usuario
    const params = new URLSearchParams();
    params.append("client_id", CLIENT_ID);
    params.append("client_secret", CLIENT_SECRET);
    params.append("grant_type", "authorization_code");
    params.append("code", code);
    params.append("redirect_uri", REDIRECT_URI);

    const tokenRes = await fetch("https://discord.com/api/oauth2/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: params,
    });

    const tokenData = await tokenRes.json();
    if (!tokenData.access_token) {
      console.error("OAuth2 error:", tokenData);
      return res.status(400).send("Error al obtener el token de Discord.");
    }

    // Obtenemos la info del usuario
    const userRes = await fetch("https://discord.com/api/users/@me", {
      headers: { Authorization: `Bearer ${tokenData.access_token}` },
    });
    const user = await userRes.json();

    console.log(`🔹 Usuario autenticado: ${user.username} (${user.id})`);

    // Redirigimos al frontend con la ID del usuario
    res.redirect(
      `https://hmfb-production.up.railway.app?discordId=${user.id}`
    );
  } catch (err) {
    console.error(err);
    res.status(500).send("Error interno en el proceso OAuth2.");
  }
});

// --- Asignación automática de roles ---
app.post("/assign-role", async (req, res) => {
  const { discordId, paquete } = req.body;
  if (!discordId || !paquete)
    return res.status(400).json({ ok: false, error: "Datos inválidos." });

  const guild = await bot.guilds.fetch(GUILD_ID);
  const member = await guild.members.fetch(discordId).catch(() => null);

  if (!member)
    return res
      .status(404)
      .json({ ok: false, error: "Usuario no encontrado en el servidor." });

  const roles = {
    "1mes": process.env.ROLE_1MES,
    "3meses": process.env.ROLE_3MESES,
    "6meses": process.env.ROLE_6MESES,
    permanente: process.env.ROLE_PERMANENTE,
  };

  const roleId = roles[paquete];
  if (!roleId)
    return res
      .status(400)
      .json({ ok: false, error: "Paquete o rol no configurado." });

  try {
    await member.roles.add(roleId);
    console.log(`✅ Rol asignado a ${member.user.tag}: ${paquete}`);
    res.json({ ok: true });
  } catch (err) {
    console.error("Error asignando rol:", err);
    res.status(500).json({ ok: false, error: "Error asignando rol." });
  }
});

// --- Puerto Railway ---
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`🚀 Servidor activo en puerto ${PORT}`));
