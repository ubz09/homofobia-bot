HMFB Discord Role Assigner - Backend
===================================

Descripción
-----------
Proyecto Node.js (Express) simple para asignar roles en Discord cuando un usuario compra un paquete en tu web.
Contiene un endpoint POST /assign-role que usa el token del bot para llamar a la API de Discord y añadir roles.

Estructura
---------
- server.js          -> servidor principal (Express)
- package.json       -> dependencias y script start
- .env.example       -> ejemplo de variables de entorno (no subir token a repos)
- README.txt         -> este archivo

Variables de entorno (rellena en Railway/Render)
------------------------------------------------
- DISCORD_BOT_TOKEN : Token del bot (NO compartir públicamente)
- GUILD_ID          : ID de tu servidor
- ROLE_ID_1MES      : ID del rol para 1 mes
- ROLE_ID_3MESES    : ID del rol para 3 meses
- ROLE_ID_6MESES    : ID del rol para 6 meses
- ROLE_ID_PERMANENTE: ID del rol permanente
- PAYMENT_SECRET    : (opcional) secreto para validar peticiones desde tu frontend

Despliegue rápido en Railway (pasos)
-----------------------------------
1. Crea cuenta en https://railway.app y crea un nuevo Project -> "Deploy from GitHub" o "Start from scratch".
2. Sube este repo (o haz zip upload). Railway detectará Node.js.
3. En Settings / Variables añade las variables de entorno (copia desde .env.example).
4. Presiona Deploy; Railway te dará una URL pública del servicio (ej: https://your-project.up.railway.app).
5. Prueba health: GET https://your-project.up.railway.app/health

Uso desde el frontend (ejemplo)
------------------------------
Al completar la compra (ideal: valida la compra en backend mediante webhook del proveedor), llama a:
POST https://TU_BACKEND/assign-role
Content-Type: application/json
Body (ejemplo):
{
  "discordId": "123456789012345678",
  "paquete": "3meses",
  "transactionId": "TX-12345",
  "signature": "mi_secret_local_demo"  // si tienes PAYMENT_SECRET configurado
}

Seguridad importante
--------------------
- Nunca pongas el BOT TOKEN en el frontend ni en repositorios públicos.
- Valida la compra en el backend (webhooks firmados: Stripe/PayPal/MercadoPago). No confíes en el cliente.
- Asegúrate que el rol del BOT en Discord esté por encima de los roles que debe asignar.

Notas
-----
- Si querés, puedo añadir endpoints para remover roles al expirar el paquete o un pequeño scheduler para revocar roles automáticamente (requiere persistencia en DB con fechas de expiración).
- Puedo añadir el flujo OAuth para obtener el discordId automáticamente (me lo pediste antes), dímelo si lo querés integrado.
