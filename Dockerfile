# Imagen base con Python
FROM python:3.12-slim

# Establecer directorio de trabajo
WORKDIR /app

# Copiar archivos del proyecto
COPY . .

# Instalar dependencias del sistema necesarias para ffmpeg y mutagen
RUN apt-get update && \
    apt-get install -y ffmpeg libjpeg-dev && \
    pip install --no-cache-dir -r requirements.txt

# Exponer el puerto que usará la app (Fly.io lo necesita)
EXPOSE 8080

# Comando para ejecutar tu app
CMD ["python", "app.py"]
