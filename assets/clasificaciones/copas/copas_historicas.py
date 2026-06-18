import os
import sys
import json
import requests
from bs4 import BeautifulSoup
import re
import time
import random

# Definimos las cabeceras aquí de forma global
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def seleccionar_torneo():
    print("🏆 --- TORNEOS NACIONALES ---")
    print(" 0. Copa del Rey (España)")
    print(" 1. Supercopa (España) - e.j. 2023")
    print(" 2. Community Shield (Inglaterra) - e.j. 2023")
    print(" 3. Supercoppa (Italia) - e.j. 2023")
    print(" 4. Trophée des Champions (Francia)")
    print(" 5. DFL-Supercup (Alemania)")
    print(" 6. Supertaça (Portugal)")
    print(" 8. Johan Cruijff Schaal (Holanda)")
    print(" 9. Süper Kupası (Turquia)")
    print("10. Pro League Supercup (Belgica)")
    print("11. Superkubok  (Rusia)")
    print("12. Premiership Relegation (Escocia)")
    print("13. Premiership Championship (Escocia)")
    print("🏆 --- TORNEOS EUROPEOS ---")
    print("14. Liga de Campeones")
    print("15. Europa League (desde 1971)")
    print("16. Copa de Conferencia (desde 2021)")
    print("17. Supercopa de Europa (desde 1973)")
    print("18. Recopa (1960 - 1998)")
    print("19. Copa Mitropa (1926 - 1939)")
    print("20. Copa de Ferias (1955 - 1971)")
    print("🏆 --- TORNEOS DEL MUNDO ---")
    print("21. Mundial de Clubes (desde 1999)")
    print("22. FIFA Club World (2024)")
    print("23. Copa Intercontinental (1960 - 2004)")
    print("\n")

    opcion = input("⚽ Selecciona el torneo: ").strip()

    # --- CAMBIO AQUÍ: SOLICITUD DE RANGO EN LUGAR DE UN SOLO AÑO ---
    print("\n--- Definir rango cronológico ---")
    anio_desde = int(input("📅 Año de INICIO del rango (ej. 2018): ").strip())
    anio_hasta = int(input("📅 Año de FIN del rango (ej. 2023): ").strip())

    return opcion, list(range(anio_desde, anio_hasta + 1))


def obtener_url_copa(opcion, anio):
    try:
        anio_int = int(anio)
        siguiente_anio_str = str(anio_int + 1)[-2:]
        temporada_str = f"{anio_int}-{siguiente_anio_str}"
    except ValueError:
        print("❌ Año no válido.")
        return None, None, None, None

    # Mapeamos también el país correspondiente para generar la carpeta correcta
    # Si es europeo o mundial, se asigna "Internacional"
    codigos = {
        "0": ("COP", "Copa del Rey", "España"),
        "1": ("SUP", "Supercopa (España)", "España"),
        "2": ("SHI", "Community Shield (Inglaterra)", "Inglaterra"),
        "3": ("ISC", "Supercopa (Italia)", "Italia"),
        "4": ("FSC", "Supercopa (Francia)", "Francia"),
        "5": ("DSC", "Supercopa (Alemania)", "Alemania"),
        "6": ("PSC", "Supercopa (Portugal)", "Portugal"),
        "7": ("PSC", "Supercopa (Portugal)", "Portugal"),  # Por seguridad en caso de typo en tu menú
        "8": ("HSC", "Johan Cruijff Schaal (Holanda)", "Holanda"),
        "9": ("TSC", "Süper Kupası (Turquia)", "Turquia"),
        "10": ("BSC", "Pro League Supercup (Belgica)", "Belgica"),
        "11": ("RSC", "Superkubok  (Rusia)", "Rusia"),
        "12": ("SP1", "Premiership Relegation (Escocia)", "Escocia"),
        "13": ("SCF", "Premiership Championship (Escocia)", "Escocia"),
        "14": ("CHA", "Liga de Campeones", "Internacional"),
        "15": ("UEF", "Europa League", "Internacional"),
        "16": ("CNF", "Copa de Conferencia", "Internacional"),
        "17": ("SCE", "Supercopa de Europa", "Internacional"),
        "18": ("REC", "Recopa", "Internacional"),
        "19": ("MIT", "Copa Mitropa", "Internacional"),
        "20": ("FER", "Copa de Ferias", "Internacional"),
        "21": ("MUN", "Mundial de Clubes", "Internacional"),
        "22": ("FIF", "FIFA Club World", "Internacional"),
        "23": ("INT", "Copa Intercontinental", "Internacional")
    }

    if opcion in codigos:
        codigo_torneo, nombre_torneo, pais = codigos[opcion]
        url_resultados = f"https://www.bdfutbol.com/es/t/t{temporada_str}a{codigo_torneo}.html?tab=results"
        return url_resultados, nombre_torneo, pais, temporada_str
    else:
        print("⚠️ Opción de torneo no válida.")
        return None, None, None, None


def extraer_resultados(url_resultados, nombre_torneo, pais, anio_int, temporada_str):
    print(f"\n🌐 Extrayendo resultados desde: {url_resultados}")

    try:
        response = requests.get(url_resultados, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            print(f"❌ Error al acceder a la web ({response.status_code})")
            return False
    except Exception as e:
        print(f"❌ Error en la petición: {e}")
        return False

    soup = BeautifulSoup(response.text, "html.parser")
    partidos_dict = {}

    # ----------------------------------------------------
    # INTENTO 1: Formato Moderno - Buscar clase "marcadorrr"
    # ----------------------------------------------------
    todos_los_marcadores = soup.find_all("div", class_="marcadorrr")

    for marcador in todos_los_marcadores:
        link = marcador.find("a")
        if not link or "id=" not in link.get("href", ""):
            continue

        id_partido = int(link["href"].split("id=")[-1])

        contenedor_padre = marcador.find_parent(class_=lambda x: x and ('elim' in x or 'quadre' in x or 'final' in x))
        if not contenedor_padre:
            contenedor_padre = marcador.parent

        div_local = contenedor_padre.find("div", class_=lambda x: x and "localrr" in x)
        div_visitante = contenedor_padre.find("div", class_=lambda x: x and "visitantrr" in x)

        if not div_local or not div_visitante:
            continue

        equipo_local = div_local.get_text(strip=True)
        equipo_visitante = div_visitante.get_text(strip=True)

        ganador_clase = None
        perdedor_clase = None

        if 'perdedor' in div_local.get('class', []): perdedor_clase = equipo_local
        if 'perdedor' in div_visitante.get('class', []): perdedor_clase = equipo_visitante
        if 'guanyador' in div_local.get('class', []): ganador_clase = equipo_local
        if 'guanyador' in div_visitante.get('class', []): ganador_clase = equipo_visitante

        goles_local = marcador.find("div", class_="marcalocalrr")
        goles_visitante = marcador.find("div", class_="marcavisitantrr")

        txt_goles_local = goles_local.get_text(strip=True) if goles_local else "0"
        txt_goles_vis = goles_visitante.get_text(strip=True) if goles_visitante else "0"

        partidos_dict[id_partido] = {
            "id": id_partido,
            "local": equipo_local,
            "visitante": equipo_visitante,
            "g_local": txt_goles_local,
            "g_vis": txt_goles_vis,
            "hubo_penaltis": False,
            "penaltis_local": None,
            "penaltis_visitante": None,
            "ganador_clase": ganador_clase,
            "perdedor_clase": perdedor_clase
        }

    # ----------------------------------------------------
    # INTENTO 2 (FALLBACK): Formato Clásico - Por posición de columnas
    # ----------------------------------------------------
    if not partidos_dict:
        tabla_partidos = soup.find("table", id="partits-competicio") or soup.find("table",
                                                                                  class_=re.compile(r"partits"))

        if tabla_partidos:
            filas = tabla_partidos.find_all("tr")
            for fila in filas:
                link_partido = fila.find("a", href=re.compile(r"p\.php\?id=\d+"))
                if not link_partido:
                    continue

                id_partido = int(link_partido["href"].split("id=")[-1])
                celdas = fila.find_all("td")

                if len(celdas) < 7:
                    continue

                td_local = celdas[2]
                td_visitante = celdas[6]

                equipo_local = td_local.get_text(strip=True)
                equipo_visitante = td_visitante.get_text(strip=True)

                divs_goles = fila.find_all("div", class_=re.compile(r"resultat-gols"))

                if len(divs_goles) >= 2:
                    txt_goles_local = divs_goles[0].get_text(strip=True)
                    txt_goles_vis = divs_goles[1].get_text(strip=True)
                else:
                    texto_marcador = link_partido.get_text(strip=True)
                    if "-" in texto_marcador:
                        txt_goles_local, txt_goles_vis = [g.strip() for g in texto_marcador.split("-")[:2]]
                    else:
                        txt_goles_local, txt_goles_vis = "0", "0"

                hubo_penaltis = False
                pen_local = None
                pen_vis = None

                div_info = fila.find("div", attrs={"data-toggle": "tooltip"})
                if div_info and div_info.get("title"):
                    texto_tooltip = div_info["title"]
                    match_penaltis = re.search(r"(\d+)-(\d+)\s*$", texto_tooltip.strip())
                    if not match_penaltis:
                        match_penaltis = re.search(r"(\d+)-(\d+)", texto_tooltip)

                    if match_penaltis:
                        hubo_penaltis = True
                        pen_local = int(match_penaltis.group(1))
                        pen_vis = int(match_penaltis.group(2))

                partidos_dict[id_partido] = {
                    "id": id_partido,
                    "local": equipo_local,
                    "visitante": equipo_visitante,
                    "g_local": txt_goles_local,
                    "g_vis": txt_goles_vis,
                    "hubo_penaltis": hubo_penaltis,
                    "penaltis_local": pen_local,
                    "penaltis_visitante": pen_vis,
                    "ganador_clase": None,
                    "perdedor_clase": None
                }

    if not partidos_dict:
        print("⚠️ No se pudieron extraer partidos para este torneo/año.")
        return False

    partidos_ordenados = [partidos_dict[id_p] for id_p in sorted(partidos_dict.keys())]
    total_partidos = len(partidos_ordenados)

    contador_emparejamientos = {}
    for p in partidos_ordenados:
        pareja = tuple(sorted([p["local"], p["visitante"]]))
        contador_emparejamientos[pareja] = contador_emparejamientos.get(pareja, 0) + 1

    pareja_final = tuple(sorted([partidos_ordenados[-1]["local"], partidos_ordenados[-1]["visitante"]]))
    partidos_totales_final = contador_emparejamientos[pareja_final]

    partidos_finales_lista = []

    for i, p in enumerate(partidos_ordenados):
        pareja_actual = tuple(sorted([p["local"], p["visitante"]]))
        distancia_al_final = total_partidos - 1 - i

        if pareja_actual == pareja_final and distancia_al_final < partidos_totales_final:
            partidos_finales_lista.append(p)
            if partidos_totales_final == 1:
                ronda_str = "Final"
            elif partidos_totales_final == 2:
                ronda_str = "Final - Ida" if len(partidos_finales_lista) == 1 else "Final - Vuelta"
            else:
                if len(partidos_finales_lista) == 1:
                    ronda_str = "Final - Ida"
                elif len(partidos_finales_lista) == 2:
                    ronda_str = "Final - Vuelta"
                else:
                    ronda_str = "Final - Desempate"
        else:
            if total_partidos <= 4:
                ronda_base = "Semifinal"
            else:
                if distancia_al_final <= 4:
                    ronda_base = "Semifinal"
                elif distancia_al_final <= 12:
                    ronda_base = "Cuartos de Final"
                else:
                    ronda_base = "Octavos de Final"

            total_cruces = contador_emparejamientos[pareja_actual]
            if total_cruces == 1:
                ronda_str = ronda_base
            else:
                anteriores = sum(1 for x in partidos_ordenados[:i + 1] if
                                 tuple(sorted([x["local"], x["visitante"]])) == pareja_actual)
                ronda_str = f"{ronda_base} - Ida" if anteriores == 1 else f"{ronda_base} - Vuelta"

        p["ronda"] = ronda_str

    # ----------------------------------------------------
    # 3. CUADRO DE HONOR GLOBAL
    # ----------------------------------------------------
    print("\n👑 === CUADRO DE HONOR ===")
    campeon = "No detectado"
    subcampeon = "No detectado"

    if partidos_finales_lista:
        team_a = partidos_finales_lista[0]["local"]
        team_b = partidos_finales_lista[0]["visitante"]

        goles_totales = {team_a: 0, team_b: 0}
        ganador_forzado = None
        perdedor_forzado = None

        for pf in partidos_finales_lista:
            loc = pf["local"]
            vis = pf["visitante"]

            try:
                g_loc = int(''.join(filter(str.isdigit, pf["g_local"])))
                g_vis = int(''.join(filter(str.isdigit, pf["g_vis"])))
            except ValueError:
                g_loc, g_vis = 0, 0

            goles_totales[loc] += g_loc
            goles_totales[vis] += g_vis

            if pf["hubo_penaltis"]:
                if pf["penaltis_local"] > pf["penaltis_visitante"]:
                    ganador_forzado = loc
                else:
                    ganador_forzado = vis

            if pf["ganador_clase"]: ganador_forzado = pf["ganador_clase"]
            if pf["perdedor_clase"]: perdedor_forzado = pf["perdedor_clase"]

        if ganador_forzado:
            campeon = ganador_forzado
            subcampeon = team_a if campeon == team_b else team_b
        elif perdedor_forzado:
            subcampeon = perdedor_forzado
            campeon = team_a if subcampeon == team_b else team_b
        else:
            if goles_totales[team_a] > goles_totales[team_b]:
                campeon = team_a
                subcampeon = team_b
            elif goles_totales[team_b] > goles_totales[team_a]:
                campeon = team_b
                subcampeon = team_a
            else:
                campeon = f"Empate global entre {team_a} y {team_b}"
                subcampeon = "No determinado"

    print(f"🥇 Campeón: {campeon}")
    print(f"🥈 Subcampeón: {subcampeon}")

    # ----------------------------------------------------
    # 4. IMPRIMIR RESULTADOS
    # ----------------------------------------------------
    print("\n⚽ === PARTIDOS LOCALIZADOS ===")
    for p in partidos_ordenados:
        texto_penaltis = f" (Ganado por penaltis: {p['penaltis_local']}-{p['penaltis_visitante']})" if p[
            'hubo_penaltis'] else ""
        print(
            f"📌 [{p['ronda']}] {p['local']} vs {p['visitante']} | ID: {p['id']} | Marcador: {p['g_local']}-{p['g_vis']}{texto_penaltis}")

    # =========================================================================
    # NUEVO: ESTRUCTURACIÓN Y EXPORTACIÓN DEL JSON EN LA RUTA /pais/copa/año.json
    # =========================================================================
    datos_json = {
        "pais": pais,
        "copa": nombre_torneo,
        "año_inicio": anio_int,
        "temporada": temporada_str,
        "cuadro_honor": {
            "campeon": campeon,
            "subcampeon": subcampeon
        },
        "partidos": []
    }

    # Volcamos los partidos limpiando marcas temporales de control HTML
    for p in partidos_ordenados:
        datos_json["partidos"].append({
            "id_partido": p["id"],
            "ronda": p["ronda"],
            "local": p["local"],
            "visitante": p["visitante"],
            "goles_local": p["g_local"],
            "goles_visitante": p["g_vis"],
            "hubo_penaltis": p["hubo_penaltis"],
            "penaltis_local": p["penaltis_local"],
            "penaltis_visitante": p["penaltis_visitante"]
        })

    # Obtenemos la ruta absoluta de ejecución del script
    ruta_base = os.getcwd()
    ruta_carpeta = os.path.join(ruta_base, pais, nombre_torneo)
    os.makedirs(ruta_carpeta, exist_ok=True)

    ruta_completa_json = os.path.join(ruta_carpeta, f"{anio_int}.json")

    try:
        with open(ruta_completa_json, "w", encoding="utf-8") as archivo:
            json.dump(datos_json, archivo, ensure_ascii=False, indent=4)
        print(f"\n[+] Archivo JSON guardado exitosamente en: {ruta_completa_json}")
        return True
    except Exception as e:
        print(f"❌ Error al guardar el archivo JSON: {e}")
        return False


def main():
    opcion, lista_anios = seleccionar_torneo()
    total_años = len(lista_anios)

    print(f"\n🚀 Iniciando procesamiento automatizado de {total_años} temporadas...")

    for indice, anio in enumerate(lista_anios):
        url_resultados, nombre_torneo, pais, temporada_str = obtener_url_copa(opcion, anio)

        if url_resultados:
            print(f"\n==================================================================")
            print(f"⏳ [{indice + 1}/{total_años}] Procesando: {nombre_torneo} ({anio})")
            print(f"==================================================================")

            extraer_resultados(url_resultados, nombre_torneo, pais, anio, temporada_str)
        else:
            print(f"❌ Saltar año {anio} debido a un error de configuración.")

        # Pausa anti-ban estratégica: imita el comportamiento humano entre descargas consecutivas
        if indice < total_años - 1:
            espera = random.randint(3, 7)
            print(f"\n⏳ Pausa de protección: Esperando {espera} segundos para evitar bloqueos del servidor...")
            time.sleep(espera)

    print("\n🏁 Proceso de rango finalizado con éxito (Exit Code 0)")


if __name__ == "__main__":
    main()