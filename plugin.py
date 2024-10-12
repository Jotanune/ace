import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmcvfs
import sys
import os
from urllib.parse import parse_qsl, urlencode
from datetime import datetime, timedelta

# Agrega la ruta a las librerías externas
addon_path = xbmcaddon.Addon().getAddonInfo('path')
sys.path.append(os.path.join(addon_path, 'lib'))

# Importar requests desde la carpeta lib
import requests

# Importar BeautifulSoup desde la carpeta lib/bs4
from bs4 import BeautifulSoup

# Obtener la instancia del addon y sus configuraciones
addon = xbmcaddon.Addon()
addon_name = addon.getAddonInfo('name')
addon_data_dir = xbmc.translatePath(addon.getAddonInfo('profile'))
cache_file = os.path.join(addon_data_dir, 'cache.txt')

# URL base configurable desde las opciones del addon
BASE_URL = addon.getSetting('base_url') or 'https://www.robertofreijo.com/acestream-ids/'


# Duración de la caché (en minutos)
CACHE_DURATION = 30

def log(message, level=xbmc.LOGNOTICE):
    """
    Registra un mensaje en los logs de Kodi.
    """
    xbmc.log(f"[{addon_name}] {message}", level)

def get_acestream_links(url):
    """
    Obtiene todos los enlaces AceStream desde una página web dada.
    Implementa una caché para no hacer múltiples peticiones innecesarias.
    """
    # Intentar cargar los enlaces desde el caché
    links, cache_valid = load_cache()
    if cache_valid:
        log("Cargando enlaces AceStream desde la caché")
        return links

    log(f"Solicitando enlaces AceStream desde {url}")
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Verifica si la respuesta fue exitosa
    except requests.RequestException as e:
        log(f"Error al solicitar enlaces: {e}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Error', f"Error de red: {str(e)}", xbmcgui.NOTIFICATION_ERROR)
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    links = []
    for link in soup.find_all('a'):
        href = link.get('href')
        if href and 'acestream://' in href:
            links.append(href)

    if links:
        # Guardar los enlaces en la caché
        save_cache(links)

    return links

def list_acestream_links():
    """
    Muestra una lista de enlaces AceStream obtenidos desde la web.
    """
    links = get_acestream_links(BASE_URL)

    # Si no hay enlaces, mostrar un mensaje de error
    if not links:
        xbmcgui.Dialog().notification('Error', 'No se encontraron enlaces de AceStream', xbmcgui.NOTIFICATION_ERROR)
        return

    # Crear una lista en la interfaz de Kodi
    for idx, link in enumerate(links):
        list_item = xbmcgui.ListItem(label=f"Enlace AceStream {idx + 1}")
        list_item.setInfo('video', {'title': f"Stream {idx + 1}"})

        # Crear una URL para reproducir el enlace seleccionado
        url = f"{sys.argv[0]}?{urlencode({'action': 'play', 'link': link})}"

        # Añadir la lista a la interfaz
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=list_item, isFolder=False)

    # Finalizar la creación de la lista
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

def play_acestream(link):
    """
    Reproduce un enlace AceStream en Kodi.
    """
    log(f"Reproduciendo enlace AceStream: {link}")
    item = xbmcgui.ListItem(path=link)
    xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, item)

def update_acestream_links():
    """
    Fuerza la actualización de los enlaces AceStream invalidando la caché.
    """
    log("Actualizando enlaces AceStream y limpiando caché")
    clear_cache()
    xbmc.executebuiltin('Container.Refresh')

def router(paramstring):
    """
    Enrutador para manejar diferentes acciones dentro del addon.
    """
    params = dict(parse_qsl(paramstring))

    if params:
        if params['action'] == 'play':
            # Reproducir el enlace AceStream
            play_acestream(params['link'])
        elif params['action'] == 'update':
            # Actualizar los enlaces AceStream
            update_acestream_links()
    else:
        # Mostrar la lista de enlaces AceStream
        list_acestream_links()

def save_cache(links):
    """
    Guarda los enlaces AceStream en un archivo de caché.
    """
    try:
        with open(cache_file, 'w') as f:
            f.write(f"{datetime.now().isoformat()}\n")
            f.write('\n'.join(links))
        log("Enlaces guardados en la caché")
    except Exception as e:
        log(f"Error al guardar la caché: {e}", xbmc.LOGERROR)

def load_cache():
    """
    Carga los enlaces AceStream desde el archivo de caché, si es válido.
    """
    if not os.path.exists(cache_file):
        return [], False

    try:
        with open(cache_file, 'r') as f:
            lines = f.readlines()
            timestamp = datetime.fromisoformat(lines[0].strip())
            if datetime.now() - timestamp < timedelta(minutes=CACHE_DURATION):
                links = [line.strip() for line in lines[1:]]
                return links, True
            else:
                log("La caché ha expirado")
    except Exception as e:
        log(f"Error al cargar la caché: {e}", xbmc.LOGERROR)

    return [], False

def clear_cache():
    """
    Limpia el archivo de caché.
    """
    try:
        if os.path.exists(cache_file):
            os.remove(cache_file)
            log("Caché eliminada")
    except Exception as e:
        log(f"Error al eliminar la caché: {e}", xbmc.LOGERROR)

if __name__ == '__main__':
    # Controlador principal del addon
    router(sys.argv[2][1:])
