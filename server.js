import express from "express";
import path from "path";
import { fileURLToPath } from "url";
import { Client, GatewayIntentBits, REST, Routes } from "discord.js";
import dotenv from "dotenv";

dotenv.config();

// ==== Discord Bot Config ====
const TOKEN = process.env.TOKEN;
const CLIENT_ID = process.env.CLIENT_ID;
const GUILD_ID = process.env.GUILD_ID; // Opcional, si el bot solo trabaja en un servidor

const client = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMembers],
});

// ==== Express Setup ====
const app = express();
const PORT = process.env.PORT || 3000;

// Rutas y archivos estáticos
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Servir archivos estáticos (como index.html, css, etc)
app.use(express.static(__dirname));

// Ruta raíz: muestra tu página web
app.get("/", (req, res) => {
  res.sendFile(path.join(__dirname, "index.html"));
});

// ==== Discord Bot ====
client.once("ready", () => {
  console.log(`✅ Bot conectado como ${client.user.tag}`);
});

// Ejemplo: comando o endpoint que otorga roles
app.get("/assign-role", async (req, res) => {
  const userId = req.query.user;
  const roleId = req.query.role;

  if (!userId || !roleId) {
    return res.status(400).send("Faltan parámetros: user o role");
  }

  try {
    const guild = await client.guilds.fetch(GUILD_ID);
    const member = await guild.members.fetch(userId);
    await member.roles.add(roleId);
    res.send(`✅ Rol otorgado a <@${userId}>`);
  } catch (error) {
    console.error("❌ Error otorgando rol:", error);
    res.status(500).send("Error al otorgar rol");
  }
});

// ==== Iniciar Bot y Servidor ====
client.login(TOKEN);

app.listen(PORT, () => {
  console.log(`🌐 Servidor web en http://localhost:${PORT}`);
});
