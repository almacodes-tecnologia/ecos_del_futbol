import os
import sys
import time
import re
import json
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Configuración y mapeo de torneos
COMPETICIONES = {
    1: {
        "nombre": "Eurocopa",
        "slug": "eurocopa",
        "carpeta": "eurocopa",
        "id_base": "EURO",
        "anios_validos": {
            2024: "2023", 2021: "2020", 2016: "2015", 2012: "2011", 2008: "2007",
            2004: "2003", 2000: "1999", 1996: "1995", 1992: "1991", 1988: "1987"
        }
    },
    2: {
        "nombre": "Copa del Mundo (Mundial)",
        "slug": "weltmeisterschaft",
        "carpeta": "copa_del_mundo",
        "id_base": "FIWC",
        "anios_validos": {
            2026: "2025", 2022: "2021", 2018: "2017", 2014: "2013", 2010: "2009",
            2006: "2005", 2002: "2001", 1998: "1997", 1994: "1993", 1990: "1989"
        }
    }
}


def raspar_torneo(comp_info, anio, s_id):
    print(f"\n[+] Configurando {comp_info['nombre']} (Año: {anio} | ID Temporada: {s_id})")

    # Estructura maestra del JSON
    datos_torneo = {
        "torneo": comp_info["nombre"],
        "anio": anio,
        "saison_id": s_id,
        "calendario": [],
        "clasificacion_grupos": {},
        "goleadores": [],
        "porteros": []
    }

    url_home = f"https://www.transfermarkt.es/{comp_info['slug']}/startseite/pokalwettbewerb/{comp_info['id_base']}?saison_id={s_id}"
    url_calendario = f"https://www.transfermarkt.es/{comp_info['slug']}/gesamtspielplan/pokalwettbewerb/{comp_info['id_base']}/saison_id/{s_id}"
    url_goleadores = f"https://www.transfermarkt.es/{comp_info['slug']}/torschuetzenliste/pokalwettbewerb/{comp_info['id_base']}/saison_id/{s_id}/plus/1"
    url_porteros = f"https://www.transfermarkt.es/{comp_info['slug']}/weisseweste/pokalwettbewerb/{comp_info['id_base']}/saison_id/{s_id}/plus/1"

    # =========================================================================
    # PARTE 1: CALENDARIO, FASES Y RESULTADOS
    # =========================================================================
    print(f"Rastreando calendario desde: {url_calendario}...\n")
    response_cal = requests.get(url_calendario, headers=HEADERS)
    if response_cal.status_code == 200:
        soup_cal = BeautifulSoup(response_cal.content, 'html.parser')
        print("=" * 95)
        print(f"{'CALENDARIO, FASES Y RESULTADOS':^95}")
        print("=" * 95)
        print(f"{'FASE / GRUPO':<25} | {'FECHA':<12} | {'LOCAL':>22} | {'RDO':^10} | {'VISITANTE':<22}")
        print("-" * 95)

        boxen = soup_cal.find_all("div", class_="box")
        for box in boxen:
            fase_header = box.find("h2")
            if not fase_header:
                continue

            fase_nombre = fase_header.get_text(strip=True)
            tabla_partidos = box.find("table")
            if not tabla_partidos:
                continue

            filas = tabla_partidos.find_all("tr")
            fecha_actual = ""

            for fila in filas:
                if "bg_blau_20" in fila.get("class", []):
                    fecha_link = fila.find("a")
                    if fecha_link:
                        fecha_actual = fecha_link.get_text(strip=True)
                    continue

                if "bg_Sturm" in fila.get("class", []):
                    cabecera_fase = fila.find("a")
                    if cabecera_fase:
                        fase_nombre = cabecera_fase.get_text(strip=True)
                    continue

                td_local = fila.select_one("td.text-right.hauptlink, td.no-border-rechts.hauptlink")
                td_visitante = fila.select_one("td.no-border-links.hauptlink")
                rdo_link = fila.find("a", class_="ergebnis-link")

                if td_local and td_visitante and rdo_link:
                    link_local = td_local.find("a", title=True)
                    link_visitante = td_visitante.find("a", title=True)

                    if link_local and link_visitante:
                        local = link_local.get_text(strip=True)
                        visitante = link_visitante.get_text(strip=True)
                        resultado = rdo_link.get_text(" ", strip=True)

                        if not fecha_actual:
                            celda_fecha = fila.find("td", class_="hide-for-small")
                            if celda_fecha:
                                fecha_texto = celda_fecha.get_text(strip=True)
                                fecha_match = re.search(r'\d{2}/\d{2}/\d{4}', fecha_texto)
                                if fecha_match:
                                    fecha_actual = fecha_match.group(0)

                        fecha_limpia = fecha_actual.replace("sáb ", "").replace("dom ", "").replace("lun ", "").replace(
                            "mar ", "").replace("mié ", "").replace("jue ", "").replace("vie ", "").strip()

                        fase_corta = (fase_nombre[:22] + '...') if len(fase_nombre) > 25 else fase_nombre
                        print(f"{fase_corta:<25} | {fecha_limpia:<12} | {local:>22} | {resultado:^10} | {visitante:<22}")

                        # CORRECCIÓN AQUÍ: Guardar los datos del partido en el JSON
                        datos_torneo["calendario"].append({
                            "fase_grupo": fase_nombre,
                            "fecha": fecha_limpia,
                            "local": local,
                            "resultado": resultado,
                            "visitante": visitante
                        })
    else:
        print(f"[-] Error al acceder al calendario. Código: {response_cal.status_code}")

    time.sleep(1.0)

    # =========================================================================
    # PARTE 2: TABLAS DE CLASIFICACIÓN
    # =========================================================================
    print("\n" + "=" * 95)
    print(f"{'TABLAS DE CLASIFICACIÓN (FASE DE GRUPOS)':^95}")
    print("=" * 95)

    response_home = requests.get(url_home, headers=HEADERS)
    if response_home.status_code == 200:
        soup_home = BeautifulSoup(response_home.text, "html.parser")
        bloques_grupos = soup_home.select("div.box")
        grupos_encontrados = False

        for bloque in bloques_grupos:
            headline = bloque.select_one("h2.content-box-headline")
            if headline and "Clasificación" in headline.text:
                grupos_encontrados = True
                nombre_grupo = headline.text.strip()

                print(f"\n> {nombre_grupo}")
                print("-" * 55)
                print(f"{'#':<4} | {'Selección':<22} | {'PJ':<4} | {'+/-':<5} | {'Ptos':<5}")
                print("-" * 55)

                datos_torneo["clasificacion_grupos"][nombre_grupo] = []

                filas_tabla = bloque.select("table.items tbody tr")
                for fila_pos in filas_tabla:
                    try:
                        pos = fila_pos.select_one("td.hauptlink").text.strip()
                        pais = fila_pos.select_one("td.no-border-links.hauptlink a").text.strip()

                        celdas_num = fila_pos.select("td.zentriert")
                        partidos_jugados = celdas_num[1].text.strip()
                        diferencia_goles = celdas_num[2].text.strip()
                        puntos = celdas_num[3].text.strip()

                        print(f"{pos:<4} | {pais:<22} | {partidos_jugados:<4} | {diferencia_goles:<5} | {puntos:<5}")

                        datos_torneo["clasificacion_grupos"][nombre_grupo].append({
                            "posicion": int(pos) if pos.isdigit() else pos,
                            "seleccion": pais,
                            "partidos_jugados": int(partidos_jugados) if partidos_jugados.isdigit() else partidos_jugados,
                            "diferencia_goles": diferencia_goles,
                            "puntos": int(puntos) if puntos.isdigit() else puntos
                        })
                    except Exception:
                        continue
        if not grupos_encontrados:
            print("[i] No se encontraron cuadros de fase de grupos en esta página.")
    else:
        print(f"[-] Error al acceder a la sección de grupos. Código: {response_home.status_code}")

    time.sleep(1.0)

    # =========================================================================
    # PARTE 3: TABLA DE GOLEADORES
    # =========================================================================
    print("\n" + "=" * 125)
    print(f"{f'TABLA DE GOLEADORES ({comp_info['nombre'].upper()})':^125}")
    print("=" * 125)
    print(f"{'#':<3} | {'JUGADOR':<22} | {'DEMARCACIÓN':<18} | {'PAÍS':<15} | {'PARTIDOS':<8} | {'ASIST.':<6} | {'PENALTI':<7} | {'MINUTOS':<9} | {'GOLES':<5}")
    print("-" * 125)

    response_goleadores = requests.get(url_goleadores, headers=HEADERS)
    if response_goleadores.status_code == 200:
        soup_goleadores = BeautifulSoup(response_goleadores.content, "html.parser")
        filas_goleadores = soup_goleadores.select("table.items tbody tr")

        for fila in filas_goleadores:
            try:
                todas_las_celdas = fila.find_all("td", recursive=False)
                if len(todas_las_celdas) < 11:
                    continue

                pos = todas_las_celdas[0].text.strip()
                if not pos or pos == "-" or not pos.isdigit():
                    continue

                jugador_tag = todas_las_celdas[1].select_one("table.inline-table td.hauptlink a")
                jugador = jugador_tag.text.strip() if jugador_tag else "Desconocido"
                if jugador == "Desconocido":
                    continue

                demarcacion_tag = todas_las_celdas[1].select("table.inline-table tr")
                demarcacion = demarcacion_tag[1].text.strip() if len(demarcacion_tag) > 1 else "-"

                bandera_tag = todas_las_celdas[3].select_one("img.flaggenrahmen")
                pais = bandera_tag.get("title").strip() if bandera_tag and bandera_tag.get("title") else todas_las_celdas[3].text.strip()

                partidos = todas_las_celdas[4].text.strip()
                asistencias = todas_las_celdas[5].text.strip()
                penaltis = todas_las_celdas[6].text.strip()
                minutos = todas_las_celdas[7].text.strip()
                goles = todas_las_celdas[10].text.strip()

                print(f"{pos:<3} | {jugador:<22} | {demarcacion:<18} | {pais:<15} | {partidos:<8} | {asistencias:<6} | {penaltis:<7} | {minutos:<9} | {goles:<5}")

                datos_torneo["goleadores"].append({
                    "posicion": int(pos),
                    "jugador": jugador,
                    "demarcacion": demarcacion,
                    "pais": pais,
                    "partidos": int(partidos) if partidos.isdigit() else partidos,
                    "asistencias": int(asistencias) if asistencias.isdigit() else asistencias,
                    "penaltis": int(penaltis) if penaltis.isdigit() else penaltis,
                    "minutos": minutos,
                    "goles": int(goles) if goles.isdigit() else goles
                })
            except Exception:
                continue
    else:
        print(f"[-] Error al acceder a la sección de goleadores. Código: {response_goleadores.status_code}")

    time.sleep(1.0)

    # =========================================================================
    # PARTE 4: TABLA DE PORTEROS
    # =========================================================================
    print("\n" + "=" * 125)
    print(f"{f'TABLA DE PORTEROS ({comp_info['nombre'].upper()})':^125}")
    print("=" * 125)
    print(f"{'#':<3} | {'PORTERO':<22} | {'PAÍS':<15} | {'PARTIDOS':<8} | {'IMBATIDO':<8} | {'G. RECIBIDOS':<12} | {'MINUTOS':<9} | {'% IMBATIBILIDAD':<15}")
    print("-" * 125)

    response_porteros = requests.get(url_porteros, headers=HEADERS)
    if response_porteros.status_code == 200:
        soup_porteros = BeautifulSoup(response_porteros.content, "html.parser")
        filas_porteros = soup_porteros.select("table.items tbody tr")

        for fila in filas_porteros:
            try:
                pos_tag = fila.select_one("td.zentriert")
                if not pos_tag:
                    continue
                pos = pos_tag.text.strip()
                if not pos or pos == "-" or not pos.isdigit():
                    continue

                portero_tag = fila.select_one("table.inline-table td.hauptlink a")
                if not portero_tag:
                    continue
                portero = portero_tag.text.strip()

                enlaces_tabla_interna = fila.select("table.inline-table td a")
                pais = "Desconocido"
                for link in enlaces_tabla_interna:
                    if link.get("title") and link.get("title") != portero:
                        pais = link.get("title").strip()
                        break

                celdas_directas = fila.find_all("td", recursive=False)
                if len(celdas_directas) >= 7:
                    partidos_p = celdas_directas[3].text.strip()
                    imbatido = celdas_directas[4].text.strip()
                    goles_recibidos = celdas_directas[5].text.strip()
                    minutos_p = celdas_directas[6].text.strip() + "'"
                else:
                    continue

                porcentaje_tag = fila.select_one("td.hauptlink.zentriert")
                porcentaje = porcentaje_tag.text.strip() if porcentaje_tag else "-"

                print(f"{pos:<3} | {portero:<22} | {pais:<15} | {partidos_p:<8} | {imbatido:<8} | {goles_recibidos:<12} | {minutos_p:<9} | {porcentaje:<15}")

                datos_torneo["porteros"].append({
                    "posicion": int(pos),
                    "portero": portero,
                    "pais": pais,
                    "partidos": int(partidos_p) if partidos_p.isdigit() else partidos_p,
                    "imbatido": int(imbatido) if imbatido.isdigit() else imbatido,
                    "goles_recibidos": int(goles_recibidos) if goles_recibidos.isdigit() else goles_recibidos,
                    "minutos": minutos_p,
                    "porcentaje_imbatibilidad": porcentaje
                })
            except Exception:
                continue
    else:
        print(f"[-] Error al acceder a la sección de porteros. Código: {response_porteros.status_code}")

    # =========================================================================
    # GUARDADO AUTOMÁTICO EN ARCHIVO JSON (MÁXIMA PORTABILIDAD)
    # =========================================================================
    # os.getcwd() toma el directorio exacto desde el cual estás ejecutando la terminal de Python
    directorio_ejecucion = os.getcwd()
    ruta_carpeta = os.path.join(directorio_ejecucion, comp_info["carpeta"])

    os.makedirs(ruta_carpeta, exist_ok=True)
    ruta_archivo_json = os.path.join(ruta_carpeta, f"{anio}.json")

    try:
        with open(ruta_archivo_json, "w", encoding="utf-8") as archivo:
            json.dump(datos_torneo, archivo, ensure_ascii=False, indent=4)
        print(f"\n[+] Archivo JSON exportado exitosamente en: {ruta_archivo_json}")
    except Exception as e:
        print(f"\n[-] Error al guardar el archivo JSON: {e}")


if __name__ == "__main__":
    print("==================================================")
    print("      SCRAPER MULTI-TORNEO (EURO / MUNDIAL)       ")
    print("==================================================")
    print("1. Eurocopa")
    print("2. Copa del Mundo (Mundial)")
    print("==================================================")

    torneo_input = input("Selecciona torneo (1 o 2): ").strip()

    if torneo_input not in ["1", "2"]:
        print("[-] Selección de torneo inválida.")
        sys.exit()

    comp_info = COMPETICIONES[int(torneo_input)]
    anio_input = input("Introduce el año (Ej: 2024, 2022) o ENTER para el último: ").strip()

    if anio_input == "":
        anio_elegido = max(comp_info["anios_validos"].keys())
    else:
        try:
            anio_elegido = int(anio_input)
        except ValueError:
            print("[-] Año inválido.")
            sys.exit()

    if anio_elegido not in comp_info["anios_validos"]:
        print(f"[-] El año {anio_elegido} no está registrado.")
        sys.exit()

    saison_id_detectada = comp_info["anios_validos"][anio_elegido]
    raspar_torneo(comp_info, anio_elegido, saison_id_detectada)