import os
import sys
import json
import requests
from bs4 import BeautifulSoup
import re
import time
import random  # Necesario para hacer pausas aleatorias humanas

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache'
}


def obtener_clasificacion_consola(anio_inicio, prefijo="", sufijo="", nombre_pais="España", division_str="Division 1"):
    anio_fin = anio_inicio + 1
    anio_fin_str = str(anio_fin)[-2:]

    temporada_id_regex = f"t{anio_inicio}-{anio_fin_str}"
    temporada_base = f"t{prefijo}{anio_inicio}-{anio_fin_str}{sufijo}"
    url = f"https://www.bdfutbol.com/es/t/{temporada_base}.html"

    print(f"\n🌐 Conectando a: {url}")

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
    except Exception as e:
        print(f"❌ Error de conexión física en {anio_inicio}: {e}")
        return False

    if response.status_code != 200:
        print(f"❌ Error {response.status_code}. No disponible o fin de historial para el año {anio_inicio}.")
        return False

    soup = BeautifulSoup(response.text, 'html.parser')
    tabla = soup.find('table', {'id': 'classific'})

    if not tabla:
        for t in soup.find_all('table'):
            texto = t.get_text()
            if "Pts" in texto and "PJ" in texto and "GF" in texto:
                tabla = t
                break

    if not tabla:
        print(f"❌ No se encontró la tabla de clasificación para el año {anio_inicio}.")
        return False

    filas = tabla.find_all('tr')

    datos_clasificacion = {
        "pais": nombre_pais,
        "liga": division_str,
        "año_inicio": anio_inicio,
        "temporada": f"{anio_inicio}-{anio_fin_str}",
        "tabla": []
    }

    print(f"\n📊 --- CLASIFICACIÓN PROCESADA ({anio_inicio}-{anio_fin_str}) ---")
    contador_posicion = 1

    for fila in filas:
        if fila.find('th') or "Pts" in fila.get_text():
            continue

        celdas = fila.find_all('td')
        if len(celdas) < 9:
            continue

        enlace_equipo = None
        for a in fila.find_all('a'):
            href = a.get('href', '')
            if temporada_id_regex in href:
                enlace_equipo = a
                break

        if not enlace_equipo:
            enlace_equipo = fila.find('a')

        if not enlace_equipo or not enlace_equipo.get_text(strip=True):
            continue

        nombre_equipo = enlace_equipo.get_text(strip=True)
        href_equipo = enlace_equipo.get('href', '')

        match_id = re.search(rf'{temporada_id_regex}(\d+)\.html', href_equipo)
        id_equipo = match_id.group(1) if match_id else "unk"

        def en_entero(nodo_celda):
            try:
                limpio = nodo_celda.get_text(strip=True).replace(' ', '').replace('\xa0', '').strip()
                return int(limpio)
            except:
                return 0

        posicion = contador_posicion
        contador_posicion += 1

        puntos = en_entero(celdas[4])
        pj = en_entero(celdas[5])
        pg = en_entero(celdas[6])
        pe = en_entero(celdas[7])
        pp = en_entero(celdas[8])

        gf, gc = 0, 0
        goles_texto = celdas[9].get_text(strip=True)
        if ':' in goles_texto:
            partes = goles_texto.split(':')
            try:
                gf = int(partes[0].strip())
                gc = int(partes[1].strip())
            except:
                pass
        else:
            gf = en_entero(celdas[9])
            if len(celdas) > 10:
                gc = en_entero(celdas[10])

        if len(celdas) > 11 and ':' in celdas[9].get_text():
            ta = en_entero(celdas[10])
            tr = en_entero(celdas[11])
        else:
            ta = en_entero(celdas[11]) if len(celdas) > 11 else 0
            tr = en_entero(celdas[12]) if len(celdas) > 12 else 0

        datos_clasificacion["tabla"].append({
            "posicion": posicion,
            "equipo": nombre_equipo,
            "id_bdfutbol": id_equipo,
            "puntos": puntos,
            "partidos_jugados": pj,
            "partidos_ganados": pg,
            "partidos_empatados": pe,
            "partidos_perdidos": pp,
            "goles_favor": gf,
            "goles_contra": gc,
            "tarjetas_amarillas": ta,
            "tarjetas_rojas": tr
        })

    # =========================================================================
    # GUARDADO AUTOMÁTICO EN ARCHIVO JSON
    # =========================================================================
    directorio_ejecucion = os.getcwd()
    ruta_carpeta = os.path.join(directorio_ejecucion, nombre_pais, division_str, "clasificaciones")
    os.makedirs(ruta_carpeta, exist_ok=True)

    ruta_archivo_json = os.path.join(ruta_carpeta, f"{anio_inicio}.json")

    try:
        with open(ruta_archivo_json, "w", encoding="utf-8") as archivo:
            json.dump(datos_clasificacion, archivo, ensure_ascii=False, indent=4)
        print(f"✅ JSON exportado con éxito: {ruta_archivo_json}")
        return True
    except Exception as e:
        print(f"❌ Error al guardar el archivo JSON: {e}")
        return False


def main():
    ligas_extranjeras = {
        "2": ("eng", "Inglaterra"),
        "3": ("ger", "Alemania"),
        "4": ("ita", "Italia"),
        "5": ("fra", "Francia"),
        "6": ("por", "Portugal"),
        "7": ("hol", "Holanda"),
        "8": ("bra", "Brasil"),
        "9": ("arg", "Argentina"),
        "10": ("tur", "Turquia"),
        "11": ("bel", "Belgica"),
        "12": ("esc", "Escocia"),
        "13": ("rus", "Rusia"),
        "14": ("sui", "Suiza"),
    }

    print("🌍 --- SELECCIÓN DE LIGA ---")
    print("1. España")
    print("2. Inglaterra")
    print("3. Alemania")
    print("4. Italia")
    print("5. Francia")
    print("6. Portugal")
    print("7. Holanda")
    print("8. Brasil")
    print("9. Argentina")
    print("10. Turquia")
    print("11. Belgica")
    print("12. Escocia")
    print("13. Rusia")
    print("14. Suiza")
    prefijo = ""
    sufijo = ""
    nombre_pais = "España"
    division_str = "Division 1"

    while True:
        pais_opcion = input("Cual pais? Selecciona un número: ").strip()
        if pais_opcion == "1":
            nombre_pais = "España"
            while True:
                division = input("Que division? (1 o 2): ").strip()
                if division == "1":
                    sufijo = ""
                    division_str = "Division 1"
                    break
                elif division == "2":
                    sufijo = "2a"
                    division_str = "Division 2"
                    break
                else:
                    print("❌ Opción inválida. Introduce '1' para Primera o '2' para Segunda.")
            break
        elif pais_opcion in ligas_extranjeras:
            prefijo = ligas_extranjeras[pais_opcion][0]
            nombre_pais = ligas_extranjeras[pais_opcion][1]
            division_str = "Division 1"
            break
        else:
            print("❌ Opción inválida. Elige un número del 1 al 9.")

    # --- CAMBIO AQUÍ: SOLICITUD DE RANGO DE AÑOS ---
    while True:
        try:
            anio_desde = int(input("📅 Año de INICIO del rango (ej. 2015): ").strip())
            anio_hasta = int(input("📅 Año de FIN del rango (ej. 2020): ").strip())
            if anio_desde > anio_hasta:
                print("❌ El año de inicio no puede ser mayor que el de fin.")
                continue
            break
        except ValueError:
            print("❌ Por favor, introduce números válidos para los años.")

    # Generamos la lista de años a procesar
    rango_anios = range(anio_desde, anio_hasta + 1)
    total_temporadas = len(rango_anios)
    print(f"\n🚀 Iniciando automatización para {total_temporadas} temporadas consecutivas...")

    for indice, anio in enumerate(rango_anios):
        print(f"\n🔄 [{indice + 1}/{total_temporadas}] Procesando año {anio}...")

        # Ejecutamos el extractor
        obtener_clasificacion_consola(anio, prefijo, sufijo, nombre_pais, division_str)

        # CONTROL DE TRÁFICO (ANTI-BAN)
        # Si quedan más años por procesar, hacemos una pausa estratégica
        if indice < total_temporadas - 1:
            # Genera una pausa aleatoria entre 3 y 7 segundos para imitar la conducta de un humano
            tiempo_espera = random.randint(3, 7)
            print(f"⏳ Pausa de seguridad: Esperando {tiempo_espera} segundos para evitar bloqueos...")
            time.sleep(tiempo_espera)

    print("\n🏁 ¡Automatización por rango completada con éxito!")


if __name__ == "__main__":
    main()