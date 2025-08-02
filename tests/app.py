from flask import Flask, render_template, request, send_file, redirect, url_for
import yt_dlp
import tempfile
import os
import io
import ffmpeg

app = Flask(__name__, template_folder='templates')

@app.route('/')
def index():
    error = request.args.get("error")
    return render_template('index.html', error=error)

@app.route('/download', methods=['POST'])
def download():
    url = request.form.get('url')

    if not url:
        return redirect(url_for('index', error="No se proporcionó una URL"))

    try:
        # Crear archivo temporal para el audio original (webm/m4a)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp_file:
            original_audio_path = tmp_file.name

        # Descargar el audio sin procesar
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': original_audio_path,
            'quiet': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'audio') + '.mp3'

        # Convertir a mp3 usando ffmpeg-python, en memoria
        mp3_data = io.BytesIO()

        stream = ffmpeg.input(original_audio_path)
        stream = ffmpeg.output(stream, 'pipe:1', format='mp3', acodec='libmp3lame', audio_bitrate='192k')
        out, err = ffmpeg.run(stream, capture_stdout=True, capture_stderr=True)
        mp3_data.write(out)
        mp3_data.seek(0)

        # Borrar archivo temporal original
        os.remove(original_audio_path)

        return send_file(mp3_data, as_attachment=True, download_name=title, mimetype='audio/mpeg')

    except Exception as e:
        return redirect(url_for('index', error=str(e)))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
