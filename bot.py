import os
import re
import uuid
import shutil
import asyncio
import logging
import threading
import http.server
import socketserver
from pathlib import Path
from dotenv import load_dotenv
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.request import HTTPXRequest
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# Cargar variables de entorno desde .env
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Configurar logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Directorio temporal para descargas
TEMP_DIR = Path("downloads")
TEMP_DIR.mkdir(exist_ok=True)

# Patrón para detectar enlaces de YouTube
YT_REGEX = re.compile(
    r"(https?://(?:www\.|m\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[a-zA-Z0-9_-]+)"
)

def find_cookie_file() -> str | None:
    """Busca cookies desde variable de entorno o archivos locales."""
    env_cookies = os.getenv("YOUTUBE_COOKIES")
    cookie_path = Path("cookies.txt")
    if env_cookies:
        with open(cookie_path, "w", encoding="utf-8") as f:
            f.write(env_cookies)
        return str(cookie_path)
    if cookie_path.exists():
        return str(cookie_path)
    for p in Path(".").glob("*cookie*.txt"):
        return str(p)
    return None

def get_base_ydl_opts() -> dict:
    """Construye las opciones base de yt-dlp."""
    cookie_file = find_cookie_file()
    opts = {
        "quiet": True,
        "no_warnings": True,
    }
    if cookie_file:
        print(f"🍪 [INFO] Usando archivo de cookies: {cookie_file}")
        opts["cookiefile"] = cookie_file
    return opts

def format_duration(seconds: int | None) -> str:
    """Convierte segundos a formato MM:SS o HH:MM:SS."""
    if not seconds:
        return "Desconocida"
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    if hours > 0:
        return f"{hours}:{mins:02d}:{secs:02d}"
    return f"{mins}:{secs:02d}"

def extract_youtube_info(url: str) -> dict:
    """Extrae metadatos del video sin descargar."""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "skip_download": True,
    }
    cookie_file = find_cookie_file()
    if cookie_file:
        ydl_opts["cookiefile"] = cookie_file

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)

def download_audio(url: str, format_choice: str, output_path: str) -> tuple[str, dict]:
    """Descarga el audio en formato mp3 o m4a usando yt-dlp."""
    ydl_opts = get_base_ydl_opts()
    if format_choice == "mp3":
        ydl_opts.update({
            "format": "bestaudio/best",
            "outtmpl": f"{output_path}/%(id)s.%(ext)s",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        })
    else:  # m4a
        ydl_opts.update({
            "format": "bestaudio/best",
            "outtmpl": f"{output_path}/%(id)s.%(ext)s",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
            }],
        })

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        # Buscar el archivo generado en output_path
        files = [f for f in Path(output_path).glob(f"*.{format_choice}")]
        if not files:
            files = [f for f in Path(output_path).glob("*") if f.is_file()]
        if not files:
            raise FileNotFoundError("No se encontró el archivo de audio descargado.")
        return str(files[0]), info

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start."""
    user = update.effective_user
    welcome_text = (
        f"👋 ¡Hola, *{user.first_name}*!\n\n"
        "🎵 Envíame un enlace de *YouTube* o *YouTube Shorts* y te permitiré descargar la música en formato *MP3* o *M4A*.\n\n"
        "💡 *Ejemplo:* `https://youtu.be/dQw4w9WgXcQ`"
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detecta enlaces de YouTube en los mensajes de texto."""
    text = update.message.text or ""
    match = YT_REGEX.search(text)
    
    if not match:
        await update.message.reply_text(
            "⚠️ Por favor envía un enlace válido de YouTube (ej. https://youtu.be/...)."
        )
        return

    url = match.group(1)
    status_msg = await update.message.reply_text("🔍 Obteniendo información del video...")

    try:
        # Extraer información en un hilo secundario
        info = await asyncio.to_thread(extract_youtube_info, url)
        
        title = info.get("title", "Audio")
        uploader = info.get("uploader", "Desconocido")
        duration = info.get("duration", 0)
        formatted_duration = format_duration(duration)
        video_id = info.get("id")
        # YouTube siempre entrega JPEG valido en esta direccion (evita el error WebP de Telegram)
        thumbnail = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

        caption = (
            f"🎶 {title}\n\n"
            f"👤 Canal: {uploader}\n"
            f"⏱ Duración: {formatted_duration}\n\n"
            "Elige el formato de descarga:"
        )

        keyboard = [
            [
                InlineKeyboardButton("🎵 MP3 (192 kbps)", callback_data=f"dl:mp3:{video_id}"),
                InlineKeyboardButton("🎧 M4A (Original)", callback_data=f"dl:m4a:{video_id}"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Intentar enviar la foto con la botonera; si Telegram rechaza el formato de la imagen, usar texto
        photo_sent = False
        if thumbnail:
            try:
                await update.message.reply_photo(
                    photo=thumbnail,
                    caption=caption,
                    reply_markup=reply_markup,
                )
                await status_msg.delete()
                photo_sent = True
            except Exception as pe:
                logger.warning(f"Telegram rechazó la URL de la miniatura ({pe}), enviando solo texto.")
                photo_sent = False

        if not photo_sent:
            await status_msg.edit_text(
                caption,
                reply_markup=reply_markup,
            )

    except Exception as e:
        logger.error(f"Error procesando enlace: {e}")
        await status_msg.edit_text(
            f"❌ No se pudo procesar el video: {str(e)}"
        )

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja los clics en los botones de descarga."""
    query = update.callback_query
    await query.answer()

    data = query.data.split(":")
    if len(data) != 3 or data[0] != "dl":
        return

    format_choice = data[1]
    video_id = data[2]
    url = f"https://www.youtube.com/watch?v={video_id}"

    # Directorio temporal exclusivo para esta descarga
    task_id = str(uuid.uuid4())
    task_dir = TEMP_DIR / task_id
    task_dir.mkdir(parents=True, exist_ok=True)

    status_text = f"⏳ Descargando y convirtiendo a {format_choice.upper()}... Por favor espera."
    try:
        if query.message.photo:
            await query.edit_message_caption(caption=status_text)
        else:
            await query.edit_message_text(text=status_text)
    except Exception as e:
        logger.warning(f"No se pudo editar el mensaje de estado: {e}")

    try:
        # Descarga en segundo plano
        file_path, info = await asyncio.to_thread(download_audio, url, format_choice, str(task_dir))
        
        # Verificar tamaño del archivo (Límite de bots de Telegram: 50MB)
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > 50:
            await query.message.reply_text(
                f"⚠️ El archivo pesa {file_size_mb:.1f} MB, lo cual excede el límite de 50 MB de Telegram."
            )
            return

        title = info.get("title", Path(file_path).stem)
        uploader = info.get("uploader", "YouTube")
        duration = info.get("duration")

        # Enviar el archivo de audio directamente al chat con tiempo de espera extendido
        with open(file_path, "rb") as audio_file:
            await context.bot.send_audio(
                chat_id=query.message.chat_id,
                audio=audio_file,
                title=title,
                performer=uploader,
                duration=duration,
                caption=f"✅ {title}\nFormato: {format_choice.upper()}",
                read_timeout=180,
                write_timeout=180,
            )

    except Exception as e:
        logger.error(f"Error en descarga: {e}", exc_info=True)
        error_msg = str(e)
        if "ffmpeg" in error_msg.lower():
            await query.message.reply_text(
                "❌ Error: Se requiere FFmpeg instalado en el sistema para la conversión de audio."
            )
        else:
            await query.message.reply_text(f"❌ Error al procesar el audio: {error_msg}")

    finally:
        # Limpieza de archivos temporales
        if task_dir.exists():
            shutil.rmtree(task_dir, ignore_errors=True)

def run_health_server():
    """Servidor web ultraligero para responder al healthcheck de Render y mantener el servicio 'Live'."""
    port = int(os.environ.get("PORT", 10000))
    class HealthHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Bot is alive and healthy!")

        def log_message(self, format, *args):
            pass  # Silenciar logs HTTP para no saturar la consola

    try:
        with socketserver.TCPServer(("", port), HealthHandler) as httpd:
            logger.info(f"Servidor de salud escuchando en el puerto {port}")
            httpd.serve_forever()
    except Exception as e:
        logger.error(f"Error en servidor de salud: {e}")

def main():
    if not TOKEN:
        print("❌ ERROR: No se encontró TELEGRAM_BOT_TOKEN en el archivo .env")
        print("Por favor crea un archivo .env y agrega: TELEGRAM_BOT_TOKEN=tu_token")
        return

    # Si estamos en Render u otro servicio en la nube con variable PORT, iniciamos el servidor web
    port = os.getenv("PORT")
    if port:
        threading.Thread(target=run_health_server, daemon=True).start()

    print("🤖 Iniciando Bot de Telegram...")
    # Configurar tiempos de espera amplios para permitir subir archivos de audio de varios megabytes
    request_config = HTTPXRequest(
        connect_timeout=60.0,
        read_timeout=180.0,
        write_timeout=180.0,
    )
    application = Application.builder().token(TOKEN).request(request_config).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_callback_query))

    print("✅ Bot en ejecución. Presiona Ctrl + C para detenerlo.")
    application.run_polling()

if __name__ == "__main__":
    main()
