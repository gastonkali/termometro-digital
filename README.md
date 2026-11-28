# 🌡️ Termómetro Digital PBA — Monitor Multi-Red Territorial

Sistema de monitoreo territorial, alertas tempranas y agenda vecinal sobre **Facebook, X (Twitter), Instagram y Google Search** para los **135 municipios de la Provincia de Buenos Aires** (con descarte automático estricto de CABA y otras provincias).

---

## 🖥️ Uso Autónomo como Software Ejecutable (Sin IA)

El sistema está diseñado para funcionar de manera **100 % autónoma e independiente**, sin necesidad de ningún chat de IA.

### En Windows (Doble Clic)
1. **Instalación en 1 paso:** Hacé doble clic en `INSTALAR_DEPENDENCIAS.bat`. Creará el entorno virtual, instalará los paquetes y descargará Chromium automáticamente.
2. **Centro de Control Ejecutable:** Hacé doble clic en `INICIAR_TERMOMETRO.bat` o ejecutá:
   ```cmd
   python launcher.py
   ```
   Se abrirá el Centro de Control interactivo con las opciones:
   * **[1] 🚀 Ejecutar barrido territorial ahora:** Realiza una pasada inmediata por Facebook, X, Instagram y Google Noticias.
   * **[2] ⏱️ Iniciar monitoreo continuo (Daemon):** Bucle automático que barre periódicamente (ej: cada 60 min) en segundo plano.
   * **[3] 🔑 Conectar sesiones de redes:** Abre el navegador visible para que inicies sesión una sola vez en Facebook, X e Instagram.
   * **[4] 📄 Generar y abrir reporte ejecutivo PDF:** Compila y abre automáticamente el reporte ejecutivo de 1 a 2 páginas.
   * **[5] 🌐 Iniciar Panel Web:** Levanta el dashboard local en `http://localhost:5055` y lo abre en tu navegador.
   * **[6] 📲 Enviar alertas:** Dispara alertas a WhatsApp y Telegram con el PDF adjunto.

### Compilar a archivo `.exe` independiente (PyInstaller)
Podés generar un archivo ejecutable binario para Windows corriendo:
```cmd
compilar_ejecutable.bat
```
El ejecutable resultante quedará en `dist/TermometroDigital/TermometroDigital.exe`.

---

## 🚀 Despliegue en Servidor

### 1. Clonar el repositorio e instalar dependencias
```bash
git clone https://github.com/gastonkali/termometro-digital.git
cd termometro-digital

# Crear entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate  # En Linux/Mac
# o en Windows: .\venv\Scripts\activate

# Instalar librerías
pip install -r requirements.txt

# Si vas a usar Playwright para la sesión de navegador:
playwright install chromium
```

### 2. Configurar variables de entorno
```bash
cp .env.example .env
# Completar con tus claves opcionales (Brave API, Google CSE, Twilio, etc.)
```

### 3. Iniciar el Panel Web
```bash
python app.py
```
Disponible por defecto en: `http://localhost:5055` o en tu IP del servidor: `http://<IP_SERVIDOR>:5055`.

### 4. Automatización con Cron o Systemd (en Servidor Linux)
Para que el monitor corra al inicio de cada hora de forma desatendida y genere los reportes PDF:
```bash
# Agregar al crontab del servidor (crontab -e):
0 * * * * cd /ruta/al/proyecto/termometro-digital && /ruta/al/venv/bin/python run_edicion.py --modo cron_horario --max-consultas 20
```

---

## 🧭 Integración de `skills-barrido` (OSINT Especializado PBA)

El repositorio incorpora la suite completa de plugins y metodologías OSINT proveniente de `gastonkali/skills-barrido`:

| Plugin / Módulo | Alcance y Objetivo | Fuentes y Actores | Salida y Utilidad |
|---|---|---|---|
| `skills-barrido/barrido-reclamos-seguridad/` | Convocatorias vecinales por seguridad y justicia (marchas, ruidazos, cortes, concentraciones frente a comisarías y tribunales). | Páginas de Facebook y medios verificados por partido (Conurbano Sur, Oeste, Norte e Interior). | Ficha por convocatoria y detección temprana. |
| `skills-barrido/barrido-organizaciones-sociales/` | Convocatorias, ollas populares, ollazos, merenderos y reclamos por alimentos o contra el ajuste. | Cuentas verificadas de UTEP, MTE, Movimiento Evita, Polo Obrero, CCC, Barrios de Pie. | Relevamiento de presencia organizada y movilización territorial. |
| `skills-barrido/barrido-visita-de-funcionarios/` | Reclamos y manifestaciones actuales o latentes ante visitas oficiales, actos o eventos en PBA. | Cuentas gremiales (SUTEBA, ATE, CICOP, UDOCBA, CGT, CTA) y medios locales en Bahía Blanca, La Plata, Coronel Rosales, Tres Arroyos, etc. | Base de datos `actores.md`, plantilla `informe.html` y grilla `consultas.ps1`. |

### Actores y Cuentas Verificadas (`actores_barrido.py`)
Todas las cuentas de Instagram (más de 60 perfiles gremiales, vecinales y sociales), las páginas difusoras de Facebook por partido y los grupos comunitarios relevados en los plugins están centralizados en `actores_barrido.py`. El motor de recolección (`session_scraper.py`) los recorre en rotación controlada respetando los intervalos de navegación OSINT.

---

## 🔎 Pasadas Metodológicas de Búsqueda

1. **1ª Pasada (Anclaje General PBA):** Búsqueda de términos y variantes sin tilde (`inseguridad`, `justicia x`, `corte de luz`, `picadas`, etc.) combinadas con *"provincia de Buenos Aires"*, *"bonaerense"* o *"conurbano"*.
2. **2ª Pasada (135 Municipios):** Cruce sistemático con cada uno de los 135 partidos de la PBA.
3. **3ª Pasada (Nombres Propios del Día):** Seguimiento de casos, víctimas, barrios o empresas críticas vigentes (ej: *"Papelera del Sur"* o *"Universo Infantil"*).
4. **4ª Pasada Abierta (`"vecinos" + partido`):** Detector de nuevas palabras o modismos. Si una palabra nueva aparece **2 ediciones consecutivas**, se propone automáticamente para sumarse al diccionario.

---

## 📲 Alertas por WhatsApp y PDF
* Los reportes PDF ejecutivos se compilan con Chromium headless en formato A4 listo para imprimir o enviar.
* El panel web incluye botón de envío directo a WhatsApp (`wa.me`) con el resumen de convocatorias, cortes y enlace al PDF, y soporte para APIs (CallMeBot / Twilio).
