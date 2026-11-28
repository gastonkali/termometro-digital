# -*- coding: utf-8 -*-
"""
launcher.py — Centro de Control y Ejecutor Autónomo de Termómetro Digital PBA
Permite ejecutar el sistema como un software independiente (desktop / consola / daemon),
sin depender de ningún chat de IA:
1. Inicio de sesión en redes (Facebook, X, Instagram) en ventana visible.
2. Ejecución inmediata de barrido territorial completo (Playwright + Noticias + Grupos + Actores).
3. Monitoreo continuo desatendido (bucle programable cada N horas/minutos).
4. Generación y apertura del reporte ejecutivo en PDF (1-2 páginas).
5. Panel Web local (Flask) con apertura automática en navegador.
6. Envío de alertas a WhatsApp y Telegram.
"""

import argparse
import os
import sys
import time
import webbrowser
from datetime import datetime
import subprocess

# Asegurar codificación utf-8 en terminal de Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

from database import init_db, get_conn
from config_pba import PARTIDOS_PBA, PARTIDOS_CONURBANO


def limpiar_pantalla():
    os.system("cls" if os.name == "nt" else "clear")


def banner():
    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║        🌡️  TERMÓMETRO DIGITAL PBA — MONITOR MULTI-RED TERRITORIAL        ║
║   Inteligencia Territorial OSINT · 135 Municipios Bonaerenses            ║
║   Facebook · X (Twitter) · Instagram · Google Noticias · Alertas PDF     ║
╚══════════════════════════════════════════════════════════════════════════╝
""")


def menu_login():
    limpiar_pantalla()
    banner()
    print("🔑 INICIO DE SESIÓN EN REDES SOCIALES")
    print("----------------------------------------------------------------------")
    print("Se abrirá una ventana de navegador para que inicies sesión con tus")
    print("cuentas. Tus cookies y sesiones quedarán guardadas permanentemente")
    print("en la carpeta local 'user_session_browser'.")
    print("")
    print("  [1] Iniciar sesión en las 3 redes (Facebook, X e Instagram)")
    print("  [2] Conectar o cambiar cuenta de X (Twitter)")
    print("  [3] Conectar o actualizar cuenta de Instagram")
    print("  [0] Volver al menú principal")
    print("----------------------------------------------------------------------")
    opc = input("Seleccioná una opción (0-3): ").strip()
    
    from session_scraper import modo_login, conectar_cuenta_x, conectar_cuenta_ig
    if opc == "1":
        modo_login()
    elif opc == "2":
        conectar_cuenta_x()
    elif opc == "3":
        conectar_cuenta_ig()
    input("\nPresioná ENTER para continuar...")


def menu_barrido_manual():
    limpiar_pantalla()
    banner()
    print("🚀 EJECUTAR BARRIDO TERRITORIAL MANUAL")
    print("----------------------------------------------------------------------")
    print("El sistema recorrerá Google Noticias, búsquedas públicas de PBA,")
    print("páginas de medios locales verificadas, grupos vecinales y cuentas de Instagram.")
    print("")
    headless_input = input("¿Correr con navegador en segundo plano (oculto)? (S/N) [por defecto S]: ").strip().lower()
    headless = False if headless_input == "n" else True
    
    max_c_input = input("Cantidad de consultas a ejecutar por pasada [por defecto 6]: ").strip()
    max_consultas = int(max_c_input) if max_c_input.isdigit() else 6

    print("\nIniciando recolección territorial...")
    from session_scraper import ejecutar_ciclo_recoleccion
    ejecutar_ciclo_recoleccion(headless=headless, max_consultas=max_consultas)
    
    print("\n✓ Barrido finalizado y almacenado en la base de datos.")
    abrir_pdf_reciente()
    input("\nPresioná ENTER para volver al menú...")


def menu_monitoreo_continuo():
    limpiar_pantalla()
    banner()
    print("⏱️ MODO MONITOREO CONTINUO / AUTOMÁTICO (DAEMON)")
    print("----------------------------------------------------------------------")
    print("El sistema quedará ejecutándose en bucle, realizando un barrido periódico,")
    print("actualizando métricas de conflicto y generando reportes automáticamente.")
    print("")
    int_input = input("Intervalo entre barridos en minutos [por defecto 60]: ").strip()
    intervalo_min = int(int_input) if int_input.isdigit() and int(int_input) > 0 else 60
    
    headless_input = input("¿Navegador oculto (headless)? (S/N) [por defecto S]: ").strip().lower()
    headless = False if headless_input == "n" else True

    print(f"\nIniciando monitor continuo (ciclos cada {intervalo_min} minutos)...")
    print("Presioná CTRL + C en cualquier momento para detenerlo.")
    print("======================================================================\n")

    from session_scraper import ejecutar_ciclo_recoleccion
    from pdf_service import crear_reporte_pdf_edicion
    
    ciclo = 1
    try:
        while True:
            ahora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            print(f"\n[Ciclo #{ciclo} — {ahora}] Ejecutando recolección...")
            ejecutar_ciclo_recoleccion(headless=headless, max_consultas=6)
            print(f"\n✓ Ciclo #{ciclo} finalizado. Próxima corrida en {intervalo_min} minutos...")
            ciclo += 1
            for seg in range(intervalo_min * 60, 0, -1):
                mins = seg // 60
                secs = seg % 60
                sys.stdout.write(f"\rPróximo ciclo en: {mins:02d}:{secs:02d} | Presioná CTRL+C para salir ")
                sys.stdout.flush()
                time.sleep(1)
            print("")
    except KeyboardInterrupt:
        print("\n\n⏹️ Monitoreo continuo detenido por el usuario.")
        time.sleep(1.5)


def abrir_pdf_reciente():
    from pdf_service import PDF_OUTPUT_DIR
    pdf_path = os.path.join(PDF_OUTPUT_DIR, "Alerta_Termometro_PBA_Ultima.pdf")
    if os.path.exists(pdf_path):
        preg = input("\n¿Deseas abrir el PDF ejecutivo generado en tu visor? (S/N) [S]: ").strip().lower()
        if preg != "n":
            try:
                os.startfile(pdf_path) if os.name == "nt" else subprocess.call(["xdg-open", pdf_path])
            except Exception as e:
                print(f"Ruta del PDF: {pdf_path} (error abriendo automáticamente: {e})")
    else:
        print(f"\nPDF disponible en la carpeta: {PDF_OUTPUT_DIR}")


def menu_generar_pdf():
    limpiar_pantalla()
    banner()
    print("📄 GENERACIÓN DE REPORTE EJECUTIVO PDF (1-2 PÁGINAS)")
    print("----------------------------------------------------------------------")
    print("Compila los hechos vigentes en el formato ejecutivo corregido:")
    print("• Semáforo general de clima (BUENO / MODERADO / EN ALERTA).")
    print("• Tabla resumida de hechos agrupados ordenada por repercusión.")
    print("• Tarjetas compactas solo para hechos en alerta con comentarios y links.")
    print("• Anexo de trazabilidad de ítems descartados y palabras nuevas.")
    print("")

    from pdf_service import crear_reporte_pdf_edicion, PDF_OUTPUT_DIR
    print("Compilando reporte con Chromium headless...")
    ruta = crear_reporte_pdf_edicion(edicion_id=None)
    if ruta and os.path.exists(ruta):
        print(f"\n✓ Reporte generado exitosamente en:\n  {ruta}")
        try:
            os.startfile(ruta) if os.name == "nt" else subprocess.call(["xdg-open", ruta])
        except Exception:
            pass
    else:
        print("Aviso: No se pudo compilar el PDF. Verificá que existan hallazgos cargados.")
    input("\nPresioná ENTER para continuar...")


def menu_panel_web():
    limpiar_pantalla()
    banner()
    print("🌐 INICIANDO PANEL WEB DE CONTROL (http://localhost:5055)")
    print("----------------------------------------------------------------------")
    print("Se levantará el servidor Flask local con la interfaz visual interactiva.")
    print("Se abrirá automáticamente en tu navegador predeterminado.")
    print("Para detener el servidor, presioná CTRL + C en esta ventana.")
    print("----------------------------------------------------------------------\n")
    time.sleep(1)
    webbrowser.open("http://localhost:5055")
    from app import app
    app.run(host="127.0.0.1", port=5055, debug=False)


def menu_alertas():
    limpiar_pantalla()
    banner()
    print("📲 ENVÍO DE ALERTAS (WHATSAPP / TELEGRAM)")
    print("----------------------------------------------------------------------")
    print("  [1] Generar y enviar reporte matutino por WhatsApp / Telegram")
    print("  [2] Probar alerta directa a Telegram con el último PDF")
    print("  [0] Volver al menú principal")
    print("----------------------------------------------------------------------")
    opc = input("Seleccioná una opción: ").strip()
    if opc == "1":
        from reporte_matutino import enviar_reporte_matutino
        enviar_reporte_matutino()
    elif opc == "2":
        from telegram_service import enviar_alerta_telegram
        from pdf_service import PDF_OUTPUT_DIR, obtener_hechos_importantes
        pdf_path = os.path.join(PDF_OUTPUT_DIR, "Alerta_Termometro_PBA_Ultima.pdf")
        datos = {
            "edicion_id": "Prueba",
            "total_hallazgos": 1,
            "nuevos_hallazgos": 1,
            "convocatorias": [],
            "nombres_propios": [],
            "hallazgos_destacados": [],
            "relevamiento_grupos": [],
            "hechos_importantes": obtener_hechos_importantes(max_hechos=3)
        }
        res = enviar_alerta_telegram(datos, ruta_pdf=pdf_path if os.path.exists(pdf_path) else "")
        print("Resultado Telegram:", res)
    input("\nPresioná ENTER para continuar...")


def main():
    init_db()
    parser = argparse.ArgumentParser(description="Launcher Autónomo Termómetro Digital PBA")
    parser.add_argument("--auto", action="store_true", help="Iniciar directamente en modo monitoreo continuo")
    parser.add_argument("--barrido", action="store_true", help="Ejecutar un barrido manual inmediato y salir")
    parser.add_argument("--web", action="store_true", help="Iniciar directamente el panel web local")
    parser.add_argument("--pdf", action="store_true", help="Generar el PDF ejecutivo y salir")
    parser.add_argument("--login", action="store_true", help="Abrir ventana de login de redes y salir")
    parser.add_argument("--headless", action="store_true", help="Modo sin ventana gráfica para servidores")
    args = parser.parse_args()

    if args.auto:
        from session_scraper import ejecutar_ciclo_recoleccion
        print("Modo automático desatendido...")
        ejecutar_ciclo_recoleccion(headless=args.headless, max_consultas=6)
        sys.exit(0)
    elif args.barrido:
        from session_scraper import ejecutar_ciclo_recoleccion
        ejecutar_ciclo_recoleccion(headless=args.headless, max_consultas=6)
        sys.exit(0)
    elif args.web:
        from app import app
        webbrowser.open("http://localhost:5055")
        app.run(host="0.0.0.0", port=5055, debug=False)
        sys.exit(0)
    elif args.pdf:
        from pdf_service import crear_reporte_pdf_edicion
        crear_reporte_pdf_edicion(edicion_id=None)
        sys.exit(0)
    elif args.login:
        from session_scraper import modo_login
        modo_login()
        sys.exit(0)

    # Menú Interactivo
    while True:
        limpiar_pantalla()
        banner()
        print("SELECCIONÁ UNA ACCIÓN:")
        print("  [1] 🚀 Ejecutar barrido territorial ahora (Manual)")
        print("  [2] ⏱️ Iniciar monitoreo continuo programado (Daemon / Bucle)")
        print("  [3] 🔑 Conectar o renovar sesiones de redes (FB / X / IG)")
        print("  [4] 📄 Generar y abrir reporte ejecutivo PDF (1-2 páginas)")
        print("  [5] 🌐 Iniciar Panel Web de Control (Dashboard local)")
        print("  [6] 📲 Enviar alertas por WhatsApp / Telegram")
        print("  [0] 🚪 Salir")
        print("----------------------------------------------------------------------")
        opcion = input("Opción: ").strip()

        if opcion == "1":
            menu_barrido_manual()
        elif opcion == "2":
            menu_monitoreo_continuo()
        elif opcion == "3":
            menu_login()
        elif opcion == "4":
            menu_generar_pdf()
        elif opcion == "5":
            menu_panel_web()
        elif opcion == "6":
            menu_alertas()
        elif opcion == "0":
            print("\n¡Hasta luego!")
            break


if __name__ == "__main__":
    main()
