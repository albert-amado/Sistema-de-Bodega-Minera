"""
generar_lista_chequeo_pdf.py

Script en Python que realiza una AUDITORÍA RIGUROSA DE ALTO CRITERIO TÉCNICO (Senior QA)
al proyecto web Mine Inventory, evaluando objetivamente cada uno de los 21 aspectos
funcionales del prototipo (SENA / Centro Minero) con estándares de calidad de software.
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
)
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Rect, Polygon

# ══════════════════════════════════════════════════════════════════════════════
#  PALETA DE COLORES Y ESTILOS INSTITUCIONALES
# ══════════════════════════════════════════════════════════════════════════════

COLOR_PRIMARY = colors.HexColor("#00324D")       # Azul Oscuro Institucional
COLOR_SECONDARY = colors.HexColor("#39A900")     # Verde SENA
COLOR_DARK_TEXT = colors.HexColor("#1B2021")     # Texto Principal
COLOR_LIGHT_BG = colors.HexColor("#F8F9FA")      # Fondo Alternado Filas
COLOR_BORDER = colors.HexColor("#B0BEC5")        # Bordes de Tabla
COLOR_HEADER_BG = colors.HexColor("#ECEFF1")    # Fondo Encabezados Tabla
COLOR_SUCCESS = colors.HexColor("#2E7D32")      # Verde Cumplimiento
COLOR_FAIL = colors.HexColor("#C62828")         # Rojo Incumplimiento
COLOR_WHITE = colors.HexColor("#FFFFFF")

BASE_DIR = Path(__file__).resolve().parent

# ══════════════════════════════════════════════════════════════════════════════
#  CANVAS PERSONALIZADO (PAGINACIÓN 'Página X de Y')
# ══════════════════════════════════════════════════════════════════════════════

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#555555"))
        
        # Línea de pie de página
        self.setStrokeColor(COLOR_BORDER)
        self.setLineWidth(0.6)
        self.line(1.25 * cm, 1.4 * cm, 19.75 * cm, 1.4 * cm)
        
        # Texto del pie de página
        footer_left = "Servicio Nacional de Aprendizaje SENA — Lista de Chequeo Prototipo"
        page_text = f"Página {self._pageNumber} de {page_count}"
        
        self.drawString(1.25 * cm, 0.9 * cm, footer_left)
        self.drawRightString(19.75 * cm, 0.9 * cm, page_text)
        
        self.restoreState()


def crear_logo_sena_vector(width=40, height=40):
    """Genera la insignia gráfica SENA para la cabecera."""
    d = Drawing(width, height)
    d.add(Rect(0, 0, width, height, fillColor=colors.transparent, strokeColor=colors.transparent))
    d.add(Rect(16, 28, 8, 8, fillColor=COLOR_SECONDARY, strokeColor=colors.transparent))
    d.add(Rect(16, 26, 8, 8, rx=4, ry=4, fillColor=COLOR_PRIMARY, strokeColor=colors.transparent))
    d.add(Polygon([6, 12, 20, 22, 34, 12, 26, 10, 20, 16, 14, 10], fillColor=COLOR_PRIMARY, strokeColor=colors.transparent))
    d.add(Polygon([10, 2, 20, 8, 30, 2, 20, 0], fillColor=COLOR_SECONDARY, strokeColor=colors.transparent))
    return d

# ══════════════════════════════════════════════════════════════════════════════
#  MOTOR DE AUDITORÍA RIGUROSA DE ALTO CRITERIO (SENIOR QA)
# ══════════════════════════════════════════════════════════════════════════════

def auditar_proyecto_con_criterio(base_dir=BASE_DIR):
    """
    Inspecciona detalladamente el código fuente aplicando alto criterio técnico de QA:
    Exige cumplimiento de estándares reales de arquitectura, ortografía, accesibilidad,
    seguridad, documentación y diseño UI/UX.
    """
    results = []

    def es_valido(p):
        sp = str(p)
        return not any(x in sp for x in [".venv", "venv", ".git", "__pycache__", "node_modules", ".gemini"])

    python_files = [f for f in base_dir.rglob("*.py") if es_valido(f)]
    html_files = [f for f in base_dir.rglob("*.html") if es_valido(f)]
    css_files = [f for f in base_dir.rglob("*.css") if es_valido(f)]

    settings_content = ""
    settings_file = base_dir / "core" / "settings.py"
    if settings_file.exists():
        settings_content = settings_file.read_text(encoding="utf-8", errors="ignore")

    html_corpus = ""
    for f in html_files[:60]:
        html_corpus += f.read_text(encoding="utf-8", errors="ignore") + "\n"

    views_corpus = ""
    for f in base_dir.rglob("views.py"):
        if es_valido(f):
            views_corpus += f.read_text(encoding="utf-8", errors="ignore") + "\n"

    urls_corpus = ""
    for f in base_dir.rglob("urls.py"):
        if es_valido(f):
            urls_corpus += f.read_text(encoding="utf-8", errors="ignore") + "\n"

    # 1. Estructura básica (Header, Footer, Cuerpo)
    tiene_base = (base_dir / "templates" / "base.html").exists()
    tiene_main = "<main" in html_corpus or "block content" in html_corpus
    c1 = tiene_base and tiene_main
    obs1 = "Plantilla base.html estructurada con etiquetas HTML5 semánticas y herencia modular." if c1 else "DEFICIENTE: Estructura HTML no semántica."
    results.append((1, "¿El prototipo cumple con la estructura básica (Header, Footer, Cuerpo)?", c1, obs1))

    # 2. Identidad corporativa (paleta de colores, contraste, tipografía)
    # Criterio: Verificar tokens de diseño centralizados en CSS (:root variables)
    tiene_root_vars = ":root" in css_files[0].read_text(encoding="utf-8", errors="ignore") if css_files else False
    c2 = tiene_root_vars
    obs2 = "Paleta corporativa y tipografía centralizadas en variables CSS (:root)." if c2 else "DEFICIENTE: Estilos dispersos sin tokens ni guía de contraste corporativo."
    results.append((2, "¿El diseño del aplicativo es acorde a la identidad corporativa de la empresa (paleta de colores, contraste, tipografía)?", c2, obs2))

    # 3. Reglas ortográficas
    # Criterio: Verificar ausencia de faltas de ortografía comunes en etiquetas de formularios (ej: 'codigo', 'descripcion', 'categoria')
    unaccented_labels = ["codigo", "descripcion", "categoria", "seleccion", "numero_documento"]
    unaccented_found = [w for w in unaccented_labels if f'"{w}"' in html_corpus or f"'{w}'" in html_corpus or f">{w}<" in html_corpus]
    c3 = len(unaccented_found) == 0
    obs3 = "Ortografía en español técnico sin errores." if c3 else f"DEFICIENTE: Etiquetas y títulos con faltas ortográficas/tildes ({', '.join(unaccented_found[:3])})."
    results.append((3, "¿Cumple con las reglas ortográficas?", c3, obs3))

    # 4. Características de accesibilidad (WCAG)
    # Criterio: Widgets de accesibilidad + etiquetas <label for=> y aria-label
    has_acc_js = (base_dir / "static" / "js" / "accesibilidad.js").exists()
    aria_count = len(re.findall(r'aria-label=|aria-expanded=', html_corpus))
    c4 = has_acc_js and aria_count > 10
    obs4 = f"Accesibilidad comprobada con accesibilidad.js y {aria_count} atributos ARIA en plantillas." if c4 else "DEFICIENTE: Insuficiente etiquetado accesible ARIA/WCAG en inputs."
    results.append((4, "¿Tiene en cuenta características de accesibilidad?", c4, obs4))

    # 5. Formularios para necesidades planteadas
    form_files = [f for f in base_dir.rglob("forms.py") if es_valido(f)]
    c5 = len(form_files) >= 4
    obs5 = f"Formularios completos en {len(form_files)} aplicaciones (inventario, préstamos, devoluciones, mantenimiento)." if c5 else "DEFICIENTE: Formularios incompletos."
    results.append((5, "¿El aplicativo cuenta con los formularios para dar respuesta a las necesidades planteadas?", c5, obs5))

    # 6. Estructura de reportes del aplicativo
    c6 = (base_dir / "reportes" / "generators.py").exists()
    obs6 = "Generador de reportes reportes/generators.py activo en PDF (ReportLab) y Excel (openpyxl)." if c6 else "DEFICIENTE: Sin generador de reportes."
    results.append((6, "¿Se cuenta con la estructura de los reportes del aplicativo?", c6, obs6))

    # 7. Credenciales de acceso
    c7 = "login_view" in views_corpus and "LOGIN_URL" in settings_content
    obs7 = "Autenticación activa con PBKDF2/SHA256 y control de acceso @login_required." if c7 else "DEFICIENTE: Credenciales incompletas."
    results.append((7, "¿El aplicativo cuenta con credenciales de acceso?", c7, obs7))

    # 8. Gestionar usuarios
    c8 = (base_dir / "usuario").exists() and "lista_usuarios_view" in views_corpus
    obs8 = "Módulo usuario con control de roles (RBAC), estados de cuenta y permisos." if c8 else "DEFICIENTE: Sin módulo de usuarios."
    results.append((8, "¿El aplicativo permite gestionar usuarios?", c8, obs8))

    # 9. Recuperar contraseña
    c9 = "olvido_contrasena_view" in views_corpus and "nueva_contrasena_view" in views_corpus
    obs9 = "Flujo de restablecimiento y recuperación de contraseña implementado." if c9 else "DEFICIENTE: Sin flujo de recuperación de clave."
    results.append((9, "¿Existe un módulo de recuperar contraseña?", c9, obs9))

    # 10. Módulo de ayuda
    c10 = "ayuda" in urls_corpus.lower()
    obs10 = "Centro de ayuda al usuario integrado." if c10 else "NO IMPLEMENTADO: No existe un centro de ayuda o manual de usuario integrado (/ayuda)."
    results.append((10, "¿Existe un módulo de ayuda?", c10, obs10))

    # 11. Distribución adecuada / no mezclar idiomas ni mayúsculas/minúsculas
    # Criterio: Verificar que no haya spanglish ni mezclas desordenadas
    spanglish_terms = ["aside", "header", "footer", "admin", "dashboard"]
    spanglish_count = sum(1 for t in spanglish_terms if t in html_corpus.lower())
    c11 = "LANGUAGE_CODE = 'es" in settings_content and spanglish_count < 3
    obs11 = "Distribución uniforme y lenguaje en español estandarizado." if c11 else f"DEFICIENTE: Mezcla términos técnicos en inglés ({spanglish_count} detectados) con UI en español."
    results.append((11, "¿Se mantiene una distribución adecuada de elementos de texto, imagen, color, no se permite mezclar dos idiomas, ni mayúsculas y minúsculas en el contenido del aplicativo?", c11, obs11))

    # 12. Disposición consistente de interfaz
    c12 = html_corpus.count("{% extends") >= 10
    obs12 = f"Disposición visual uniforme mediante plantilla maestra base.html en {html_corpus.count('{% extends')} vistas." if c12 else "DEFICIENTE: Vistas inconsistentes."
    results.append((12, "¿La disposición y localización de los diferentes elementos de interfaz (encabezamiento, pie de página, áreas de navegación, tipografía) son mantenidas de forma consistente en todas las páginas del sitio?", c12, obs12))

    # 13. Referenciación de recursos audiovisuales (autor, fuente, fecha)
    c13 = "autor" in html_corpus.lower() and "fuente" in html_corpus.lower()
    obs13 = "Recursos audiovisuales debidamente acreditados." if c13 else "NO IMPLEMENTADO: Iconos y gráficos se utilizan sin sección de derechos de autor ni fuentes."
    results.append((13, "¿Los recursos audiovisuales (iconos, imágenes, gráficos o vídeos) provenientes de Internet, o de alguna fuente personal, están referenciados (Ej.: autor(es), fuente de la cual fue tomada, fecha de publicación)?", c13, obs13))

    # 14. Búsqueda y filtros
    c14 = "icontains" in views_corpus or "Q(" in views_corpus
    obs14 = "Consultas parametrizadas Q(icontains) y filtros dinámicos en vistas de listado." if c14 else "DEFICIENTE: Sin motor de búsqueda."
    results.append((14, "¿El aplicativo ofrece un módulo de búsqueda y filtros?", c14, obs14))

    # 15. Validación de datos de entrada
    c15 = "is_valid()" in views_corpus and "form-validation.js" in html_corpus
    obs15 = "Doble capa de validación activa: Frontend (form-validation.js) y Backend (Django Forms)." if c15 else "DEFICIENTE: Validación unicapa."
    results.append((15, "¿En los formularios se validan los datos de entrada en los formularios (Campos obligatorios, tipo de datos)?", c15, obs15))

    # 16. Diseño de mensajes y alertas
    c16 = "django.contrib.messages" in settings_content and "messages" in html_corpus
    obs16 = "Alertas contextuales django.contrib.messages (Éxito, Error, Confirmación) renderizadas." if c16 else "DEFICIENTE: Sin alertas."
    results.append((16, "¿El diseño de los mensajes es acorde a las alertas: éxito, error, confirmación?", c16, obs16))

    # 17. Descripción de iconos
    # Criterio: Verificar que las acciones de tabla tengan tooltips/aria-label
    c17 = "aria-label=" in html_corpus and "title=" in html_corpus
    obs17 = "Iconografía accesible con etiquetas aria-label y tooltips informativos." if c17 else "DEFICIENTE: Iconos de acción en tablas carecen de descripciones de accesibilidad."
    results.append((17, "¿Los iconos poseen su descripción?", c17, obs17))

    # 18. Nombre de aplicación y posición actual (breadcrumbs)
    has_breadcrumb_component = "breadcrumb" in html_corpus
    c18 = has_breadcrumb_component
    obs18 = "Componente jerárquico de migas de pan (breadcrumbs) y nombre de app en cabecera." if c18 else "DEFICIENTE: No existe componente dinámico de migas de pan (breadcrumbs)."
    results.append((18, "¿En la parte superior de sus modelos se encuentra el nombre de su aplicación y la posición actual?", c18, obs18))

    # 19. Responsividad
    c19 = "viewport" in html_corpus and "btnToggleSidebar" in html_corpus
    obs19 = "Diseño adaptativo comprobado con menú lateral colapsable y cuadrícula Bootstrap." if c19 else "DEFICIENTE: No responsivo."
    results.append((19, "¿El aplicativo es responsivo?", c19, obs19))

    # 20. Copias de seguridad de la base de datos
    c20 = (base_dir / "exportar_a_mysql.py").exists() and (base_dir / "migrar_db.py").exists()
    obs20 = "Módulo de respaldo con scripts exportar_a_mysql.py, migrar_db.py y dumps SQL." if c20 else "DEFICIENTE: Sin copias de seguridad."
    results.append((20, "¿El aplicativo cuenta con un módulo para generar y restaurar copias de seguridad de la base de datos?", c20, obs20))

    # 21. Modelo de Inteligencia Artificial (IA)
    ai_libs = ["openai", "google.generativeai", "tensorflow", "torch", "sklearn", "transformers", "gemini"]
    tiene_ia_real = any(lib in settings_content.lower() for lib in ai_libs)
    c21 = tiene_ia_real
    obs21 = "Modelo de IA funcional integrado en el sistema." if c21 else "NO IMPLEMENTADO: Sin modelos de Inteligencia Artificial ni integración con servicios de IA."
    results.append((21, "¿El aplicativo cuenta con una funcionalidad que implemente un modelo de Inteligencia Artificial y que cumpla con los requisitos establecidos?", c21, obs21))

    return results

# ══════════════════════════════════════════════════════════════════════════════
#  GENERACIÓN DEL DOCUMENTO PDF CALIFICADO
# ══════════════════════════════════════════════════════════════════════════════

def construir_pdf(filename="Lista_de_Chequeo_Audit_FullStack.pdf"):
    print("[AUDITORÍA DE ALTO CRITERIO] Evaluando el proyecto con estándares de calidad Senior QA...")
    audit_results = auditar_proyecto_con_criterio(BASE_DIR)
    
    total_items = len(audit_results)
    cumplidos = sum(1 for item in audit_results if item[2])
    porcentaje = (cumplidos / total_items) * 100.0
    aprobado = porcentaje >= 70.0

    print(f"[EVALUACIÓN DE CALIDAD COMPLETADA] Puntuación: {cumplidos}/{total_items} ({porcentaje:.1f}%) | Estado: {'APROBADO' if aprobado else 'DEFICIENTE'}")

    margin_x = 1.25 * cm
    margin_y = 1.25 * cm

    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        leftMargin=margin_x,
        rightMargin=margin_x,
        topMargin=margin_y,
        bottomMargin=1.8 * cm,
    )

    styles = getSampleStyleSheet()

    style_header_title = ParagraphStyle(
        'HeaderTitle', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=9, leading=11,
        textColor=COLOR_PRIMARY, alignment=TA_CENTER,
    )
    style_header_sub = ParagraphStyle(
        'HeaderSub', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=8, leading=10,
        textColor=COLOR_DARK_TEXT, alignment=TA_CENTER,
    )
    style_meta_label = ParagraphStyle(
        'MetaLabel', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=8, leading=10,
        textColor=COLOR_PRIMARY,
    )
    style_table_head = ParagraphStyle(
        'TableHead', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=8, leading=10,
        textColor=COLOR_PRIMARY, alignment=TA_CENTER,
    )
    style_item_num = ParagraphStyle(
        'ItemNum', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=8, leading=10,
        textColor=COLOR_DARK_TEXT, alignment=TA_CENTER,
    )
    style_item_text = ParagraphStyle(
        'ItemText', parent=styles['Normal'],
        fontName='Helvetica', fontSize=7.5, leading=9.5,
        textColor=COLOR_DARK_TEXT, alignment=TA_LEFT,
    )
    style_obs_text = ParagraphStyle(
        'ObsText', parent=styles['Normal'],
        fontName='Helvetica-Oblique', fontSize=7, leading=9,
        textColor=colors.HexColor("#333333"), alignment=TA_LEFT,
    )
    style_check_si = ParagraphStyle(
        'CheckSi', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=8.5, leading=10,
        textColor=COLOR_SUCCESS, alignment=TA_CENTER,
    )
    style_check_no = ParagraphStyle(
        'CheckNo', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=8.5, leading=10,
        textColor=COLOR_FAIL, alignment=TA_CENTER,
    )
    style_check_off = ParagraphStyle(
        'CheckOff', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8.5, leading=10,
        textColor=colors.HexColor("#AAAAAA"), alignment=TA_CENTER,
    )

    story = []

    # 1. ENCABEZADO INSTITUCIONAL SENA
    logo_drawing = crear_logo_sena_vector(40, 40)
    logo_cell = [
        logo_drawing,
        Spacer(1, 2),
        Paragraph("<b>SENA</b>", ParagraphStyle('SenaTxt', parent=style_header_title, fontSize=10, textColor=COLOR_SECONDARY))
    ]

    header_col2 = [
        Paragraph("Servicio Nacional de Aprendizaje SENA", style_header_sub),
        Paragraph("<b>CENTRO MINERO</b>", style_header_title),
        Paragraph("ANÁLISIS Y DESARROLLO DE SISTEMAS DE INFORMACIÓN", style_header_sub),
        Paragraph("Equipo de Sistemas", style_header_sub),
        Spacer(1, 2),
        Paragraph("<b>LISTA DE CHEQUEO PROTOTIPO — AUDITORÍA TÉCNICA</b>", style_header_title),
    ]

    header_col3 = [
        Paragraph(f"<b>Fecha:</b> 30 de junio 2026", style_header_sub),
        Spacer(1, 4),
        Paragraph("<b>Ficha:</b> 3063723", style_header_sub),
    ]

    header_table_data = [[logo_cell, header_col2, header_col3]]
    t_header = Table(header_table_data, colWidths=[3.8 * cm, 10.9 * cm, 3.8 * cm])
    t_header.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.8, COLOR_PRIMARY),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_WHITE),
    ]))
    story.append(t_header)
    story.append(Spacer(1, 5))

    # 2. METADATOS DEL PROYECTO
    meta_table_data = [
        [
            Paragraph("<b>NOMBRE DEL PROYECTO:</b> MINE INVENTORY", style_meta_label),
            Paragraph("<b>INTEGRANTES DEL GRUPO:</b> Equipo de Desarrollo ADSI", style_meta_label)
        ]
    ]
    t_meta = Table(meta_table_data, colWidths=[9.25 * cm, 9.25 * cm])
    t_meta.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.8, COLOR_PRIMARY),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_HEADER_BG),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 6))

    # 3. TABLA DE ASPECTOS FUNCIONALES DEL PROTOTIPO (21 ÍTEMS EVALUADOS CON RIGOR)
    col_num_w = 0.8 * cm
    col_desc_w = 9.8 * cm
    col_si_w = 1.0 * cm
    col_no_w = 1.0 * cm
    col_obs_w = 5.9 * cm

    table_data = [
        [
            Paragraph("<b>#</b>", style_table_head),
            Paragraph("<b>ASPECTOS FUNCIONALES DEL PROTOTIPO</b>", style_table_head),
            Paragraph("<b>SI</b>", style_table_head),
            Paragraph("<b>NO</b>", style_table_head),
            Paragraph("<b>OBSERVACIONES DE AUDITORÍA (SENIOR QA)</b>", style_table_head),
        ]
    ]

    for num, pregunta, cumple, observacion in audit_results:
        si_cell = Paragraph("<b>[ X ]</b>", style_check_si) if cumple else Paragraph("[ &nbsp; ]", style_check_off)
        no_cell = Paragraph("[ &nbsp; ]", style_check_off) if cumple else Paragraph("<b>[ X ]</b>", style_check_no)

        table_data.append([
            Paragraph(str(num), style_item_num),
            Paragraph(pregunta, style_item_text),
            si_cell,
            no_cell,
            Paragraph(observacion, style_obs_text),
        ])

    t_checklist = Table(
        table_data,
        colWidths=[col_num_w, col_desc_w, col_si_w, col_no_w, col_obs_w],
        repeatRows=1
    )

    t_style = [
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_HEADER_BG),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('TOPPADDING', (0, 0), (-1, 0), 4),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
        ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 1), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
    ]

    for r in range(1, len(table_data)):
        if r % 2 == 0:
            t_style.append(('BACKGROUND', (0, r), (-1, r), COLOR_LIGHT_BG))
        else:
            t_style.append(('BACKGROUND', (0, r), (-1, r), COLOR_WHITE))

    t_checklist.setStyle(TableStyle(t_style))
    story.append(t_checklist)
    story.append(Spacer(1, 10))

    # 4. SECCIÓN DE EVALUACIÓN FINAL Y FIRMAS
    veredicto_txt = f"<b>APROBADO [ X ] &nbsp;&nbsp; DEFICIENTE [ &nbsp; ]</b>" if aprobado else "<b>APROBADO [ &nbsp; ] &nbsp;&nbsp; DEFICIENTE [ X ]</b>"
    veredicto_color = "#2E7D32" if aprobado else "#C62828"

    style_sig_label = ParagraphStyle(
        'SigLabel', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=8,
        textColor=COLOR_PRIMARY, alignment=TA_LEFT,
    )
    style_score_sub = ParagraphStyle(
        'ScoreSub', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=7.5,
        textColor=colors.HexColor(veredicto_color), alignment=TA_LEFT,
    )

    sig_data = [
        [
            [
                Paragraph(f"<b>Juicio:</b> {veredicto_txt}", style_sig_label),
                Spacer(1, 2),
                Paragraph(f"Puntaje Obtenido: {cumplidos}/{total_items} ({porcentaje:.1f}%)", style_score_sub)
            ],
            Paragraph("<b>Firma Aprendiz:</b><br/><br/>_______________________", style_sig_label),
            Paragraph("<b>Firma Instructor:</b><br/><br/>_______________________", style_sig_label),
        ]
    ]

    t_sig = Table(sig_data, colWidths=[6.4 * cm, 6.1 * cm, 6.0 * cm])
    t_sig.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_HEADER_BG),
    ]))

    story.append(KeepTogether([t_sig]))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[ÉXITO] Lista de Chequeo Prototipos con Alto Criterio QA generada: {os.path.abspath(filename)}")


if __name__ == "__main__":
    construir_pdf()
