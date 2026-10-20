#!/usr/bin/env python3
"""Genera la presentación PowerPoint del proyecto de Regresión Lineal Múltiple."""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn
import copy

# -----------------------------------------------------------------------------
# Colores y estilo
# -----------------------------------------------------------------------------
AZUL_OSCURO   = RGBColor(0x1F, 0x3A, 0x5F)   # Heading color del informe
AZUL_MEDIO    = RGBColor(0x2E, 0x5A, 0x88)
AZUL_CLARO    = RGBColor(0xD9, 0xE2, 0xEC)
GRIS          = RGBColor(0x55, 0x55, 0x55)
BLANCO        = RGBColor(0xFF, 0xFF, 0xFF)
NEGRO         = RGBColor(0x22, 0x22, 0x22)
VERDE         = RGBColor(0x1E, 0x7A, 0x3C)
ROJO          = RGBColor(0xB0, 0x2A, 0x2A)
AMARILLO      = RGBColor(0xF2, 0xC1, 0x4E)

FONT = "Calibri"

prs = Presentation()
prs.slide_width  = Inches(13.333)  # 16:9
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def add_slide():
    return prs.slides.add_slide(BLANK)

def rect(slide, x, y, w, h, fill, line=None, shadow=False):
    shp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, h)
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(1)
    shp.shadow.inherit = False
    return shp

def txt(slide, x, y, w, h, runs, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
        space_after=4, line_spacing=1.0, wrap=True):
    """runs: lista de párrafos; cada párrafo es lista de (texto, size, bold, color, italic)."""
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = wrap
    tf.vertical_anchor = anchor
    tf.margin_left = Pt(2); tf.margin_right = Pt(2)
    tf.margin_top = Pt(1); tf.margin_bottom = Pt(1)
    for i, para in enumerate(runs):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(space_after)
        p.line_spacing = line_spacing
        # Normalizar: permitir párrafo como lista de runs o un solo run plano
        if isinstance(para, (list, tuple)) and len(para) >= 4 and isinstance(para[0], str) and isinstance(para[1], (int, float)):
            para = [para]
        for run in para:
            (t, size, bold, color, *rest) = run
            italic = rest[0] if rest else False
            r = p.add_run(); r.text = t
            r.font.name = FONT; r.font.size = Pt(size)
            r.font.bold = bold; r.font.italic = italic
            r.font.color.rgb = color
    return tb

def title_bar(slide, kicker, title, num=None, total=None):
    """Barra superior con título y número de diapositiva."""
    rect(slide, 0, 0, prs.slide_width, Inches(1.05), AZUL_OSCURO)
    rect(slide, 0, Inches(1.05), prs.slide_width, Inches(0.06), AMARILLO)
    txt(slide, Inches(0.55), Inches(0.12), Inches(11.0), Inches(0.3),
        [[(kicker, 12, True, RGBColor(0xF5, 0xB7, 0xB1))]])
    txt(slide, Inches(0.55), Inches(0.40), Inches(11.5), Inches(0.6),
        [[(title, 26, True, BLANCO)]])
    if num:
        txt(slide, Inches(12.35), Inches(0.30), Inches(0.7), Inches(0.5),
            [[(f"{num}", 20, True, BLANCO)]], align=PP_ALIGN.RIGHT)

def footer(slide, texto="Regresión Lineal Múltiple  ·  Generación eléctrica Colombia  ·  datos.gov.co"):
    rect(slide, 0, prs.slide_height - Inches(0.34), prs.slide_width, Inches(0.34), AZUL_CLARO)
    txt(slide, Inches(0.55), prs.slide_height - Inches(0.30), Inches(12.0), Inches(0.28),
        [[(texto, 8.5, False, GRIS)]], anchor=MSO_ANCHOR.MIDDLE)

def bullets(slide, x, y, w, h, items, size=16, color=NEGRO, space_after=8,
            marker="▪ ", marker_color=AZUL_MEDIO, line_spacing=1.05):
    """items: lista de (texto, nivel) o texto plano."""
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = Pt(2); tf.margin_right = Pt(2)
    for i, it in enumerate(items):
        if isinstance(it, tuple):
            texto, nivel = it
        else:
            texto, nivel = it, 0
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(space_after)
        p.line_spacing = line_spacing
        p.level = nivel
        mk = marker if nivel == 0 else "–"
        r = p.add_run(); r.text = mk + " "
        r.font.name = FONT; r.font.size = Pt(size if nivel == 0 else size - 2)
        r.font.bold = True; r.font.color.rgb = marker_color if nivel == 0 else GRIS
        r2 = p.add_run(); r2.text = texto
        r2.font.name = FONT; r2.font.size = Pt(size if nivel == 0 else size - 2)
        r2.font.color.rgb = color
    return tb

def add_table(slide, x, y, w, h, headers, rows, font_size=13, header_fill=AZUL_OSCURO,
              header_color=BLANCO, col_widths=None, row_height=0.32, aligns=None,
              highlight_rows=None, highlight_fill=RGBColor(0xFD, 0xF2, 0xD9)):
    n_rows = len(rows) + 1
    n_cols = len(headers)
    shp = slide.shapes.add_table(n_rows, n_cols, x, y, w, h)
    tbl = shp.table
    # desactivar banda automática
    tbl.first_row = True; tbl.horz_banding = True
    if col_widths:
        total_w = sum(col_widths)
        for j, cw in enumerate(col_widths):
            tbl.columns[j].width = Emu(int(w * cw / total_w))
    for j, hh in enumerate(headers):
        cell = tbl.cell(0, j)
        cell.fill.solid(); cell.fill.fore_color.rgb = header_fill
        cell.margin_left = Pt(5); cell.margin_right = Pt(5)
        cell.margin_top = Pt(2); cell.margin_bottom = Pt(2)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = cell.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run(); r.text = hh
        r.font.name = FONT; r.font.size = Pt(font_size); r.font.bold = True
        r.font.color.rgb = header_color
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = tbl.cell(i + 1, j)
            cell.margin_left = Pt(5); cell.margin_right = Pt(5)
            cell.margin_top = Pt(1); cell.margin_bottom = Pt(1)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            if highlight_rows and i in highlight_rows:
                cell.fill.solid(); cell.fill.fore_color.rgb = highlight_fill
            else:
                cell.fill.solid()
                cell.fill.fore_color.rgb = BLANCO if i % 2 == 0 else RGBColor(0xEE, 0xF3, 0xF8)
            p = cell.text_frame.paragraphs[0]
            al = PP_ALIGN.CENTER
            if aligns:
                al = aligns[j] if j < len(aligns) else PP_ALIGN.CENTER
            p.alignment = al
            r = p.add_run(); r.text = str(val)
            r.font.name = FONT; r.font.size = Pt(font_size - 1)
            r.font.color.rgb = NEGRO
            if highlight_rows and i in highlight_rows:
                r.font.bold = True
    # altura filas
    for i in range(n_rows):
        tbl.rows[i].height = Inches(0.30 if i == 0 else row_height)
    return tbl

def add_notes(slide, texto):
    slide.notes_slide.notes_text_frame.text = texto

def pic(slide, path, x, y, w=None, h=None):
    return slide.shapes.add_picture(path, x, y, width=w, height=h)

CARPETA = "/mnt/c/Users/felis/OneDrive/Escritorio/Python/Regresion lineal multiple"

# =============================================================================
# DIAPOSITIVA 1 — PORTADA
# =============================================================================
s = add_slide()
rect(s, 0, 0, prs.slide_width, prs.slide_height, AZUL_OSCURO)
rect(s, 0, Inches(4.9), prs.slide_width, Inches(0.08), AMARILLO)
txt(s, Inches(0.9), Inches(1.35), Inches(11.5), Inches(1.7), [
    [("INFORME / PRESENTACIÓN", 15, True, RGBColor(0xF5, 0xB7, 0xB1))],
    [("Regresión Lineal Múltiple", 44, True, BLANCO)],
    [("Predicción del promedio mensual de generación eléctrica en Colombia", 20, False, RGBColor(0xCF, 0xDA, 0xE6))],
], space_after=10)
txt(s, Inches(0.9), Inches(3.35), Inches(11.5), Inches(1.4), [
    [("Variable objetivo (Y): promedio_mensual_gwh   │   Predictores: máximo (X₁) y mínimo (X₂)", 15, False, BLANCO)],
    [("Método: ecuación normal + gradiente descendente  ·  Muestra n = 10  ·  Sin sklearn (NumPy puro)", 14, False, RGBColor(0xCF, 0xDA, 0xE6))],
    [("Fuente: datos.gov.co  ·  Vista tq63-itzr (2.786 registros, 2000–2026, 13 fuentes)", 13, False, RGBColor(0xCF, 0xDA, 0xE6))],
], space_after=6)
txt(s, Inches(0.9), Inches(5.25), Inches(11.5), Inches(1.6), [
    [("Evento evaluativo · 18 de octubre · Valor 15%", 14, True, AMARILLO)],
    [("Elaborado con: 01_descargar.py → 02_modelo.py → 03_informe.py", 12, False, RGBColor(0xCF, 0xDA, 0xE6))],
    [("Entregable: Informe_Regresion_Lineal_Multiple.docx", 12, False, RGBColor(0xCF, 0xDA, 0xE6))],
], space_after=6)
add_notes(s, "Portada. Presentar el objetivo: predecir generación promedio mensual a partir de máx/mín. Mencionar que todo se hizo con NumPy puro y que el informe DOCX es el entregable formal.")

# =============================================================================
# DIAPOSITIVA 2 — OBJETIVO DEL PROBLEMA
# =============================================================================
s = add_slide()
title_bar(s, "Planteamiento", "¿Qué queremos predecir?", num="2")
footer(s)
bullets(s, Inches(0.7), Inches(1.45), Inches(7.4), Inches(5.2), [
    ("Objetivo: predecir el promedio mensual de generación (Y, en GWh) a partir del máximo (X₁) y el mínimo (X₂) registrados en ese mes y fuente energética.", 0),
    ("Tipo de problema: regresión supervisada con variable objetivo continua y dos predictores continuos.", 0),
    ("Suposición física: el promedio mensual debe ubicarse entre el mínimo y el máximo, por lo que modelarlo como combinación lineal de ambos es coherente.", 0),
    ("No usamos año, mes ni fuente como predictores: sirven solo para trazabilidad y estratificación de la muestra.", 0),
    ("Descartamos generacion_total como predictor: total / promedio ≈ días del mes (sería predecir algo trivial).", 0),
], size=16)
# Panel derecho resumen
rect(s, Inches(8.4), Inches(1.5), Inches(4.35), Inches(5.2), AZUL_CLARO)
txt(s, Inches(8.65), Inches(1.7), Inches(3.9), Inches(0.4), [["RESUMEN DEL MODELO", 14, True, AZUL_OSCURO]])
formulas = [
    ("ŷ = b₀ + b₁·X₁ + b₂·X₂", "Ecuación de regresión"),
    ("b = (XᵀX)⁻¹·Xᵀy", "Ecuación normal (mínimos cuadrados)"),
    ("J(b) = (1/2m)·Σ(ŷᵢ − yᵢ)²", "Función de costo"),
]
yy = 2.25
for f, d in formulas:
    rect(s, Inches(8.65), Inches(yy), Inches(3.85), Inches(0.85), BLANCO)
    txt(s, Inches(8.8), Inches(yy + 0.08), Inches(3.6), Inches(0.7), [
        [(f, 15, True, AZUL_OSCURO)],
        [(d, 10.5, False, GRIS, True)],
    ], space_after=1)
    yy += 1.0
add_notes(s, "Explicar la lógica física: promedio entre min y max. Justificar por qué OLS con 2 predictores: interpretable, solución cerrada verificable a mano. Descartar total por fuga de información (días del mes).")

# =============================================================================
# DIAPOSITIVA 3 — ORIGEN DE LOS DATOS
# =============================================================================
s = add_slide()
title_bar(s, "Datos", "Origen y preparación de la información", num="3")
footer(s)
txt(s, Inches(0.7), Inches(1.35), Inches(7.3), Inches(0.4), [["FUENTE OFICIAL", 14, True, AZUL_OSCURO]])
bullets(s, Inches(0.7), Inches(1.8), Inches(7.3), Inches(2.4), [
    ("API: https://www.datos.gov.co/api/v3/views/tq63-itzr/query.json", 0),
    ("Vista: generación eléctrica por fuente en Colombia (promedio / máximo / mínimo mensual en GWh)", 0),
    ("Registros: 2.786 filas · periodo 2000–2026 · 13 fuentes energéticas (AGUA, GAS, CARBÓN, ACPM, etc.)", 0),
    ("Descarga y limpieza automatizadas con 01_descargar.py → datos_completos.csv", 0),
], size=14, space_after=8)
txt(s, Inches(0.7), Inches(4.15), Inches(7.3), Inches(0.4), [["DECISIONES CLAVE SOBRE LOS DATOS", 14, True, AZUL_OSCURO]])
bullets(s, Inches(0.7), Inches(4.6), Inches(7.3), Inches(2.4), [
    ("No usar generacion_total: ratio total/promedio ≈ días del mes (mediana 30,0) → contaminado por duración del mes.", 0),
    ("Muestra intencional estratificada n = 10 (8 fuentes, rango bajo/medio/alto) para cálculo manual verificable.", 0),
    ("Sin valores nulos; no se eliminaron atípicos (ej. AGUA 70–90 GWh) porque son informativos.", 0),
], size=14, space_after=8)
rect(s, Inches(8.4), Inches(1.5), Inches(4.35), Inches(5.2), BLANCO, line=AZUL_MEDIO)
txt(s, Inches(8.65), Inches(1.7), Inches(3.9), Inches(0.4), [["DATOS COMPLETOS (datos_completos.csv)", 13, True, AZUL_OSCURO]])
stats = [
    ("Filas", "2.786"),
    ("Periodo", "2000 – 2026"),
    ("Fuentes", "13"),
    ("Columnas numéricas", "5"),
    ("Valores nulos", "0"),
    ("Script", "01_descargar.py"),
]
yy = 2.25
for k, v in stats:
    txt(s, Inches(8.65), Inches(yy), Inches(2.3), Inches(0.35), [[(k, 11.5, True, GRIS)]])
    txt(s, Inches(10.45), Inches(yy), Inches(2.35), Inches(0.35), [[(v, 12, False, AZUL_OSCURO)]])
    yy += 0.5
add_notes(s, "Origen: API pública datos.gov.co. Decisión importante: no usar generación total porque es prácticamente promedio × días del mes. Muestra de 10 elegida a propósito para que el cálculo sea trazable.")

# =============================================================================
# DIAPOSITIVA 4 — MUESTRA DE TRABAJO
# =============================================================================
s = add_slide()
title_bar(s, "Muestra", "Muestra de trabajo (n = 10)", num="4")
footer(s)
txt(s, Inches(0.7), Inches(1.28), Inches(11.5), Inches(0.4), [["MUESTRA INTENCIONAL ESTRATIFICADA (muestra_10.csv)", 13, True, AZUL_OSCURO]])
headers = ["#", "Año", "Mes", "Fuente", "Y (prom.)", "X₁ (máx)", "X₂ (mín)"]
rows = [
    ["1", "2000", "1", "AGUA", "70.28", "76.41", "57.63"],
    ["2", "2000", "1", "GAS", "16.26", "19.19", "12.29"],
    ["3", "2000", "2", "CARBÓN", "12.10", "15.35", "7.41"],
    ["4", "2000", "4", "OTROS", "11.40", "19.08", "5.41"],
    ["5", "2001", "2", "ACPM", "6.94", "16.69", "0.43"],
    ["6", "2001", "4", "GAS", "23.98", "26.34", "19.80"],
    ["7", "2000", "8", "BAGAZO", "0.29", "0.32", "0.06"],
    ["8", "2000", "12", "COMBUSTÓLEO", "2.50", "2.98", "0.01"],
    ["9", "2001", "2", "JET-A1", "0.88", "1.16", "0.10"],
    ["10", "2000", "12", "AGUA", "90.37", "103.01", "70.30"],
]
add_table(s, Inches(0.7), Inches(1.75), Inches(7.6), Inches(4.2), headers, rows,
          font_size=12, row_height=0.36)
txt(s, Inches(0.7), Inches(6.15), Inches(7.6), Inches(0.9), [
    [("Medias: Ȳ = 23,5006  ·  media X₁ = 28,0531  ·  media X₂ = 17,3434", 11, True, AZUL_OSCURO)],
    [("Rango de Y: 0,29 a 90,37 GWh (cubre bajo, medio y alto)", 10.5, False, GRIS)],
], space_after=2)
# Panel derecho
rect(s, Inches(8.65), Inches(1.5), Inches(4.05), Inches(5.35), AZUL_CLARO)
txt(s, Inches(8.9), Inches(1.68), Inches(3.6), Inches(0.4), [["CÓMO SE ELIGIÓ", 13, True, AZUL_OSCURO]])
bullets(s, Inches(8.9), Inches(2.1), Inches(3.6), Inches(4.6), [
    ("10 registros, 8 fuentes distintas", 0),
    ("Rango bajo (Bagazo, Jet-A1)", 0),
    ("Rango medio (Gas, ACPM)", 0),
    ("Rango alto (Agua)", 0),
    ("Años y meses variados", 0),
    ("Sin nulos, sin eliminar extremos", 0),
], size=12, space_after=7)
add_notes(s, "Mostrar la tabla real de la muestra. Resaltar que cubre todo el rango (0,29 a 90,37) y 8 fuentes, y que las medias son Ȳ=23,5006. Esto permite hacer el cálculo a mano y verificar cada paso.")

# =============================================================================
# DIAPOSITIVA 5 — MODELO MATEMÁTICO
# =============================================================================
s = add_slide()
title_bar(s, "Modelo", "Regresión Lineal Múltiple (OLS)", num="5")
footer(s)
rect(s, Inches(0.7), Inches(1.45), Inches(11.9), Inches(1.15), AZUL_CLARO)
txt(s, Inches(0.95), Inches(1.6), Inches(11.4), Inches(0.9), [
    [("ŷ = b₀ + b₁·X₁ + b₂·X₂", 30, True, AZUL_OSCURO)],
    [("b₀ = intercepto   │   b₁ = efecto del máximo   │   b₂ = efecto del mínimo", 13, False, GRIS)],
], space_after=4)
txt(s, Inches(0.7), Inches(2.85), Inches(5.9), Inches(0.4), [["¿POR QUÉ ESTE ALGORITMO?", 14, True, AZUL_OSCURO]])
bullets(s, Inches(0.7), Inches(3.3), Inches(5.9), Inches(3.8), [
    ("Objetivo continuo y relación física esperada (promedio ≈ función de máx/mín).", 0),
    ("Solo 2 predictores → modelo interpretable: cada coeficiente se lee en GWh.", 0),
    ("Solución cerrada verificable a mano con matrices 3×3 (objetivo pedagógico).", 0),
    ("Descartadas: KNN/árboles (no dan ecuación explícita), regresión simple (pierde un predictor).", 0),
], size=13.5, space_after=7)
rect(s, Inches(6.95), Inches(2.85), Inches(5.65), Inches(3.95), BLANCO, line=AZUL_MEDIO)
txt(s, Inches(7.2), Inches(3.0), Inches(5.2), Inches(0.4), [["HIPÓTESIS DEL MODELO", 13, True, AZUL_OSCURO]])
bullets(s, Inches(7.2), Inches(3.45), Inches(5.2), Inches(3.2), [
    ("Linealidad entre predictores y objetivo.", 0),
    ("Errores de media cero e independencia.", 0),
    ("Homocedasticidad (varianza de errores constante).", 0),
    ("Multicolinealidad X₁–X₂: r = 0,986 (se discute como limitación).", 0),
], size=12.5, space_after=7)
add_notes(s, "Presentar la ecuación y la interpretación de cada coeficiente. Justificar OLS por interpretabilidad y porque permite desarrollo manual. Mencionar hipótesis y advertir de la alta correlación entre máx y mín.")

# =============================================================================
# DIAPOSITIVA 6 — ECUACIÓN NORMAL PASO A PASO
# =============================================================================
s = add_slide()
title_bar(s, "Cálculo", "Ecuación normal paso a paso (1/2)", num="6")
footer(s)
txt(s, Inches(0.7), Inches(1.3), Inches(11.5), Inches(0.4), [["MATRIZ DE DISEÑO X (10 × 3): columna de unos + X₁ + X₂", 13, True, AZUL_OSCURO]])
txt(s, Inches(0.7), Inches(1.7), Inches(11.5), Inches(0.4), [["XᵀX (3×3)   y   Xᵀy (3×1)  —  valores extraídos de XtX.csv y 02_modelo.py", 12.5, False, GRIS]])
add_table(s, Inches(0.7), Inches(2.15), Inches(3.75), Inches(2.1),
          ["", "1", "X₁", "X₂"],
          [["1", "10,00", "280,53", "173,43"],
           ["X₁", "280,53", "18.399,80", "12.626,60"],
           ["X₂", "173,43", "12.626,60", "8.890,55"]],
          font_size=11.5, row_height=0.30)
add_table(s, Inches(4.65), Inches(2.15), Inches(3.75), Inches(1.35),
          ["Componente", "Valor"],
          [["(Xᵀy)₀ = Σy", "235,0061"],
           ["(Xᵀy)₁ = ΣX₁·y", "16.150,53"],
           ["(Xᵀy)₂ = ΣX₂·y", "11.232,44"]],
          font_size=11.5, row_height=0.30)
txt(s, Inches(0.7), Inches(4.45), Inches(11.5), Inches(0.4), [
    [("det(XᵀX) = 17.073.437,13  (≠ 0 → la matriz es invertible, tiene solución única)", 12.5, True, VERDE)],
], space_after=2)
txt(s, Inches(0.7), Inches(4.9), Inches(11.5), Inches(0.4), [["Paso 2: calcular (XᵀX)⁻¹  →  Paso 3: multiplicar b = (XᵀX)⁻¹·Xᵀy", 13, True, AZUL_MEDIO]])
add_notes(s, "Explicar las tres operaciones: formar X, calcular XᵀX e Xᵀy, verificar determinante distinto de cero. Los números son reales de los archivos CSV.")

# =============================================================================
# DIAPOSITIVA 7 — RESULTADO THETA
# =============================================================================
s = add_slide()
title_bar(s, "Cálculo", "Resultado: coeficientes theta", num="7")
footer(s)
rect(s, Inches(0.7), Inches(1.5), Inches(11.9), Inches(1.5), AZUL_CLARO)
txt(s, Inches(0.95), Inches(1.65), Inches(11.4), Inches(1.25), [
    [("b₀ = 0,3387      b₁ = 0,3988      b₂ = 0,6904", 30, True, AZUL_OSCURO)],
    [("Valores exactos de theta.csv: b₀=0,338684 · b₁=0,398836 · b₂=0,690369", 13, False, GRIS)],
], space_after=5)
rect(s, Inches(0.7), Inches(3.35), Inches(5.7), Inches(3.4), BLANCO, line=AZUL_MEDIO)
txt(s, Inches(0.95), Inches(3.5), Inches(5.2), Inches(0.4), [["ECUACIÓN FINAL APRENDIDA", 14, True, AZUL_OSCURO]])
txt(s, Inches(0.95), Inches(4.0), Inches(5.2), Inches(0.7), [
    [("ŷ = 0,3387 + 0,3988·X₁ + 0,6904·X₂", 22, True, AZUL_OSCURO)],
], space_after=2)
txt(s, Inches(0.95), Inches(4.85), Inches(5.25), Inches(1.8), [
    [("Interpretación operativa:", 12.5, True, NEGRO)],
    [("• Con X₁ = X₂ = 0 → predice 0,34 GWh (intercepto de ajuste).", 12, False, NEGRO)],
    [("• Cada GWh extra de máximo → +0,40 GWh al promedio.", 12, False, NEGRO)],
    [("• Cada GWh extra de mínimo → +0,69 GWh al promedio.", 12, False, NEGRO)],
    [("• b₂ > b₁: el piso sostiene el promedio más que el pico aislado.", 12, False, NEGRO)],
], space_after=4)
rect(s, Inches(6.8), Inches(3.35), Inches(5.8), Inches(3.4), AZUL_CLARO)
txt(s, Inches(7.05), Inches(3.5), Inches(5.3), Inches(0.4), [["MATRIZ (XᵀX)⁻¹ (XtX_inv.csv)", 13, True, AZUL_OSCURO]])
add_table(s, Inches(7.05), Inches(3.95), Inches(5.35), Inches(2.55),
          ["", "c0", "c1", "c2"],
          [["f0", "0,2433", "−0,0178", "0,0206"],
           ["f1", "−0,0178", "0,0034", "−0,0045"],
           ["f2", "0,0206", "−0,0045", "0,0062"]],
          font_size=11.5, row_height=0.32)
add_notes(s, "Mostrar la ecuación final y cómo leerla. b₂ mayor que b₁ tiene sentido físico: el mínimo (piso) sostiene el promedio más que el máximo aislado. Mostrar la inversa como evidencia del cálculo matricial.")

# =============================================================================
# DIAPOSITIVA 8 — GRADIENTE DESCENDENTE
# =============================================================================
s = add_slide()
title_bar(s, "Validación", "Gradiente descendente (método iterativo)", num="8")
footer(s)
txt(s, Inches(0.7), Inches(1.3), Inches(11.5), Inches(0.4), [["VERIFICACIÓN INDEPENDIENTE DE LA ECUACIÓN NORMAL", 13, True, AZUL_OSCURO]])
bullets(s, Inches(0.7), Inches(1.75), Inches(5.9), Inches(5.0), [
    ("Estandarización de X₁ y X₂ (media 0, desv. 1).", 0),
    ("Inicialización b = (0,0,0) · tasa de aprendizaje α = 0,1.", 0),
    ("2.000 iteraciones con J(b) = (1/2m)·Σe².", 0),
    ("Costo inicial J = 713,88 → costo final J = 0,1038.", 0),
    ("Converge a partir de la iteración ~500 (cambios < 0,01).", 0),
    ("Vuelto a escala original: b₀=0,3210 · b₁=0,4025 · b₂=0,6855.", 0),
    ("Diferencia vs ecuación normal < 0,018 → valida el cálculo exacto.", 0),
], size=13.5, space_after=7)
try:
    pic(s, f"{CARPETA}/fig_convergencia.png", Inches(6.85), Inches(2.05), w=Inches(5.9))
except Exception as e:
    rect(s, Inches(6.85), Inches(2.05), Inches(5.9), Inches(4.2), RGBColor(0xEE, 0xEE, 0xEE))
    txt(s, Inches(6.85), Inches(4.0), Inches(5.9), Inches(1.5), [[("Figura convergencia no embebida", 12, False, GRIS)]])
txt(s, Inches(6.85), Inches(6.45), Inches(5.9), Inches(0.6), [[("Figura 1. Costo J vs. iteración (α = 0,1).", 10, False, GRIS, True)]])
add_notes(s, "El gradiente descendente es un método separado que confirma la ecuación normal. El coste cae de 713,88 a 0,1038 y los coeficientes en escala original coinciden dentro de 0,018. La convergencia es lenta por la alta correlación entre predictores.")

# =============================================================================
# DIAPOSITIVA 9 — MÉTRICAS
# =============================================================================
s = add_slide()
title_bar(s, "Evaluación", "Métricas de error y ajuste", num="9")
footer(s)
add_table(s, Inches(0.7), Inches(1.45), Inches(7.35), Inches(4.2),
          ["Métrica", "Valor", "Interpretación"],
          [["SSE = Σe²", "2,0719", "Suma de errores al cuadrado"],
           ["MSE = SSE/m", "0,2072", "Error cuadrado medio"],
           ["RMSE = √MSE", "0,4552 GWh", "≈ 1,9 % de la media de Y"],
           ["MAE = Σ|e|/m", "0,3833 GWh", "Error absoluto medio"],
           ["SST = Σ(y−ȳ)²", "8.754,82", "Varianza total de Y"],
           ["R² = 1 − SSE/SST", "0,999763 (99,98 %)", "Varianza explicada"],
           ["R² ajustado", "0,999696", "Ajustado por n y p"]],
          font_size=12, row_height=0.48,
          col_widths=[2.2, 1.9, 3.2],
          highlight_rows=[5],
          highlight_fill=RGBColor(0xE2, 0xEF, 0xDA))
txt(s, Inches(0.7), Inches(5.9), Inches(7.35), Inches(1.0), [
    [("Errores registro por registro (tabla_metricas.csv): máx |e| = 0,9708 (Combustóleo), mín |e| = 0,0064 (Jet-A1).", 11, False, GRIS)],
], space_after=2)
rect(s, Inches(8.4), Inches(1.5), Inches(4.25), Inches(5.35), AZUL_CLARO)
txt(s, Inches(8.65), Inches(1.68), Inches(3.8), Inches(0.4), [["LECTURA RÁPIDA", 13, True, AZUL_OSCURO]])
bullets(s, Inches(8.65), Inches(2.1), Inches(3.8), Inches(4.6), [
    ("R² ≈ 1 → max+mín explican casi toda la varianza del promedio en la muestra.", 0),
    ("RMSE de 0,46 GWh es muy pequeño frente a Ȳ = 23,5 GWh.", 0),
    ("Ajuste casi perfecto en entrenamiento (n = 10).", 0),
    ("Cuidado: R² puede estar inflado por muestra pequeña.", 0),
], size=12.5, space_after=8)
add_notes(s, "Resaltar R² = 99,98 % y RMSE = 0,455 GWh (solo 1,9 % de la media). Advertir que con n=10 el R² de entrenamiento está inflado y hay que ser cauteloso al generalizar.")

# =============================================================================
# DIAPOSITIVA 10 — PREDICCIÓN EJEMPLO
# =============================================================================
s = add_slide()
title_bar(s, "Aplicación", "Predicción para un dato nuevo", num="10")
footer(s)
rect(s, Inches(0.7), Inches(1.5), Inches(5.9), Inches(2.6), AZUL_CLARO)
txt(s, Inches(0.95), Inches(1.65), Inches(5.4), Inches(0.4), [["DATO DE PRUEBA (no visto en entrenamiento)", 13, True, AZUL_OSCURO]])
txt(s, Inches(0.95), Inches(2.15), Inches(5.4), Inches(0.4), [
    [("Máximo X₁ = 20,0 GWh", 15, True, NEGRO)],
    [("Mínimo X₂ = 10,0 GWh", 15, True, NEGRO)],
], space_after=5)
rect(s, Inches(0.95), Inches(2.7), Inches(5.4), Inches(1.25), BLANCO, line=AZUL_MEDIO)
txt(s, Inches(1.1), Inches(2.82), Inches(5.1), Inches(1.0), [
    [("ŷ = 0,338684 + 0,398836×20,0 + 0,690369×10,0", 14, True, AZUL_OSCURO)],
    [("= 15,2191 GWh", 16, True, VERDE)],
], space_after=2)
txt(s, Inches(0.7), Inches(4.35), Inches(5.9), Inches(0.4), [["INTERVALO ORIENTATIVO ± RMSE", 13, True, AZUL_OSCURO]])
txt(s, Inches(0.95), Inches(4.75), Inches(5.4), Inches(0.7), [
    [("[14,7639 ; 15,6743] GWh", 15, True, AZUL_OSCURO)],
    [("Plausible: queda entre el mínimo (10) y el máximo (20).", 10.5, False, GRIS, True)],
], space_after=2)
try:
    pic(s, f"{CARPETA}/fig_real_vs_pred.png", Inches(6.95), Inches(1.75), w=Inches(5.8))
except Exception as e:
    rect(s, Inches(6.95), Inches(1.75), Inches(5.8), Inches(4.6), RGBColor(0xEE, 0xEE, 0xEE))
    txt(s, Inches(6.95), Inches(3.9), Inches(5.8), Inches(1.5), [[("Figura real-vs-pred no embebida", 12, False, GRIS)]])
txt(s, Inches(6.95), Inches(6.55), Inches(5.8), Inches(0.5), [[("Figura 2. Real vs. predicho: puntos sobre la diagonal.", 10, False, GRIS, True)]])
add_notes(s, "Hacer la sustitución en vivo: ŷ = 15,22 GWh. El intervalo ±RMSE da una idea de incertidumbre. El valor es plausible porque está entre 10 y 20. Mostrar la figura de dispersión alineada en la diagonal.")

# =============================================================================
# DIAPOSITIVA 11 — LIMITACIONES
# =============================================================================
s = add_slide()
title_bar(s, "Análisis crítico", "Limitaciones y advertencias", num="11")
footer(s)
bullets(s, Inches(0.7), Inches(1.45), Inches(11.9), Inches(2.6), [
    ("Muestra muy pequeña: n = 10 → el modelo memoriza la muestra; no se puede generalizar a las 2.786 filas sin más datos.", 0),
    ("Multicolinealidad alta: X₁ y X₂ correlacionados (r = 0,986) → los coeficientes b₁ y b₂ son sensibles a pequeños cambios, aunque el pronóstico siga siendo bueno.", 0),
    ("R² de entrenamiento inflado (0,9998): excelente para interpolar dentro de 0–103 GWh, pero no extrapolar a fuentes o años no representados.", 0),
], size=15, space_after=10)
rect(s, Inches(0.7), Inches(4.35), Inches(11.9), Inches(2.5), RGBColor(0xFD, 0xF2, 0xD9), line=AMARILLO)
txt(s, Inches(0.95), Inches(4.5), Inches(11.4), Inches(0.4), [["¿QUÉ PASARÍA SI…?", 14, True, RGBColor(0xB0, 0x7A, 0x1E)]])
bullets(s, Inches(0.95), Inches(4.95), Inches(11.4), Inches(1.8), [
    ("Forzar b₀ = 0 → el SSE se triplica (pierde ajuste fino en valores bajos como BAGAZO/JET-A1).", 0),
    ("Eliminar X₂ → el R² cae (el mínimo aporta información independiente del pico).", 0),
    ("La inversa de XᵀX tiene entradas grandes y opuestas (−0,0045 / +0,0062) que se compensan → inestabilidad numérica.", 0),
], size=13.5, space_after=6)
add_notes(s, "Esta diapositiva es clave para el jurado. Ser honesto: n pequeño, colinealidad r=0,986, R² inflado. Recomendar no extrapolar. Las preguntas 'qué pasaría si' muestran comprensión profunda del modelo.")

# =============================================================================
# DIAPOSITIVA 12 — CONCLUSIONES
# =============================================================================
s = add_slide()
title_bar(s, "Cierre", "Conclusiones y reproducibilidad", num="12")
footer(s)
txt(s, Inches(0.7), Inches(1.35), Inches(11.5), Inches(0.4), [["CONCLUSIONES", 14, True, AZUL_OSCURO]])
bullets(s, Inches(0.7), Inches(1.8), Inches(5.9), Inches(4.9), [
    ("Ventaja: ecuación explícita, auditable y barata (invertir 3×3 es milisegundos). Cada coeficiente tiene lectura operativa para planeación energética.", 0),
    ("Valor pedagógico: el cálculo manual enseña qué optimiza la máquina; el valor productivo está en automatizarlo (NumPy).", 0),
    ("Para operación real: reentrenar con las 2.786 filas, añadir estacionalidad (mes) y reportar intervalos, no solo puntos.", 0),
], size=13.5, space_after=9)
rect(s, Inches(6.95), Inches(1.5), Inches(5.65), Inches(4.9), AZUL_CLARO)
txt(s, Inches(7.2), Inches(1.65), Inches(5.2), Inches(0.4), [["REPRODUCIBILIDAD", 13, True, AZUL_OSCURO]])
bullets(s, Inches(7.2), Inches(2.1), Inches(5.2), Inches(4.2), [
    ("01_descargar.py → descarga y limpia datos (datos_completos.csv)", 0),
    ("02_modelo.py → ecuación normal, gradiente, métricas, figuras", 0),
    ("03_informe.py → genera el DOCX formal automáticamente", 0),
    ("CSV intermedios: XtX.csv, XtX_inv.csv, theta.csv, tabla_metricas.csv, gradiente_iters.csv", 0),
    ("Entregable: Informe_Regresion_Lineal_Multiple.docx", 0),
    ("Entorno: venv (dependencias de Python)", 0),
], size=12.5, space_after=8)
add_notes(s, "Cierre: ventajas del modelo, recomendación para operación real (más datos, estacionalidad, intervalos) y cómo se reproduce todo con los tres scripts más el informe DOCX.")

# -----------------------------------------------------------------------------
# Guardar
# -----------------------------------------------------------------------------
OUT = f"{CARPETA}/Presentacion_Regresion_Lineal_Multiple.pptx"
prs.save(OUT)
print("Guardado:", OUT)
print("Diapositivas:", len(prs.slides.__iter__.__self__._sldIdLst))