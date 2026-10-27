#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador del léxico libre de Letrópolis.

Construye la lista de palabras jugables a partir de fuentes con licencia libre
y la compila al grafo binario DAWG que usa la app (app/src/main/assets/lexico.bin).

Fuentes:
  - herramientas/lexico/fuentes/rla-es/es_ES.dic + es_ES.aff
    Recursos Lingüísticos Abiertos del Español (RLA-ES), usado bajo MPL 1.1+.
  - herramientas/lexico/suplemento.txt   (palabras añadidas a mano)
  - herramientas/lexico/exclusiones.txt  (abreviaturas y símbolos a descartar)

Salidas:
  - herramientas/lexico/lexico_letropolis.txt  (obra derivada, MPL 1.1+)
  - app/src/main/assets/lexico.bin

Uso:
  python herramientas/generar_lexico_libre.py
"""

import re
import sys
import unicodedata
from pathlib import Path

from compilar_lexico_dawg import compilar_lexico_dawg

# Rutas del proyecto
RAIZ = Path(__file__).resolve().parent.parent
DIR_LEXICO = RAIZ / "herramientas" / "lexico"
DIR_FUENTE = DIR_LEXICO / "fuentes" / "rla-es"
RUTA_SUPLEMENTO = DIR_LEXICO / "suplemento.txt"
RUTA_EXCLUSIONES = DIR_LEXICO / "exclusiones.txt"
RUTA_LISTA_SALIDA = DIR_LEXICO / "lexico_letropolis.txt"
RUTA_BINARIO = RAIZ / "app" / "src" / "main" / "assets" / "lexico.bin"

# Longitudes jugables en un tablero de 15 casillas
LONGITUD_MINIMA = 2
LONGITUD_MAXIMA = 15

# Vocales usadas para descartar abreviaturas sin vocal (pts, cfr...)
VOCALES = set("aeiouy")

CABECERA_LICENCIA = """# Léxico libre de Letrópolis
# Obra derivada de "Recursos Lingüísticos Abiertos del Español" (RLA-ES)
# https://github.com/sbosio/rla-es
# Este archivo se distribuye bajo la Mozilla Public License, versión 1.1 o posterior.
# Modificaciones: expansión de afijos, normalización (minúsculas, sin tildes),
# eliminación de nombres propios, abreviaturas y símbolos, y suplemento manual.
"""


def leer_lista_simple(ruta):
    """
    Lee un archivo de una palabra por línea ignorando comentarios y vacíos.

    @param ruta Ruta del archivo de texto.
    @return Conjunto de palabras normalizadas.
    """
    if not ruta.exists():
        return set()
    resultado = set()
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if linea and not linea.startswith("#"):
            normalizada = normalizar(linea, permitir_mayuscula=True)
            if normalizada:
                resultado.add(normalizada)
    return resultado


def leer_afijos(ruta):
    """
    Lee las reglas PFX/SFX de un archivo .aff de Hunspell (FLAG UTF-8).

    @param ruta Ruta del archivo .aff.
    @return Diccionario bandera -> (tipo, admite_cruce, lista_de_reglas).
    """
    reglas = {}
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lineas):
        partes = lineas[i].split()
        # Cabecera de bloque: "SFX bandera Y|N numero"
        if len(partes) == 4 and partes[0] in ("PFX", "SFX") and partes[2] in ("Y", "N"):
            tipo, bandera, cruce, total = partes[0], partes[1], partes[2] == "Y", int(partes[3])
            lista = []
            for j in range(1, total + 1):
                p = lineas[i + j].split()
                quitar = "" if p[2] == "0" else p[2]
                anadir, _, continuacion = p[3].partition("/")
                anadir = "" if anadir == "0" else anadir
                condicion = p[4] if len(p) > 4 else "."
                patron = re.compile(("^" + condicion) if tipo == "PFX" else (condicion + "$"))
                lista.append((quitar, anadir, patron, continuacion))
            reglas[bandera] = (tipo, cruce, lista)
            i += total + 1
        else:
            i += 1
    return reglas


def aplicar_sufijos(palabra, banderas, reglas, profundidad=0):
    """
    Aplica los sufijos indicados (y sus continuaciones, un nivel más).

    @return Lista de tuplas (forma, admite_cruce_con_prefijo).
    """
    salida = []
    for bandera in banderas:
        regla = reglas.get(bandera)
        if not regla or regla[0] != "SFX":
            continue
        _, cruce, lista = regla
        for quitar, anadir, patron, continuacion in lista:
            if patron.search(palabra) and (not quitar or palabra.endswith(quitar)):
                base = palabra[: len(palabra) - len(quitar)] if quitar else palabra
                nueva = base + anadir
                salida.append((nueva, cruce))
                # Sufijos encadenados (p. ej. pronombres enclíticos)
                if continuacion and profundidad == 0:
                    salida.extend(aplicar_sufijos(nueva, continuacion, reglas, 1))
    return salida


def aplicar_prefijos(palabra, banderas, reglas):
    """
    Aplica los prefijos indicados a una palabra.

    @return Lista de formas prefijadas.
    """
    salida = []
    for bandera in banderas:
        regla = reglas.get(bandera)
        if not regla or regla[0] != "PFX":
            continue
        for quitar, anadir, patron, _ in regla[2]:
            if patron.search(palabra) and (not quitar or palabra.startswith(quitar)):
                salida.append(anadir + palabra[len(quitar):])
    return salida


def expandir_diccionario(ruta_dic, reglas):
    """
    Genera todas las formas de un .dic de Hunspell aplicando sus afijos.

    @return Conjunto de formas crudas (con tildes y mayúsculas originales).
    """
    formas = set()
    for linea in ruta_dic.read_text(encoding="utf-8").splitlines()[1:]:
        linea = linea.strip()
        if not linea:
            continue
        raiz, _, banderas = linea.partition("/")
        banderas = banderas.split()[0] if banderas else ""
        formas.add(raiz)
        sufijadas = aplicar_sufijos(raiz, banderas, reglas)
        formas.update(forma for forma, _ in sufijadas)
        prefijos = [b for b in banderas if reglas.get(b, ("",))[0] == "PFX"]
        formas.update(aplicar_prefijos(raiz, prefijos, reglas))
        # Producto cruzado prefijo + sufijo
        for forma, cruce in sufijadas:
            if cruce:
                formas.update(aplicar_prefijos(forma, prefijos, reglas))
    return formas


def normalizar(palabra, permitir_mayuscula=False):
    """
    Pasa a minúsculas, quita tildes y diéresis (conserva la ñ) y valida.

    @param palabra Forma original.
    @param permitir_mayuscula Si es False, descarta nombres propios y siglas.
    @return Palabra normalizada o None si no es jugable.
    """
    if not palabra:
        return None
    if not permitir_mayuscula and palabra[0].isupper():
        return None
    texto = palabra.lower().replace("ñ", "\0")
    texto = "".join(c for c in unicodedata.normalize("NFD", texto)
                    if unicodedata.category(c) != "Mn")
    texto = texto.replace("\0", "ñ")
    if not re.fullmatch(r"[a-zñ]+", texto):
        return None
    if not (LONGITUD_MINIMA <= len(texto) <= LONGITUD_MAXIMA):
        return None
    if not VOCALES.intersection(texto):
        return None
    return texto


def main():
    """Genera la lista libre y la compila a lexico.bin."""
    reglas = leer_afijos(DIR_FUENTE / "es_ES.aff")
    crudas = expandir_diccionario(DIR_FUENTE / "es_ES.dic", reglas)
    palabras = {n for n in (normalizar(f) for f in crudas) if n}
    total_rla = len(palabras)

    exclusiones = leer_lista_simple(RUTA_EXCLUSIONES)
    suplemento = leer_lista_simple(RUTA_SUPLEMENTO)

    excluidas = palabras & exclusiones
    palabras -= exclusiones
    nuevas_suplemento = suplemento - palabras
    palabras |= suplemento

    print(f"Formas RLA-ES jugables: {total_rla:,}")
    print(f"Excluidas (abreviaturas): {len(excluidas):,}")
    print(f"Añadidas por suplemento: {len(nuevas_suplemento):,} "
          f"(ya presentes: {len(suplemento) - len(nuevas_suplemento)})")
    print(f"Total léxico final: {len(palabras):,}")

    RUTA_LISTA_SALIDA.write_text(
        CABECERA_LICENCIA + "\n".join(sorted(palabras)) + "\n", encoding="utf-8"
    )
    print(f"Lista publicable escrita en: {RUTA_LISTA_SALIDA}")

    compilar_lexico_dawg(str(RUTA_LISTA_SALIDA), str(RUTA_BINARIO))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
