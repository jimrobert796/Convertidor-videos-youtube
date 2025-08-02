# Importación de librerías necesarias
from flask import Flask, render_template, request, jsonify, send_file  # Flask y funciones útiles

# Youtube
from pytubefix import YouTube  # Objeto principal para trabajar con videos de YouTube
from pytubefix.cli import on_progress  # Función para mostrar progreso de descarga
from pytubefix.exceptions import PytubeFixError  # Manejo de errores específicos

# Archivos y audios
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
    return render_template("index.html")  # Muestra index.html


# Ruta que recibe la URL y devuelve información del video
@app.route("/info", methods=["POST"])
def get_info():
    data = request.get_json()  # Obtiene el JSON enviado desde el cliente
    url = data.get("url")  # Extrae la URL del json
    if not url:
        return jsonify({"error": "No se proporcionó URL"}), 400  # Devuelve error si no hay URL
    try:
        yt = YouTube(url)  #Sino crea objeto YouTube
        info = {
            "title": yt.title,  # Título del video
            "author": yt.author,  # Autor del video
            "thumbnail_url": yt.thumbnail_url,  # URL de miniatura
            "length": yt.length,  # Duración en segundos
        }
        return jsonify(info)  # Envía datos como respuesta JSON
    except Exception as e:
        return jsonify({"error": str(e)}), 500  # Devuelve error si falla algo


# Ruta que descarga el audio del video y lo convierte en MP3 con portada
@app.route("/download", methods=["POST"])
def download_audio():
    url = request.form.get("url")  # Obtiene la URL de youtube con el identificador de html "url"
    if not url:
        return "Error: No URL provided", 400  # Verifica que haya URL
    try:
        # Crea el objeto YouTube
        yt = YouTube(url, on_progress_callback=on_progress)

        # Obtiene la mejor calidad de solo audio
        audio_stream = yt.streams.filter(only_audio=True).order_by("abr").desc().first()
        if not audio_stream:
            return "No audio stream found", 400  # Si no hay audio, muestra error

        # Crea una carpeta temporal invisible para descargar y trabajar con los archivos
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = os.path.join(tmpdir, "audio.webm")  # Ruta para archivo original
            mp3_path = os.path.join(tmpdir, "audio.mp3")     # Ruta para archivo convertido

            # Descarga el audio en formato webm s
            audio_stream.download(output_path=tmpdir, filename="audio.webm")

            # Usa ffmpeg para convertir el audio a mp3
            subprocess.run([
                "ffmpeg", "-i", audio_path, "-vn", "-ab", "192k", "-ar", "44100", "-y", mp3_path
            ], check=True)

            # Descarga la miniatura del video
            thumb_resp = requests.get(yt.thumbnail_url)
            image_data = thumb_resp.content

            # Detectar si la imagen es jpeg o png para definir mime-type correcto
            mime_type = 'image/jpeg'  # Por defecto jpg
            img_type = what(None, h=image_data)  # Detecta tipo de imagen
            if img_type == 'png':
                mime_type = 'image/png'  # Cambia a png si corresponde

            # Abrir el archivo mp3 con mutagen para editar sus etiquetas ID3
            audio = MP3(mp3_path, ID3=ID3)
            if audio.tags is None:
                audio.add_tags()  # Si no tiene etiquetas, las agrega
                
            # Agregar la portada con etiqueta APIC (imagen incrustada)
            audio.tags.add(APIC(
                encoding=3,        # UTF-8
                mime=mime_type,    # tipo de imagen (jpeg/png)
                type=3,            # tipo portada frontal (cover front)
                desc='Cover',      # descripción
                data=image_data    # datos binarios de la imagen
            ))

            # Agregar título y artista (autor) del video como etiquetas ID3
            audio.tags.add(TIT2(encoding=3, text=yt.title))  # Título
            audio.tags.add(TPE1(encoding=3, text=yt.author)) # Artista
            audio.save(v2_version=3)

            # Abre el archivo y lo devuelve como descarga
            with open(mp3_path, "rb") as f:
                return send_file(
                    BytesIO(f.read()),  # Envía el archivo como flujo de bytes
                    as_attachment=True,  # Indica que es un archivo para descargar
                    download_name=f"{yt.title}.mp3",  # Nombre del archivo descargado
                    mimetype="audio/mp3"  # Tipo MIME
                )
    except Exception as e:
        return f"Error: {str(e)}", 500  # Devuelve cualquier error que ocurra

# Ejecutar la aplicación en modo debug
if __name__ == "__main__":
    app.run(debug=True)  # Ejecuta Flask con depuración activada
