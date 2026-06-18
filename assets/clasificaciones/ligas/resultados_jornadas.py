import os
import sys
import json
import requests
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'es-ES,es;q=0.9',
}

# Configuración de ligas: prefijo de URL y partidos que se juegan por jornada
CONFIG_LIGAS = {
    "1": {"nombre": "España", "prefijo": "", "partidos_jornada": 10},
    "2": {"nombre": "Inglaterra", "prefijo": "eng", "partidos_jornada": 10},
    "3": {"nombre": "Alemania", "prefijo": "ger", "partidos_jornada": 9},
    "4": {"nombre": "Italia", "prefijo": "ita", "partidos_jornada": 10},
    "5": {"nombre": "Francia", "prefijo": "fra", "partidos_jornada": 10},
    "6": {"nombre": "Portugal", "prefijo": "por", "partidos_jornada": 9},
    "7": {"nombre": "Holanda", "prefijo": "ned", "partidos_jornada": 9},
    "8": {"nombre": "Brasil", "prefijo": "bra", "partidos_jornada": 10},
    "9": {"nombre": "Argentina", "prefijo": "arg", "partidos_jornada": 14}
}


def seleccionar_opciones():
    print("🌍 --- SELECCIÓN DE LIGA PARA RESULTADOS MULTIPAÍS ---")
    for opcion, info in CONFIG_LIGAS.items():
        print(f"{opcion}. {info['nombre']}")

    pais = input("¿Qué país? Selecciona un número (1-9): ").strip()

    if pais not in CONFIG_LIGAS:
        print("❌ Selección no válida. Asumiendo España por defecto.")
        pais = "1"

    division = input("¿Qué división? (1 o 2): ").strip()
    anio = input("📅 Introduce el año de inicio de la temporada (ej. 2020): ").strip()

    return pais, division, anio


def generar_url_base(id_pais, division, anio):
    anio_int = int(anio)
    sig_anio_str = str(anio_int + 1)[-2:]

    info_pais = CONFIG_LIGAS[id_pais]
    prefijo_pais = info_pais["prefijo"]

    # Manejo de divisiones: En BDFutbol la segunda división añade una 'b' antes de la 't'
    prefijo_div = "" if division == "1" else "b"

    return f"https://www.bdfutbol.com/es/t/{prefijo_div}t{prefijo_pais}{anio_int}-{sig_anio_str}.html"


def formatear_marcador(texto_resultado):
    """Transforma marcadores compactos tipo '20' o '11' en '2 - 0' o '1 - 1'"""
    texto = texto_resultado.strip()
    if len(texto) == 2 and texto.isdigit():
        return f"{texto[0]} - {texto[1]}"
    return texto


def procesar_y_formatear(id_pais, division, anio, url_jornada, partidos_por_jornada):
    try:
        response = requests.get(url_jornada, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            print(
                f"❌ Error al acceder a la página (Status: {response.status_code}). Verifica si la combinación año/división existe.")
            return False

        soup = BeautifulSoup(response.text, 'html.parser')

        # Mantenemos la clase exacta que localizó nuestro escáner
        tabla_partidos = soup.find('table', class_='taula_estil-16')

        if not tabla_partidos:
            print("❌ No se encontró la tabla de partidos ('taula_estil-16') en esta URL.")
            return False

        filas = tabla_partidos.find_all('tr')

        # Estructura inicial del JSON maestro
        info_pais = CONFIG_LIGAS[id_pais]
        datos_temporada = {
            "pais": info_pais["nombre"],
            "division": f"División {division}",
            "año_inicio": int(anio),
            "jornadas": {}
        }

        partido_en_jornada = 0
        numero_jornada = 1

        # Clave inicial para agrupar en el JSON (ej: "Jornada 1")
        nombre_jornada_actual = f"Jornada {numero_jornada}"
        datos_temporada["jornadas"][nombre_jornada_actual] = []

        print(f"\n📌 =================== JORNADA {numero_jornada} ===================")

        for fila in filas:
            if fila.find('th'):
                continue

            celdas = fila.find_all('td')
            if len(celdas) >= 4:
                # Si alcanzamos el límite de partidos de la liga actual, cambiamos de jornada interna y estructural
                if partido_en_jornada == partidos_por_jornada:
                    partido_en_jornada = 0
                    numero_jornada += 1
                    nombre_jornada_actual = f"Jornada {numero_jornada}"
                    datos_temporada["jornadas"][nombre_jornada_actual] = []
                    print(f"\n📌 =================== JORNADA {numero_jornada} ===================")

                fecha = celdas[0].text.strip()
                local = celdas[1].text.strip()
                marcador_sucio = celdas[2].text.strip()
                visitante = celdas[3].text.strip()
                estadio = celdas[4].text.strip() if len(celdas) > 4 else "N/A"

                marcador_limpio = formatear_marcador(marcador_sucio)

                # Mantenemos el log visual en consola para monitorear el raspado
                print(f"🗓️  {fecha:<10} | {local:>24}   {marcador_limpio}   {visitante:<24} | 🏟️  {estadio}")

                # Añadimos el partido al bloque de la jornada correspondiente en el JSON
                datos_temporada["jornadas"][nombre_jornada_actual].append({
                    "fecha": fecha,
                    "local": local,
                    "resultado": marcador_limpio,
                    "visitante": visitante,
                    "estadio": estadio
                })

                partido_en_jornada += 1

        # =========================================================================
        # GUARDADO AUTOMÁTICO EN ARCHIVO JSON (MÁXIMA PORTABILIDAD)
        # =========================================================================
        directorio_ejecucion = os.getcwd()

        # Definición de ruta dinámica: /pais/liga (como División X)/jornadas/año.json
        liga_carpeta = f"Division {division}"
        ruta_carpeta = os.path.join(directorio_ejecucion, info_pais["nombre"], liga_carpeta, "jornadas")

        os.makedirs(ruta_carpeta, exist_ok=True)
        ruta_archivo_json = os.path.join(ruta_carpeta, f"{anio}.json")

        with open(ruta_archivo_json, "w", encoding="utf-8") as archivo:
            json.dump(datos_temporada, archivo, ensure_ascii=False, indent=4)

        print(f"\n[+] Archivo JSON exportado exitosamente en: {ruta_archivo_json}")
        return True

    except Exception as e:
        print(f"💥 Ocurrió un error inesperado al empaquetar los datos: {e}")
        return False


def main():
    id_pais, division, anio = seleccionar_opciones()
    url_base = generar_url_base(id_pais, division, anio)

    # Obtenemos cuántos partidos definen una jornada en el país seleccionado
    partidos_por_jornada = CONFIG_LIGAS[id_pais]["partidos_jornada"]

    # Apuntamos a la pestaña de resultados completos
    url_final = f"{url_base}?tab=results"

    print(f"\n🌍 Liga seleccionada: {CONFIG_LIGAS[id_pais]['nombre']} (División {division})")
    print(f"🌐 Conectando a: {url_final}")
    print(f"⏳ Extrayendo, formateando y guardando datos en servidor local...")

    exito = procesar_y_formatear(id_pais, division, anio, url_final, partidos_por_jornada)

    if exito:
        print("\n✅ Estructuración de datos internacional finalizada con éxito.")
    else:
        print("\n❌ Hubo un problema al procesar o exportar la solicitud.")


if __name__ == "__main__":
    main()