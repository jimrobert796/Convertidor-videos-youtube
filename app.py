# Importación de librerías necesarias
from flask import Flask, render_template, request, jsonify, send_file  # Flask y funciones útiles

# Youtube
from pytubefix import YouTube  # Objeto principal para trabajar con videos de YouTube
from pytubefix.cli import on_progress  # Función para mostrar progreso de descarga
from pytubefix.exceptions import PytubeFixError, VideoUnavailable  # Manejo de errores específicos

# Archivos y audios
import ffmpeg  # Para manejar ffmpeg desde Python
import tempfile, os, subprocess, requests  # Utilidades para manejar archivos, procesos y peticiones web
from mutagen.mp3 import MP3  # Para manipular archivos MP3
from mutagen.id3 import ID3, APIC, TIT2, TPE1  # Para editar etiquetas ID3 del MP3

from io import BytesIO  # Para enviar el archivo como flujo de bytes
from imghdr import what  # Para detectar tipo de imagen

# Crear la aplicación Flask
app = Flask(__name__)

# Ruta principal que muestra el formulario en HTML
@app.route("/")
def index():
    return render_template("index.html")

# Ruta que recibe la URL y devuelve información del video
@app.route("/info", methods=["POST"])
def get_info():
    data = request.get_json()
    url = data.get("url")
    if not url:
        return jsonify({"error": "No se proporcionó URL"}), 400
    try:
        yt = YouTube(url)
        info = {
            "title": yt.title,
            "author": yt.author,
            "thumbnail_url": yt.thumbnail_url,
            "length": yt.length,
        }
        return jsonify(info)
    except VideoUnavailable:
        return jsonify({"error": "Este video no está disponible."}), 403
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Ruta que descarga el audio del video y lo convierte en MP3 con portada
@app.route("/download", methods=["POST"])
def download_audio():
    url = request.form.get("url")
    if not url:
        return "Error: No URL provided", 400
    try:
        yt = YouTube(url, on_progress_callback=on_progress)

        audio_stream = yt.streams.filter(only_audio=True).order_by("abr").desc().first()
        if not audio_stream:
            return "No audio stream found", 400

        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = os.path.join(tmpdir, "audio.webm")
            mp3_path = os.path.join(tmpdir, "audio.mp3")

            audio_stream.download(output_path=tmpdir, filename="audio.webm")

            ffmpeg.input(audio_path).output(
                mp3_path, format='mp3', audio_bitrate='192k', ar='44100'
            ).run(overwrite_output=True)

            thumb_resp = requests.get(yt.thumbnail_url)
            image_data = thumb_resp.content

            mime_type = 'image/jpeg'
            img_type = what(None, h=image_data)
            if img_type == 'png':
                mime_type = 'image/png'

            audio = MP3(mp3_path, ID3=ID3)
            if audio.tags is None:
                audio.add_tags()

            audio.tags.add(APIC(encoding=3, mime=mime_type, type=3, desc='Cover', data=image_data))
            audio.tags.add(TIT2(encoding=3, text=yt.title))
            audio.tags.add(TPE1(encoding=3, text=yt.author))
            audio.save(v2_version=3)

            with open(mp3_path, "rb") as f:
                return send_file(
                    BytesIO(f.read()),
                    as_attachment=True,
                    download_name=f"{yt.title}.mp3",
                    mimetype="audio/mp3"
                )

    except VideoUnavailable:
        return "Error: Este video no está disponible o está restringido.", 403
    except Exception as e:
        return f"Error: {str(e)}", 500

# Ejecutar la aplicación
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
