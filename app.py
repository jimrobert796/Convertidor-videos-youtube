# Importación de librerías necesarias
from flask import Flask, render_template, request, jsonify, send_file  # Flask y funciones útiles

# Youtube con yt-dlp
import yt_dlp

# Archivos y audios
import ffmpeg  # Para manejar ffmpeg desde Python
import tempfile, os, requests  # Utilidades para manejar archivos, procesos y peticiones web
from mutagen.mp3 import MP3  # Para manipular archivos MP3
from mutagen.id3 import ID3, APIC, TIT2, TPE1  # Para editar etiquetas ID3 del MP3

from io import BytesIO  # Para enviar el archivo como flujo de bytes
from imghdr import what  # Para detectar tipo de imagen

# Crear la aplicación Flask
app = Flask(__name__)

# Ruta principal que muestra el formulario en HTML
@app.route("/")
def index():
    return render_template("index.html")  # Muestra index.html


# Ruta que recibe la URL y devuelve información del video
@app.route("/info", methods=["POST"])
def get_info():
    data = request.get_json()
    url = data.get("url")
    if not url:
        return jsonify({"error": "No se proporcionó URL"}), 400
    try:
        # Usamos yt-dlp para obtener info del video
        ydl_opts = {'quiet': True, 'skip_download': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        info_data = {
            "title": info.get('title'),
            "author": info.get('uploader'),
            "thumbnail_url": info.get('thumbnail'),
            "length": info.get('duration'),
        }
        return jsonify(info_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Ruta que descarga el audio del video y lo convierte en MP3 con portada
@app.route("/download", methods=["POST"])
def download_audio():
    url = request.form.get("url")
    if not url:
        return "Error: No URL provided", 400
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            mp3_path = os.path.join(tmpdir, "audio.mp3")
            audio_path = os.path.join(tmpdir, "audio.webm")

            # Opciones para yt-dlp: descarga solo audio en mejor calidad y guarda en audio.webm
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': audio_path,
                'quiet': True,
                'no_warnings': True,
                'postprocessors': [],
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url)

            # Convertir audio descargado a mp3 usando ffmpeg-python
            (
                ffmpeg
                .input(audio_path)
                .output(mp3_path, format='mp3', audio_bitrate='192k', ar='44100')
                .run(overwrite_output=True)
            )

            # Descarga la miniatura
            thumb_url = info.get('thumbnail')
            thumb_resp = requests.get(thumb_url)
            image_data = thumb_resp.content

            mime_type = 'image/jpeg'
            img_type = what(None, h=image_data)
            if img_type == 'png':
                mime_type = 'image/png'

            # Editar etiquetas ID3 con mutagen
            audio = MP3(mp3_path, ID3=ID3)
            if audio.tags is None:
                audio.add_tags()

            audio.tags.add(APIC(
                encoding=3,
                mime=mime_type,
                type=3,
                desc='Cover',
                data=image_data
            ))

            audio.tags.add(TIT2(encoding=3, text=info.get('title')))
            audio.tags.add(TPE1(encoding=3, text=info.get('uploader')))
            audio.save(v2_version=3)

            with open(mp3_path, "rb") as f:
                return send_file(
                    BytesIO(f.read()),
                    as_attachment=True,
                    download_name=f"{info.get('title')}.mp3",
                    mimetype="audio/mp3"
                )

    except Exception as e:
        return f"Error: {str(e)}", 500


# Ejecutar la aplicación en modo debug
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
