# Importación de librerías necesarias
# Flask y funciones útiles
from flask import Flask, render_template, request, jsonify, send_file

# Youtube
from pytubefix import YouTube  # Objeto principal para trabajar con videos de YouTube
# Función para mostrar progreso de descarga
from pytubefix.cli import on_progress

# Archivos y audios
import ffmpeg  # Para manejar ffmpeg desde Python
import tempfile
import os
import requests  # Utilidades para manejar archivos, procesos y peticiones web
from mutagen.mp3 import MP3  # Para manipular archivos MP3
# Para editar etiquetas ID3 del MP3
from mutagen.id3 import ID3, APIC, TIT2, TPE1
from io import BytesIO  # Para enviar el archivo como flujo de bytes

# Crear la aplicación Flask
app = Flask(__name__)


def url_image(url_id):
    maxres_thumb_url = f"https://i.ytimg.com/vi/{url_id}/maxresdefault.jpg"
    response = requests.get(maxres_thumb_url)

    if response.status_code == 200:
        print("Miniatura maxresdefault encontrada")
    else:
        print("No hay miniatura maxresdefault, intentara con hqdefault.")
        maxres_thumb_url = f"https://i.ytimg.com/vi/sddefault/maxresdefault.jpg"
        return maxres_thumb_url

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
        # Devuelve error si no hay URL
        return jsonify({"error": "No se proporcionó URL"}), 400
    try:
        yt = YouTube(url)  # Sino crea objeto YouTube
        info = {
            "title": yt.title,  # Título del video
            "author": yt.author,  # Autor del video
            "thumbnail_url": yt.thumbnail_url,  # URL de miniatura
            "length": yt.length,  # Duración en segundos
        }
        return jsonify(info)  # Envía datos como respuesta JSON
    except Exception as e:
        return jsonify({"error": str(e)}), 500  # Devuelve error si falla algo


@app.route('/download_mp4', methods=['POST'])
def download_mp4():
    try:
        # Obtener la URL enviada por formulario
        url = request.form.get("url")
        if not url:
            # Si no hay URL, responder con error 400
            return jsonify({"error": "No se proporcionó URL"}), 400

        # Crear objeto YouTube con la URL dada
        yt = YouTube(url)

        # Filtrar streams para obtener los progresivos (video + audio juntos)
        # que sean mp4 y tomar el de mayor resolución
        stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by(
            'resolution').desc().first()

        if not stream:
            # Si no encontró ningún stream progresivo mp4, error 404
            return jsonify({"error": "No se encontró stream progresivo mp4"}), 404

        # Crear carpeta temporal para descargar el archivo
        with tempfile.TemporaryDirectory() as tmp:
            # Descargar el video en la carpeta temporal con nombre fijo
            filepath = stream.download(output_path=tmp, filename="video.mp4")

            # Abrir el archivo descargado en modo binario
            with open(filepath, "rb") as f:
                # Leer todo el contenido en memoria
                data = f.read()

            # Enviar el archivo leído en memoria al cliente
            return send_file(
                # Se envía el archivo desde memoria
                BytesIO(data),
                as_attachment=True,          # Para que se descargue como archivo
                # Nombre del archivo que verá el usuario
                download_name=f"{yt.title}.mp4",
                mimetype="video/mp4"         # Tipo MIME para MP4
            )

    except Exception as e:
        # En caso de cualquier error devolverlo en JSON con código 500
        return jsonify({"error": str(e)}), 500


# Ruta que descarga el audio del video y lo convierte en MP3 con portada
@app.route("/download_mp3", methods=["POST"])
def download_mp3():
    # Obtiene la URL de youtube con el identificador de html "url"
    url = request.form.get("url")
    if not url:
        return "Error: No URL provided", 400  # Verifica que haya URL
    try:
        # Crea el objeto YouTube
        yt = YouTube(url, on_progress_callback=on_progress)

        # Obtiene la mejor calidad de solo audio
        audio_stream = yt.streams.filter(
            only_audio=True).order_by("abr").desc().first()
        if not audio_stream:
            return "No audio stream found", 400  # Si no hay audio, muestra error

        # Crea una carpeta temporal invisible para descargar y trabajar con los archivos
        with tempfile.TemporaryDirectory() as tmpdir:
            # Ruta para archivo original
            audio_path = os.path.join(tmpdir, "audio.webm")
            # Ruta para archivo convertido
            mp3_path = os.path.join(tmpdir, "audio.mp3")

            # Descarga el audio en formato webm s
            audio_stream.download(output_path=tmpdir, filename="audio.webm")

            # Convertir audio a mp3 usando ffmpeg-python
            (
                ffmpeg
                .input(audio_path)
                .output(mp3_path, format='mp3', audio_bitrate='192k', ar='44100')
                .run(overwrite_output=True)
            )

            # Descarga la miniatura del video en su mejor calidad posible(Manualmente construyendo su link en ese caso)
            """
                YouTube guarda varias versiones de miniatura:
                    default.jpg (120x90)
                    mqdefault.jpg (320x180)
                    hqdefault.jpg (480x360)
                    sddefault.jpg (640x480)
                    maxresdefault.jpg (1280x720) ← la más grande
            """

            maxres_thumb_url = f"https://i.ytimg.com/vi/{yt.video_id}/maxresdefault.jpg"
            response = requests.get(maxres_thumb_url)

            if response.status_code == 200:
                print("Miniatura maxresdefault encontrada")
            else:
                print("No hay miniatura maxresdefault, intentara con hqdefault.")
                maxres_thumb_url = yt.thumbnail_url

            # Recuest para obtener la miniatura
            thumb_resp = requests.get(maxres_thumb_url)
            print(maxres_thumb_url)
            image_data = thumb_resp.content

            # Detectar si la imagen es jpeg o png para definir mime-type correcto
            mime_type = 'image/jpeg'  # Por defecto jpg
            # Cambia a png si corresponde

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
            audio.tags.add(TPE1(encoding=3, text=yt.author))  # Artista
            audio.save(v2_version=3)

            # Abre el archivo y lo devuelve como descarga
            with open(mp3_path, "rb") as f:
                return send_file(
                    BytesIO(f.read()),  # Envía el archivo como flujo de bytes
                    as_attachment=True,  # Indica que es un archivo para descargar
                    # Nombre del archivo descargado
                    download_name=f"{yt.title}.mp3",
                    mimetype="audio/mp3"  # Tipo MIME
                )
    except Exception as e:
        return f"Error: {str(e)}", 500  # Devuelve cualquier error que ocurra


# Ejecutar la aplicación en modo debug
if __name__ == "__main__":
    app.run()   
