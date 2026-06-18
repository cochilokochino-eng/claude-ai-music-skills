"""Genera 20 titulos virales + concepto + gancho para los temas del CSV.

A diferencia de main.py (que genera la letra completa de cada corrido), este
script produce solo la parte de "empaque viral" para cada tema en UNA sola
llamada a la API, y guarda el resultado en TITULOS.md y TITULOS.json.

Uso:
    python generar_titulos.py
    python generar_titulos.py --temas temas.csv --salida . --limite 20
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from corridos.almacenamiento import leer_temas
from corridos.cliente import ClienteCorridos, ErrorAPI
from corridos.config import Config, ConfigError
from corridos.generador import _extraer_json

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("titulos")

RAIZ = Path(__file__).resolve().parent

SYSTEM_PROMPT = (
    "Eres un experto en marketing de musica regional mexicana y en titulos "
    "virales para YouTube/TikTok de corridos nortenos. Creas titulos con alto "
    "CTR, conceptos claros y ganchos emocionales. Respondes SIEMPRE en espanol "
    "y SOLO con JSON valido, sin texto adicional ni bloques de codigo."
)


def construir_prompt(temas) -> str:
    lista = "\n".join(
        f"{i}. TEMA: {t.tema} | ENFOQUE: {t.enfoque}"
        for i, t in enumerate(temas, start=1)
    )
    return f"""
Para cada uno de los siguientes {len(temas)} temas de corridos para el DIA DEL
PADRE, crea un empaque viral.

{lista}

Devuelve EXCLUSIVAMENTE un objeto JSON con esta forma EXACTA:

{{
  "items": [
    {{
      "numero": 1,
      "tema": "el tema original",
      "titulo": "Titulo viral con alto CTR (max 70 caracteres, emotivo, llamativo)",
      "concepto": "1-2 frases que describen la idea/historia central del corrido",
      "gancho": "Gancho emocional corto para miniatura/primer comentario (max 90 caracteres)"
    }}
  ]
}}

REGLAS:
- Devuelve EXACTAMENTE {len(temas)} items, en el mismo orden y numeracion.
- Titulos originales y emotivos; nada de mencionar o imitar artistas reales.
- Tono: celebracion respetuosa de la figura paterna, estilo corrido norteno.
- Responde solo con el JSON. Nada de explicaciones ni ```.
""".strip()


def guardar_md(items: list[dict], ruta: Path) -> None:
    lineas = [
        "# 20 titulos virales para corridos del Dia del Padre",
        "",
        "Por cada tema: titulo viral, concepto y gancho emocional.",
        "",
    ]
    for it in items:
        lineas.extend(
            [
                f"## {it.get('numero', '?')}. {it.get('titulo', '').strip()}",
                "",
                f"- **Tema:** {it.get('tema', '').strip()}",
                f"- **Concepto:** {it.get('concepto', '').strip()}",
                f"- **Gancho:** {it.get('gancho', '').strip()}",
                "",
            ]
        )
    ruta.write_text("\n".join(lineas), encoding="utf-8")


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Genera 20 titulos virales + concepto + gancho."
    )
    p.add_argument("--temas", type=Path, default=RAIZ / "temas.csv")
    p.add_argument("--salida", type=Path, default=RAIZ)
    p.add_argument("--limite", type=int, default=20)
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)

    try:
        config = Config.desde_entorno()
    except ConfigError as exc:
        logger.error("%s", exc)
        return 2

    try:
        temas = leer_temas(args.temas)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("%s", exc)
        return 2

    if args.limite > 0:
        temas = temas[: args.limite]

    logger.info(
        "Modelo: %s | Endpoint: %s | Temas: %d",
        config.model,
        config.base_url,
        len(temas),
    )

    cliente = ClienteCorridos(config)
    try:
        respuesta = cliente.completar(SYSTEM_PROMPT, construir_prompt(temas))
        datos = _extraer_json(respuesta)
    except (ErrorAPI, ValueError) as exc:
        logger.error("Fallo la generacion: %s", exc)
        return 1

    items = datos.get("items") if isinstance(datos, dict) else None
    if not isinstance(items, list) or not items:
        logger.error("La respuesta no contiene una lista 'items' valida.")
        return 1

    args.salida.mkdir(parents=True, exist_ok=True)
    ruta_json = args.salida / "TITULOS.json"
    ruta_md = args.salida / "TITULOS.md"
    ruta_json.write_text(
        json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    guardar_md(items, ruta_md)

    logger.info("Generados %d titulos.", len(items))
    logger.info("Guardado: %s y %s", ruta_md, ruta_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
