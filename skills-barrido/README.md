# Skills de barrido OSINT

Tres plugins de Claude Code para barridos por fuentes abiertas en la provincia de Buenos Aires.

| Plugin | Skill | Qué hace | Salida |
|---|---|---|---|
| `barrido-reclamos-seguridad/` | `barrido-reclamos-seguridad` | Convocatorias vecinales por seguridad y reclamos de justicia (marchas, ruidazos, cortes, concentraciones en comisarías) | Un Word por convocatoria |
| `barrido-visita-de-funcionarios/` | `barrido-redes` | Convocatorias, cortes y reclamos ante visitas oficiales o eventos en una localidad | PDF 9:16 con fichas y capturas |
| `barrido-organizaciones-sociales/` | `barrido-organizaciones-sociales` | Convocatorias, ollas, cortes y reclamos de organizaciones sociales (UTEP, MTE, Evita, CCC, etc.) | Informe |

## Estructura

```
<plugin>/
  .claude-plugin/plugin.json   # manifiesto del plugin
  skills/<skill>/SKILL.md      # instrucciones del skill
```

`barrido-visita-de-funcionarios` incluye además:

- `actores.md` — listado de cuentas/actores relevados
- `plantilla/informe.html` — plantilla del PDF
- `scripts/*.ps1` — consultas, barrido de Instagram, recorte de capturas y generación del PDF (PowerShell)

## Instalación

Copiar la carpeta del plugin en un marketplace local de Claude Code o cargarla con `claude --plugin-dir <ruta-al-plugin>`.
