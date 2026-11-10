FROM python:3.11-slim

# Instalar FFmpeg y Node.js (requerido por yt-dlp para descifrar las URLs de audio de YouTube)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg nodejs && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar e instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código del proyecto
COPY . .

# Comando de inicio del bot
CMD ["python", "bot.py"]
