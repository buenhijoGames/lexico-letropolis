# lexico-letropolis
Léxico libre en español para el juego Letrópolis (581.000+ palabras), derivado de RLA-ES bajo licencia Mozilla Public License (MPL 1.1+).

# 📖 Léxico Oficial de Letrópolis

Este repositorio contiene la lista oficial de palabras válidas en español empleadas en el juego de palabras cruzadas **Letrópolis** (desarrollado por [buenhijoGames](https://github.com/buenhijogames)).

La publicación de este léxico en texto plano se realiza en estricto cumplimiento de los términos de la **Mozilla Public License (MPL) versión 1.1 o posterior**.

---

## ⚖️ Licencia y Atribución de Fuentes

El léxico contenido en este repositorio es una obra derivada construida a partir del proyecto de código abierto:

* **Fuente original:** [Recursos Lingüísticos Abiertos del Español (RLA-ES)](https://github.com/sbosio/rla-es)
* **Autores originales:** Santiago Bosio y colaboradores.
* **Licencia de origen:** Triple licencia disjunta GPL 3.0+ / LGPL 3.0+ / MPL 1.1+.
* **Licencia elegida para esta obra derivada:** **Mozilla Public License (MPL), versión 1.1 o posterior**.

Conforme a la sección 3.1 y 3.2 de la licencia MPL, cualquier modificación o lista derivada debe ponerse a disposición pública en formato de texto legible ("Source Code form") bajo los mismos términos de licencia.

---

## 🛠️ Modificaciones Realizadas

A partir de las fuentes morfológicas originales de RLA-ES (`es_ES.dic` y `es_ES.aff`), se han aplicado los siguientes procesos artesanos y computacionales:

1. **Expansión morfológica completa:** Generación sistemática de formas flexionadas (género, número, tiempos verbales y participios) mediante reglas de afijos con Hunspell.
2. **Normalización ortográfica para tablero:** Conversión a minúsculas sin tildes diacríticas (conservando la letra **Ñ** como carácter independiente conforme a la lengua española).
3. **Filtrado de caracteres y entradas no jugables:** Eliminación de abreviaturas, símbolos, siglas, números, puntuaciones y nombres propios que no constituyen jugadas reglamentarias de palabras cruzadas.
4. **Incorporación de enclíticos:** Admisión reglamentaria de formas verbales con pronombres enclíticos (*dámelo*, *contenerlo*, *amándola*), dinamizando el juego conforme a los estándares de palabras cruzadas modernas.
5. **Suplemento léxico contemporáneo:** Inclusión revisada a mano de préstamos léxicos asentados e incorporados al abecedario oficial de la Real Academia Española (incluyendo términos con **K** y **W**).

---

## 📂 Archivos en este repositorio

* **[`lexico_letropolis.txt`](lexico_letropolis.txt):** Listado completo en texto plano (UTF-8, una palabra por línea) con **581.022 palabras únicas**.
* **`LICENSE`:** Texto oficial de la licencia Mozilla Public License 1.1.

---

## 📱 Uso en la Aplicación

Para optimizar el rendimiento y la memoria en dispositivos Android, la aplicación **Letrópolis** no carga este archivo de texto plano de ~7 MB en memoria, sino que lo compila previamente a un grafo acíclico dirigido mínimo (**DAWG binario de 421 KB**, `lexico.bin`), permitiendo validaciones ultrarrápidas en tiempo $O(L)$ (microsegundos) y con funcionamiento 100% offline sin conexión a internet.

