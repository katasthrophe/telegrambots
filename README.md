# 🎵 Telegram YouTube Music Bot

Un bot de Telegram en Python que permite a los usuarios enviar cualquier enlace de YouTube o YouTube Shorts, previsualizar la información (título, duración, canal y miniatura), y elegir si descargarlo en formato **MP3** o **M4A**.

---

## 🚀 Requisitos Previos

1. **Python 3.10+**: Ya instalado en tu sistema.
2. **FFmpeg**: Requerido por `yt-dlp` para convertir y extraer audio a MP3 y M4A.
   - En Windows puedes instalarlo fácilmente abriendo una terminal (PowerShell o CMD) y ejecutando:
     ```bash
     winget install Gyan.FFmpeg
     ```
   - Reinicia tu terminal después de instalarlo.

---

## 🛠️ Configuración Paso a Paso

### 1. Obtener el Token de Telegram
1. Abre Telegram y busca al bot oficial [@BotFather](https://t.me/BotFather).
2. Escribe `/newbot` y sigue las instrucciones para asignarle un nombre y un usuario.
3. Copia el token HTTP API que te entregue (ejemplo: `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ`).

### 2. Configurar el archivo `.env`
1. Entra a la carpeta del proyecto.
2. Copia `.env.example` a `.env` (o renómbralo).
3. Pega tu token:
   ```env
   TELEGRAM_BOT_TOKEN=tu_token_aqui
   ```

### 3. Instalar Dependencias
En la carpeta del proyecto, ejecuta:
```bash
py -m pip install -r requirements.txt
```

---

## ▶️ Ejecución Local

Puedes iniciar el bot de dos formas:

- **Opción 1:** Doble clic en `run.bat`.
- **Opción 2:** Desde la terminal:
  ```bash
  py bot.py
  ```

---

## ☁️ Despliegue en la Nube (24/7 Gratis)

### Opción 1: Despliegue en Koyeb (Con Docker y GitHub)
1. Sube esta carpeta a un repositorio privado o público en **GitHub**.
2. Regístrate en [Koyeb.com](https://www.koyeb.com) (plan gratuito).
3. Haz clic en **Create App** > Selecciona **GitHub**.
4. Selecciona tu repositorio y elige **Dockerfile** como método de construcción.
5. En la sección **Environment Variables**, añade:
   - Nombre: `TELEGRAM_BOT_TOKEN`
   - Valor: `tu_token_aqui`
6. En **Service Type**, selecciona **Worker** (un proceso en segundo plano continuo).
7. Haz clic en **Deploy**. ¡Tu bot estará activo 24/7!

---

### Opción 2: Despliegue en un VPS Linux (Oracle Cloud / Ubuntu / Debian)
En tu servidor remoto conectado por SSH:

1. Clona o sube los archivos a tu servidor:
   ```bash
   git clone <tu-repositorio> bot-musica
   cd bot-musica
   ```
2. Instala Python y FFmpeg:
   ```bash
   sudo apt update
   sudo apt install -y python3 python3-pip python3-venv ffmpeg
   ```
3. Crea un entorno virtual e instala los paquetes:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
4. Configura tu token:
   ```bash
   nano .env
   # Escribe: TELEGRAM_BOT_TOKEN=tu_token
   # Guarda con Ctrl+O y sal con Ctrl+X
   ```
5. Déjalo corriendo 24/7 como servicio con `systemd`:
   ```bash
   sudo nano /etc/systemd/system/telegram-bot.service
   ```
   Pega el siguiente contenido (reemplaza `tu_usuario` y la ruta si es diferente):
   ```ini
   [Unit]
   Description=Telegram YouTube Music Bot
   After=network.target

   [Service]
   Type=simple
   User=ubuntu
   WorkingDirectory=/home/ubuntu/bot-musica
   ExecStart=/home/ubuntu/bot-musica/venv/bin/python bot.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```
6. Inicia el servicio:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now telegram-bot
   ```
   Para ver su estado o logs:
   ```bash
   sudo systemctl status telegram-bot
   journalctl -u telegram-bot -f
   ```

---

## 🍪 Solución a bloqueos de YouTube en servidores
Si YouTube llega a pedir confirmación (`Sign in to confirm you're not a bot`), genera un archivo `cookies.txt` desde tu navegador (usando extensiones como *Get cookies.txt LOCALLY*) y colócalo en la misma carpeta del bot. El bot lo detectará y usará automáticamente.

---

## 🎧 Uso del Bot

1. Abre tu bot en Telegram y presiona **/start**.
2. Envía cualquier enlace de YouTube (por ejemplo, `https://youtu.be/dQw4w9WgXcQ` o enlaces estándar / shorts).
3. El bot responderá con la miniatura del video, título, canal y duración, junto con dos botones:
   - 🎵 **MP3 (192 kbps)**
   - 🎧 **M4A (Original)**
4. Presiona el botón del formato deseado y el bot descargará, procesará y te enviará la canción directamente al chat como un archivo de audio reproducible.
