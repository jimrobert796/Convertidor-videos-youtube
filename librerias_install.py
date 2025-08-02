import subprocess
import sys

# Lista de paquetes de PyPI que necesitas instalar
required_packages = [
    "Flask",
    "pytubefix",
    "mutagen",
    "requests",
    "jinja2"
]

# Recorremos la lista e instalamos si falta


def install_if_missing(pkg):
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "show", pkg])
    except subprocess.CalledProcessError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])


for package in required_packages:
    install_if_missing(package)
