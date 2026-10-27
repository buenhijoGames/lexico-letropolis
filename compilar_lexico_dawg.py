#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compilador DAWG (Directed Acyclic Word Graph) para Letrópolis.

Transforma una lista léxica de palabras en texto plano a un grafo binario mínimo
ultra-optimizado (lexico.bin) para validación en microsegundos y consumo mínimo de memoria.

Propiedades del binario resultante:
- Tamaño reducido de ~7 MB a ~421 KB.
- Velocidad de comprobación O(longitud) en microsegundos.
- Nota: el DAWG es un formato de compresión reversible (contiene exactamente las
  mismas palabras), por lo que la lista de origen debe tener licencia libre.
  La fuente oficial es herramientas/lexico/lexico_letropolis.txt (o lexico_libre_palabreando.txt),
  generada por generar_lexico_libre.py bajo licencia MPL 1.1+.
"""

import os
import struct
import sys
import time

# Alfabeto estándar en español para Letrópolis (27 letras)
LETRAS = "ABCDEFGHIJKLMNÑOPQRSTUVWXYZ"
CHAR_TO_CODE = {c: i + 1 for i, c in enumerate(LETRAS)}
CODE_TO_CHAR = {i + 1: c for i, c in enumerate(LETRAS)}

def clave_ordenacion(palabra):
    return [CHAR_TO_CODE.get(c, 999) for c in palabra]

# Palabras estándar con K y W de la lengua española para enriquecer el vocabulario
PALABRAS_KW = [
    "KILO", "KILOS", "KILOMETRO", "KILOMETROS", "KILOGRAMO", "KILOGRAMOS",
    "KILOVATIO", "KILOVATIOS", "KILOBYTE", "KILOBYTES", "KILOBIT", "KILOBITS",
    "KILOHERCIO", "KILOHERCIOS", "KILOJULIO", "KILOJULIOS", "KILOBAUDIO",
    "KARATE", "KARATES", "KARATECA", "KARATECAS", "KIMONO", "KIMONOS",
    "KIOSCO", "KIOSCOS", "QUIOSCO", "QUIOSCOS", "KOALA", "KOALAS",
    "KETCHUP", "KETCHUPS", "KRILL", "KRILLS", "KURDO", "KURDA", "KURDOS", "KURDAS",
    "KELVIN", "KELVINS", "KAZAJO", "KAZAJA", "KAZAJOS", "KAZAJAS",
    "KEFIR", "KEFIRES", "KEPI", "KEPIS", "KAPPA", "KAPPAS", "KRAUSISMO",
    "KITSCH", "KUMIS", "KOSHER", "KASHER", "KAYAK", "KAYAKS",
    "WATER", "WATERPOLO", "WATERPOLOS", "WATERPOLISTA", "WATERPOLISTAS",
    "WEB", "WEBS", "WIFI", "WIFIS", "WOK", "WOKS", "WALKMAN", "WALKMANS",
    "WHISKY", "WHISKIES", "WINDSURF", "WINDSURFISTA", "WATT", "WATTS",
    "WAGNERIANO", "WAGNERIANA", "WAGNERIANOS", "WAGNERIANAS", "WIKIPEDIA",
    "WAFLE", "WAFLES", "WESTERN", "WESTERNS", "WIDGET", "WIDGETS"
]

class DawgNode:
    next_id = 0
    def __init__(self):
        self.id = DawgNode.next_id
        DawgNode.next_id += 1
        self.edges = {} # char -> DawgNode
        self.is_final = False

    def signature(self):
        sorted_edges = tuple(sorted((char, node.id) for char, node in self.edges.items()))
        return (self.is_final, sorted_edges)

class DawgBuilder:
    def __init__(self):
        self.root = DawgNode()
        self.minimized_nodes = {}
        self.previous_word = ""
        self.unchecked_nodes = []

    def insert(self, word):
        common_prefix = 0
        min_len = min(len(word), len(self.previous_word))
        for i in range(min_len):
            if word[i] == self.previous_word[i]:
                common_prefix += 1
            else:
                break

        self._minimize(common_prefix)

        if common_prefix == 0:
            current_node = self.root
        else:
            current_node = self.unchecked_nodes[common_prefix - 1][2]

        for char in word[common_prefix:]:
            next_node = DawgNode()
            current_node.edges[char] = next_node
            self.unchecked_nodes.append((current_node, char, next_node))
            current_node = next_node

        current_node.is_final = True
        self.previous_word = word

    def finish(self):
        self._minimize(0)

    def _minimize(self, down_to):
        while len(self.unchecked_nodes) > down_to:
            parent, char, child = self.unchecked_nodes.pop()
            sig = child.signature()
            if sig in self.minimized_nodes:
                parent.edges[char] = self.minimized_nodes[sig]
            else:
                self.minimized_nodes[sig] = child

def compilar_lexico_dawg(ruta_diccionario_txt, ruta_salida_bin):
    print("=" * 60)
    print("  COMPILADOR DAWG - LETRÓPOLIS")
    print("=" * 60)
    inicio = time.time()
    
    if not os.path.exists(ruta_diccionario_txt):
        print(f"Error: no se encontró el archivo de origen: {ruta_diccionario_txt}")
        sys.exit(1)

    directorio_destino = os.path.dirname(ruta_salida_bin)
    if not os.path.exists(directorio_destino):
        os.makedirs(directorio_destino, exist_ok=True)

    palabras_set = set()
    with open(ruta_diccionario_txt, "r", encoding="utf-8") as f:
        for linea in f:
            p = linea.strip().upper()
            if p and all(c in CHAR_TO_CODE for c in p):
                palabras_set.add(p)

    for p in PALABRAS_KW:
        if all(c in CHAR_TO_CODE for c in p):
            palabras_set.add(p)

    total_palabras = len(palabras_set)
    print(f"Total de palabras únicas a indexar: {total_palabras:,}")

    palabras_ordenadas = sorted(list(palabras_set), key=clave_ordenacion)
    print("Construyendo e indexando grafo DAWG...")

    builder = DawgBuilder()
    for idx, p in enumerate(palabras_ordenadas):
        builder.insert(p)
    builder.finish()

    # Recorrido BFS para indexación contigua de aristas
    nodes_ordered = []
    node_to_offset = {}
    current_edge_offset = 0

    q = [builder.root]
    visited = {builder.root.id}

    while q:
        curr = q.pop(0)
        nodes_ordered.append(curr)
        if curr.edges:
            node_to_offset[curr.id] = current_edge_offset
            current_edge_offset += len(curr.edges)
            for char in sorted(curr.edges.keys(), key=lambda c: CHAR_TO_CODE[c]):
                child = curr.edges[char]
                if child.id not in visited:
                    visited.add(child.id)
                    q.append(child)
        else:
            node_to_offset[curr.id] = 0

    total_bytes = current_edge_offset * 4
    print(f"Nodos únicos minimizados: {len(nodes_ordered):,}")
    print(f"Aristas compactadas: {current_edge_offset:,}")
    print(f"Tamaño binario final: {total_bytes:,} bytes ({total_bytes / (1024*1024):.2f} MB)")

    # Escribir archivo binario
    with open(ruta_salida_bin, "wb") as f_out:
        # Magic: 'LPLE' (0x4C504C45), seguido de número de aristas
        magic = 0x4C504C45
        f_out.write(struct.pack(">II", magic, current_edge_offset))

        for node in nodes_ordered:
            if not node.edges:
                continue
            sorted_chars = sorted(node.edges.keys(), key=lambda c: CHAR_TO_CODE[c])
            for idx, char in enumerate(sorted_chars):
                child = node.edges[char]
                is_last = 1 if idx == len(sorted_chars) - 1 else 0
                is_final = 1 if child.is_final else 0
                char_code = CHAR_TO_CODE[char]
                child_offset = node_to_offset.get(child.id, 0)
                
                entry = (is_final << 31) | (is_last << 30) | ((char_code & 0x3F) << 24) | (child_offset & 0x00FFFFFF)
                f_out.write(struct.pack(">I", entry))

    print(f"Compilación completada en {time.time() - inicio:.2f} s")
    print(f"Archivo generado en: {ruta_salida_bin}")

if __name__ == "__main__":
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    origen_letropolis = os.path.join(base_dir, "herramientas", "lexico", "lexico_letropolis.txt")
    origen_historico = os.path.join(base_dir, "herramientas", "lexico", "lexico_libre_palabreando.txt")
    origen = origen_letropolis if os.path.exists(origen_letropolis) else origen_historico
    destino = os.path.join(base_dir, "app", "src", "main", "assets", "lexico.bin")
    compilar_lexico_dawg(origen, destino)
