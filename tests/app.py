from flask import Flask, render_template, request, send_file, jsonify
from yt_dlp import YoutubeDL
import ffmpeg
import tempfile
import io
import os


app = Flask(__name__, template_folder='templates')


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/download", methods=["POST"])
def download():
    url = request.form.get("url")

    if not url:
        return jsonify({"error": "URL no proporcionada"}), 400

    try:
        # Carpeta temporal en memoria
        with tempfile.TemporaryDirectory() as tmpdir:
            # Descarga del audio en formato bestaudio
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(tmpdir, 'audio.%(ext)s'),
                'noplaylist': True,
                'quiet': True
            }

            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                input_audio_path = ydl.prepare_filename(info)

            # Convertir a MP3 usando ffmpeg-python
            output_io = io.BytesIO()
            stream = ffmpeg.input(input_audio_path)
            stream = ffmpeg.output(stream, 'pipe:', format='mp3', audio_bitrate='192k')
            out, _ = ffmpeg.run(stream, capture_stdout=True, capture_stderr=True)
            output_io.write(out)
            output_io.seek(0)

            # Nombre del archivo
            filename = f"{info.get('title', 'audio')}.mp3"

            return send_file(
                output_io,
                mimetype="audio/mpeg",
                as_attachment=True,
                download_name=filename
            )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
