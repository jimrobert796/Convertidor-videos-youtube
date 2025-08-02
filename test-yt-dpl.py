import yt_dlp
import ffmpeg
import requests
import os
import tempfile

# URL del video
url = "https://youtu.be/tboHVE1ORjY"

# Carpeta temporal
with tempfile.TemporaryDirectory() as tmpdir:
    webm_path = os.path.join(tmpdir, "audio.webm")
    mp3_path = os.path.join(tmpdir, "audio.mp3")
    thumbnail_path = os.path.join(tmpdir, "thumbnail.jpg")

    # Configuración de yt-dlp
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': webm_path,
        'quiet': True,
    }

    # Descargar audio
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    # Descargar el thumbnail
    if 'thumbnail' in info:
        response = requests.get(info['thumbnail'])
        with open(thumbnail_path, 'wb') as f:
            f.write(response.content)
    else:
        thumbnail_path = None

    final_name = f"{info['title']}.mp3"

    if thumbnail_path:
        # Usamos ffmpeg en modo comando directamente con ffmpeg-python
        stream = ffmpeg.input(webm_path)
        ffmpeg.output(
            stream,
            mp3_path,
            **{
                'b:a': '192k',
                'ar': '44100',
                'map': '0:a',
                'id3v2_version': '3',
                'metadata:s:v': 'title=Cover',
                'metadata:s:v': 'comment=Cover',
            },
            vn=None
        ).run(overwrite_output=True)

        # Añadir la portada al mp3 (segunda pasada, ya que ffmpeg-python no lo hace directamente bien)
        os.system(f'ffmpeg -i "{mp3_path}" -i "{thumbnail_path}" -map 0 -map 1 -c copy -id3v2_version 3 '
                  f'-metadata:s:v title="Album cover" -metadata:s:v comment="Cover (Front)" "{final_name}"')
        os.remove(mp3_path)  # Borramos el mp3 sin portada
    else:
        # Solo convertir a mp3 si no hay portada
        ffmpeg.input(webm_path).output(
            final_name, format='mp3', audio_bitrate='192k', ar='44100'
        ).run(overwrite_output=True)

    print(f"✅ Archivo MP3 guardado como: {final_name}")
