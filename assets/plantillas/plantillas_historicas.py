import os
import sys
import requests
import re
import chompjs
import time
import random
import json
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# --- DICCIONARIO DE COMPETICIONES ---
COMPETICIONES_MAP = {
    "1": ("COP", "Copa del Rey (España)"), "2": ("SUP", "Supercopa (España)"),
    "3": ("ISC", "Supercopa (Italia)"), "4": ("FSC", "Supercopa (Francia)"),
    "5": ("DSC", "Supercopa (Alemania)"), "7": ("PSC", "Supercopa (Portugal)"),
    "8": ("HSC", "Johan Cruijff Schaal (Holanda)"), "9": ("TSC", "Süper Kupası (Turquia)"),
    "10": ("BSC", "Pro League Supercup (Belgica)"), "11": ("RSC", "Superkubok (Rusia)"),
    "12": ("SP1", "Premiership Relegation (Escocia)"), "13": ("SCF", "Premiership Championship (Escocia)"),
    "14": ("CHA", "Liga de Campeones"), "15": ("UEF", "Europa League"),
    "16": ("CNF", "Copa de Conferencia"), "17": ("SCE", "Supercopa de Europa"),
    "18": ("REC", "Recopa"), "19": ("MIT", "Copa Mitropa"),
    "20": ("FER", "Copa de Ferias"), "21": ("MUN", "Mundial de Clubes"),
    "22": ("FIF", "FIFA Club World"), "23": ("INT", "Copa Intercontinental")
}

BASE_DATOS_EQUIPOS = {
    "España": {
        "Barcelona": "1",
        "Real Madrid": "2",
        "Real Sociedad": "30",
        "Athletic": "6",
        "Atlético de Madrid": "7",
        "Espanyol": "14",
        "Sevilla": "33",
        "Real Betis": "8",
        "Valencia": "36",
        "Celta": "11",
        "Zaragoza" : "39",
        "Deportivo de la Coruna": "13",
        "Osasuna" : "27",
        "Valladolid" : "37",
        "Villarreal" : "38",
        "Racing de Santander" : "29",
        "Mallorca" : "24",
        "Sporting de Gijon" : "34",
        "Oviedo" : "28",
        "Getafe" : "16",
        "Las Palmas" : "19",
        "Rayo Vallecano" : "5",
        "Granada" : "59",
        "Malaga" : "23",
        "Alaves" : "3",
        "Elche" : "42",
        "Levante" : "20",
        "Hercules" : "18",
        "Tenerife" : "35",
        "Cadiz" : "10",
        "Murcia" : "40",
        "Salamanca" : "32",
        "Sabadell" : "44",
        "Eibar" : "47",
        "Almeria" : "43",
        "Girona" : "78"
    },
    "Inglaterra": {
        "Manchester City": "2007",
        "Liverpool": "2009",
        "Arsenal": "2001",
        "Manchester United": "2008"
    },
    "Italia": {
        "Juventus": "3004",
        "Inter de Milán": "3008",
        "AC Milan": "3013"
    }
}


def generar_string_temporada(año_inicio):
    """Convierte un año como 2020 en el formato '2020-21' requerido por BDFutbol."""
    año_fin = (año_inicio + 1) % 100
    return f"{año_inicio}-{año_fin:02d}"


def obtener_nombre_jugador(id_num, soup):
    enlace = soup.find('a', href=lambda h: h and f"j{id_num}.html" in h)
    if enlace:
        return list(enlace.stripped_strings)[0].replace("⬤", "").replace("●", "").strip()
    return f"Jugador {id_num}"


def obtener_posicion_jugador(id_num, soup):
    """Busca al jugador en el HTML para identificar su posición real mediante las clases del div 'fit'."""
    enlace = soup.find('a', href=lambda h: h and f"j{id_num}.html" in h)
    if not enlace:
        return "?"

    fila = enlace.find_parent("tr")
    if not fila:
        return "?"

    div_pos = fila.find("div", class_="fit")
    if not div_pos:
        return "?"

    clases = div_pos.get("class", [])
    for c in clases:
        c = c.lower()
        if c in ["por", "portero"]: return "portero"
        if c in ["def", "df"]: return "defensa"
        if c in ["cen", "cen"]: return "central"
        if c in ["ltd", "ltd"]: return "lateral derecho"
        if c in ["lti", "lti"]: return "lateral izquierdo"
        if c in ["mig", "cc"]: return "centrocampista"
        if c in ["dav", "dlv"]: return "extremo"
        if c in ["dac", "dlc"]: return "delantero centro"

    return "?"


def extraer_estadistica(bloque_stat, sigla_torneo, total_jugadores):
    """Extrae los datos evitando mezclar bloques sin 'tip' (Liga) con las Copas."""
    for item in bloque_stat:
        if sigla_torneo == "LIGA":
            if "tip" not in item or item.get("tip") == "LIGA":
                return item.get("data", [0] * total_jugadores)
        elif item.get("tip") == sigla_torneo:
            return item.get("data", [0] * total_jugadores)
    return [0] * total_jugadores


def procesar_bloque_competicion(nombre_torneo, ids_jugadores, lista_pj, lista_pt, lista_min, lista_goles, lista_genc,
                                soup):
    """Genera y retorna la lista de jugadores estructurada con sus estadísticas para una competición dada."""
    jugadores_datos = []

    for idx, id_num in enumerate(ids_jugadores):
        pj = lista_pj[idx] if idx < len(lista_pj) else 0
        pt = lista_pt[idx] if idx < len(lista_pt) else 0
        minutos = lista_min[idx] if idx < len(lista_min) else 0
        goles = lista_goles[idx] if idx < len(lista_goles) else 0
        genc = lista_genc[idx] if idx < len(lista_genc) else 0

        if minutos > 0 or pj > 0:
            nombre = obtener_nombre_jugador(id_num, soup)
            posicion = obtener_posicion_jugador(id_num, soup)

            jugadores_datos.append({
                "id": f"j{id_num}",
                "nombre": nombre,
                "posicion": posicion,
                "partidos_jugados": pj,
                "partidos_titular": pt,
                "minutos": minutos,
                "goles_marcados": goles,
                "goles_encajados": genc
            })

    return jugadores_datos


def raspar_temporada(pais, equipo, id_equipo, año_inicio):
    temp_str = generar_string_temporada(año_inicio)
    url = f"https://www.bdfutbol.com/es/t/t{temp_str}{id_equipo}.html"
    print(f"\n🌐 Descargando datos desde: {url}")

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            print(f"❌ Error al acceder a la temporada {temp_str} (Status: {response.status_code}).")
            return False

        html = response.text
        soup = BeautifulSoup(html, 'html.parser')

        match_json = re.search(r'json_data\s*=\s*JSON\.parse\(\'(.*?)\'\);', html)
        if not match_json:
            print(f"⚠️ No se encontró el bloque 'json_data' para la temporada {temp_str}.")
            return False

        datos_js = chompjs.parse_js_object(match_json.group(1))
        ids_jugadores = datos_js.get("COD", [{}])[0].get("data", [])
        total_jugadores = len(ids_jugadores)

        if total_jugadores == 0:
            print(f"⚠️ No hay jugadores registrados en esta temporada.")
            return False

        # Estructura principal del JSON de salida
        datos_json_final = {
            "pais": pais,
            "equipo": equipo,
            "id_bdfutbol": id_equipo,
            "temporada": temp_str,
            "año_inicio": año_inicio,
            "competiciones": {}
        }

        bloque_pj = datos_js.get("PJ", [])
        bloque_pt = datos_js.get("PT", [])
        bloque_min = datos_js.get("M", [])
        bloque_goles = datos_js.get("G", [])
        bloque_genc = datos_js.get("GENC", [])

        # Detectar copas extras disputadas por el club
        siglas_detectadas = set()
        for item in bloque_pj:
            if "tip" in item:
                siglas_detectadas.add(item["tip"])

        # Extraer Liga Regular
        liga_pj = extraer_estadistica(bloque_pj, "LIGA", total_jugadores)
        liga_pt = extraer_estadistica(bloque_pt, "LIGA", total_jugadores)
        liga_min = extraer_estadistica(bloque_min, "LIGA", total_jugadores)
        liga_goles = extraer_estadistica(bloque_goles, "LIGA", total_jugadores)
        liga_genc = extraer_estadistica(bloque_genc, "LIGA", total_jugadores)

        datos_liga = procesar_bloque_competicion("Liga Regular", ids_jugadores, liga_pj, liga_pt, liga_min, liga_goles,
                                                 liga_genc, soup)
        if datos_liga:
            datos_json_final["competiciones"]["Liga Regular"] = datos_liga

        # Extraer las copas dinámicas detectadas
        mapeo_siglas = {v[0]: v[1] for v in COMPETICIONES_MAP.values()}
        for sigla in siglas_detectadas:
            nombre_torneo = mapeo_siglas.get(sigla, f"Torneo ({sigla})")
            comp_pj = extraer_estadistica(bloque_pj, sigla, total_jugadores)
            comp_pt = extraer_estadistica(bloque_pt, sigla, total_jugadores)
            comp_min = extraer_estadistica(bloque_min, sigla, total_jugadores)
            comp_goles = extraer_estadistica(bloque_goles, sigla, total_jugadores)
            comp_genc = extraer_estadistica(bloque_genc, sigla, total_jugadores)

            datos_copa = procesar_bloque_competicion(nombre_torneo, ids_jugadores, comp_pj, comp_pt, comp_min,
                                                     comp_goles, comp_genc, soup)
            if datos_copa:
                datos_json_final["competiciones"][nombre_torneo] = datos_copa

        # --- GUARDADO EN ARCHIVO JSON ---
        # Aseguramos máxima portabilidad utilizando os.getcwd()
        directorio_ejecucion = os.getcwd()
        # Normalizamos nombres de carpetas eliminando tildes y espacios problemáticos (opcional, aquí directo)
        ruta_carpeta = os.path.join(directorio_ejecucion, pais, equipo)
        os.makedirs(ruta_carpeta, exist_ok=True)

        ruta_archivo_json = os.path.join(ruta_carpeta, f"{año_inicio}.json")

        with open(ruta_archivo_json, "w", encoding="utf-8") as archivo:
            json.dump(datos_json_final, archivo, ensure_ascii=False, indent=4)

        print(f"✅ Archivo JSON exportado con éxito en: {ruta_archivo_json}")
        return True

    except Exception as e:
        print(f"❌ Error inesperado procesando la temporada {temp_str}: {e}")
        return False


def main():
    print("=== ASISTENTE DE EXTRACCIÓN HISTÓRICA BDFUTBOL A JSON ===\n")

    paises = list(BASE_DATOS_EQUIPOS.keys())
    for i, pais in enumerate(paises):
        print(f"[{i + 1}] {pais}")
    idx_pais = int(input("\nSelecciona el número de país: ")) - 1
    pais_seleccionado = paises[idx_pais]

    equipos = list(BASE_DATOS_EQUIPOS[pais_seleccionado].keys())
    print(f"\nEquipos disponibles en {pais_seleccionado}:")
    for i, equipo in enumerate(equipos):
        print(f"[{i + 1}] {equipo}")
    idx_equipo = int(input("\nSelecciona el número de equipo: ")) - 1
    equipo_seleccionado = equipos[idx_equipo]
    id_equipo = BASE_DATOS_EQUIPOS[pais_seleccionado][equipo_seleccionado]

    print("\n--- Definir rango cronológico (Ejemplo: desde 2018 hasta 2021) ---")
    año_inicio = int(input("Año de inicio (formato AAAA, ej. 2018): "))
    año_fin = int(input("Año de fin (formato AAAA, ej. 2021): "))

    print(
        f"\n🚀 Iniciando extracción para el {equipo_seleccionado} desde la temporada {generar_string_temporada(año_inicio)} hasta {generar_string_temporada(año_fin)}...")

    lista_años = list(range(año_inicio, año_fin + 1))

    for indice, año in enumerate(lista_años):
        raspar_temporada(pais_seleccionado, equipo_seleccionado, id_equipo, año)

        if indice < len(lista_años) - 1:
            tiempo_espera = random.randint(3, 10)
            print(f"\n⏳ Esperando {tiempo_espera} segundos antes de solicitar la siguiente temporada...")
            time.sleep(tiempo_espera)

    print("\n🏁 ¡Proceso completado con éxito!")


if __name__ == "__main__":
    main()