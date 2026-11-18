"""
excel_backup.py - Exportación e importación incremental ("subir lo que falte")
de copias de seguridad en formato Excel (.xlsx) para el Sistema de Bodega Minera.

No requiere librerías externas adicionales: construye y lee archivos OpenXML (.xlsx)
estándar compatibles con Microsoft Excel, LibreOffice Calc y Google Sheets.
"""
from __future__ import annotations

import datetime
import io
import logging
import re
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

from django.conf import settings
from django.core.management.color import no_style
from django.db import connection, transaction

from almacen.models import Almacen, Estante
from herramienta.models import (
    BitacoraEstado,
    CategoriaHerramienta,
    DetalleMantenimiento,
    DetalleTraslado,
    Herramienta,
    Mantenimiento,
    Proveedor,
    Suministro,
    Traslado,
)
from prestamo.models import DetallePrestamo, DevolucionHerramienta, Prestamo
from usuario.models import Usuario

logger = logging.getLogger(__name__)

NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"


# ─────────────────────────────────────────────────────────────
#  Utilidades para lectura y escritura de archivos .xlsx
# ─────────────────────────────────────────────────────────────
def _col_letter(idx_zero_based: int) -> str:
    """Convierte índice base 0 (0 -> A, 25 -> Z, 26 -> AA) a letra de columna Excel."""
    result = []
    n = idx_zero_based + 1
    while n > 0:
        n, rem = divmod(n - 1, 26)
        result.append(chr(65 + rem))
    return "".join(reversed(result))


def _col_index(col_str: str) -> int:
    """Convierte letra de columna Excel ('A' -> 0, 'AA' -> 26) a índice base 0."""
    idx = 0
    for ch in col_str.upper():
        if "A" <= ch <= "Z":
            idx = idx * 26 + (ord(ch) - 64)
    return idx - 1


def _clean_xml_text(val: Any) -> str:
    """Convierte cualquier valor a texto seguro para XML 1.0."""
    if val is None:
        return ""
    if isinstance(val, bool):
        return "TRUE" if val else "FALSE"
    if isinstance(val, datetime.datetime):
        if val.tzinfo is not None:
            val = val.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        return val.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(val, datetime.date):
        return val.strftime("%Y-%m-%d")
    s = str(val)
    # Eliminar caracteres de control inválidos en XML 1.0
    s = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", s)
    return s


def _build_worksheet_xml(headers: list[str], rows: list[list[Any]]) -> bytes:
    """Construye el XML de una hoja de cálculo Excel con cabeceras estilizadas."""
    out = io.StringIO()
    out.write('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n')
    out.write(
        f'<worksheet xmlns="{NS_MAIN}" '
        f'xmlns:r="{NS_REL}">'
    )

    # Ancho automático aproximado de columnas
    out.write("<cols>")
    for c_idx, h in enumerate(headers):
        max_len = len(str(h))
        for r in rows[:200]:
            if c_idx < len(r) and r[c_idx] is not None:
                max_len = max(max_len, len(str(r[c_idx])))
        width = min(max(max_len + 4, 12), 48)
        col_num = c_idx + 1
        out.write(f'<col min="{col_num}" max="{col_num}" width="{width}" customWidth="1"/>')
    out.write("</cols>")

    out.write("<sheetData>")

    # Fila 1: Cabeceras (estilo s="1")
    out.write('<row r="1" ht="22" customHeight="1">')
    for c_idx, h in enumerate(headers):
        ref = f"{_col_letter(c_idx)}1"
        text = escape(_clean_xml_text(h))
        out.write(f'<c r="{ref}" s="1" t="inlineStr"><is><t>{text}</t></is></c>')
    out.write("</row>")

    # Filas de datos (estilo s="2")
    for r_idx, row in enumerate(rows, start=2):
        out.write(f'<row r="{r_idx}">')
        for c_idx, val in enumerate(row):
            ref = f"{_col_letter(c_idx)}{r_idx}"
            if val is None or val == "":
                out.write(f'<c r="{ref}" s="2"/>')
            elif isinstance(val, bool):
                num_val = "1" if val else "0"
                out.write(f'<c r="{ref}" s="2" t="b"><v>{num_val}</v></c>')
            elif isinstance(val, (int, float)) and not isinstance(val, bool):
                out.write(f'<c r="{ref}" s="2" t="n"><v>{val}</v></c>')
            else:
                text = escape(_clean_xml_text(val))
                out.write(f'<c r="{ref}" s="2" t="inlineStr"><is><t xml:space="preserve">{text}</t></is></c>')
        out.write("</row>")

    out.write("</sheetData>")
    out.write("</worksheet>")
    return out.getvalue().encode("utf-8")


def build_xlsx_bytes(sheets: list[tuple[str, list[str], list[list[Any]]]]) -> bytes:
    """
    Recibe una lista de tuplas (sheet_name, headers, rows) y genera un archivo .xlsx en memoria.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # 1. [Content_Types].xml
        ct_parts = [
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
            '<Default Extension="xml" ContentType="application/xml"/>',
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
            '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
        ]
        for i in range(1, len(sheets) + 1):
            ct_parts.append(
                f'<Override PartName="/xl/worksheets/sheet{i}.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            )
        ct_parts.append("</Types>")
        zf.writestr("[Content_Types].xml", "".join(ct_parts))

        # 2. _rels/.rels
        rels_root = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<Relationships xmlns="{NS_PKG_REL}">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="xl/workbook.xml"/>'
            "</Relationships>"
        )
        zf.writestr("_rels/.rels", rels_root)

        # 3. xl/workbook.xml y xl/_rels/workbook.xml.rels
        wb_parts = [
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            f'<workbook xmlns="{NS_MAIN}" xmlns:r="{NS_REL}"><sheets>',
        ]
        wb_rels = [
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            f'<Relationships xmlns="{NS_PKG_REL}">',
        ]
        for i, (name, _, _) in enumerate(sheets, start=1):
            safe_name = escape(name[:31])
            wb_parts.append(f'<sheet name="{safe_name}" sheetId="{i}" r:id="rId{i}"/>')
            wb_rels.append(
                f'<Relationship Id="rId{i}" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
                f'Target="worksheets/sheet{i}.xml"/>'
            )
        wb_parts.append("</sheets></workbook>")
        wb_rels.append(
            f'<Relationship Id="rId{len(sheets) + 1}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
            'Target="styles.xml"/>'
            "</Relationships>"
        )
        zf.writestr("xl/workbook.xml", "".join(wb_parts))
        zf.writestr("xl/_rels/workbook.xml.rels", "".join(wb_rels))

        # 4. xl/styles.xml (Cabecera verde institucional #39A900 con texto blanco #FFFFFF)
        styles_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<styleSheet xmlns="{NS_MAIN}">'
            '<fonts count="2">'
            '<font><sz val="10"/><color rgb="FF1E1E1E"/><name val="Calibri"/></font>'
            '<font><b/><sz val="10"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font>'
            '</fonts>'
            '<fills count="3">'
            '<fill><patternFill patternType="none"/></fill>'
            '<fill><patternFill patternType="gray125"/></fill>'
            '<fill><patternFill patternType="solid"><fgColor rgb="FF39A900"/><bgColor indexed="64"/></patternFill></fill>'
            '</fills>'
            '<borders count="2">'
            '<border><left/><right/><top/><bottom/><diagonal/></border>'
            '<border>'
            '<left style="thin"><color rgb="FFD1D5DB"/></left>'
            '<right style="thin"><color rgb="FFD1D5DB"/></right>'
            '<top style="thin"><color rgb="FFD1D5DB"/></top>'
            '<bottom style="thin"><color rgb="FFD1D5DB"/></bottom>'
            '<diagonal/>'
            '</border>'
            '</borders>'
            '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
            '<cellXfs count="3">'
            '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
            '<xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1">'
            '<alignment vertical="center"/>'
            '</xf>'
            '<xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1">'
            '<alignment vertical="center"/>'
            '</xf>'
            '</cellXfs>'
            '</styleSheet>'
        )
        zf.writestr("xl/styles.xml", styles_xml)

        # 5. Hojas xl/worksheets/sheet{i}.xml
        for i, (_, headers, rows) in enumerate(sheets, start=1):
            zf.writestr(f"xl/worksheets/sheet{i}.xml", _build_worksheet_xml(headers, rows))

    return buf.getvalue()


def parse_xlsx_file(file_obj_or_bytes: Any) -> dict[str, list[dict[str, Any]]]:
    """
    Lee cualquier archivo .xlsx (generado por el sistema o guardado desde Microsoft Excel)
    y devuelve un diccionario: {nombre_hoja: [{columna: valor, ...}, ...]}.
    """
    if isinstance(file_obj_or_bytes, (bytes, bytearray)):
        stream = io.BytesIO(file_obj_or_bytes)
    elif isinstance(file_obj_or_bytes, (str, Path)):
        stream = open(file_obj_or_bytes, "rb")  # noqa: SIM115
    else:
        file_obj_or_bytes.seek(0)
        stream = io.BytesIO(file_obj_or_bytes.read())

    result: dict[str, list[dict[str, Any]]] = {}

    with zipfile.ZipFile(stream, "r") as zf:
        namelist = set(zf.namelist())

        # 1. Leer sharedStrings.xml si existe (usado por Excel al guardar)
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in namelist:
            ss_root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in ss_root.findall(f"{{{NS_MAIN}}}si"):
                parts = [t.text or "" for t in si.iter(f"{{{NS_MAIN}}}t")]
                shared_strings.append("".join(parts))

        # 2. Mapear rId -> ruta de archivo en xl/_rels/workbook.xml.rels
        rel_map: dict[str, str] = {}
        if "xl/_rels/workbook.xml.rels" in namelist:
            rels_root = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
            for rel in rels_root:
                r_id = rel.attrib.get("Id", "")
                target = rel.attrib.get("Target", "").lstrip("/")
                if not target.startswith("xl/"):
                    target = f"xl/{target}"
                rel_map[r_id] = target

        # 3. Leer hojas desde xl/workbook.xml
        wb_root = ET.fromstring(zf.read("xl/workbook.xml"))
        sheets_el = wb_root.find(f"{{{NS_MAIN}}}sheets")
        if sheets_el is None:
            return result

        for idx, sheet_el in enumerate(sheets_el, start=1):
            sheet_name = sheet_el.attrib.get("name", f"Sheet{idx}")
            r_id = sheet_el.attrib.get(f"{{{NS_REL}}}id", "")
            sheet_path = rel_map.get(r_id, f"xl/worksheets/sheet{idx}.xml")
            if sheet_path not in namelist:
                continue

            ws_root = ET.fromstring(zf.read(sheet_path))
            sheet_data = ws_root.find(f"{{{NS_MAIN}}}sheetData")
            if sheet_data is None:
                continue

            parsed_rows: list[list[Any]] = []
            for row_el in sheet_data.findall(f"{{{NS_MAIN}}}row"):
                row_cells: dict[int, Any] = {}
                max_col = -1
                for c_el in row_el.findall(f"{{{NS_MAIN}}}c"):
                    ref = c_el.attrib.get("r", "")
                    col_letters = "".join(ch for ch in ref if ch.isalpha())
                    c_idx = _col_index(col_letters) if col_letters else (max_col + 1)
                    max_col = max(max_col, c_idx)

                    c_type = c_el.attrib.get("t", "")
                    v_el = c_el.find(f"{{{NS_MAIN}}}v")
                    is_el = c_el.find(f"{{{NS_MAIN}}}is")

                    val: Any = None
                    if c_type == "s" and v_el is not None and v_el.text is not None:
                        s_idx = int(v_el.text)
                        val = shared_strings[s_idx] if 0 <= s_idx < len(shared_strings) else ""
                    elif c_type == "inlineStr" and is_el is not None:
                        val = "".join(t.text or "" for t in is_el.iter(f"{{{NS_MAIN}}}t"))
                    elif c_type == "b" and v_el is not None and v_el.text is not None:
                        val = v_el.text.strip() in ("1", "TRUE", "true")
                    elif v_el is not None and v_el.text is not None:
                        raw = v_el.text.strip()
                        if c_type in ("str", "e"):
                            val = raw
                        else:
                            # Número entero o decimal
                            try:
                                if "." in raw or "e" in raw.lower():
                                    f_val = float(raw)
                                    val = int(f_val) if f_val.is_integer() else f_val
                                else:
                                    val = int(raw)
                            except ValueError:
                                val = raw
                    row_cells[c_idx] = val

                if max_col >= 0:
                    parsed_rows.append([row_cells.get(i) for i in range(max_col + 1)])

            if not parsed_rows:
                result[sheet_name] = []
                continue

            headers = [
                str(h).strip() if h is not None else f"col_{i}"
                for i, h in enumerate(parsed_rows[0])
            ]
            dict_rows: list[dict[str, Any]] = []
            for data_row in parsed_rows[1:]:
                if all(v is None or str(v).strip() == "" for v in data_row):
                    continue
                row_dict = {}
                for i, h in enumerate(headers):
                    if not h:
                        continue
                    row_dict[h] = data_row[i] if i < len(data_row) else None
                dict_rows.append(row_dict)

            result[sheet_name] = dict_rows

    return result


# ─────────────────────────────────────────────────────────────
#  Definición de tablas para Exportar e Importar
# ─────────────────────────────────────────────────────────────
def obtener_hojas_sistema() -> list[tuple[str, list[str], list[list[Any]]]]:
    """Extrae todos los registros de la base de datos activa en orden de dependencias."""
    sheets: list[tuple[str, list[str], list[list[Any]]]] = []

    # 1. Usuarios
    usuarios_headers = [
        "documento", "tipo_documento", "primer_nombre", "segundo_nombre",
        "primer_apellido", "segundo_apellido", "correo_personal", "telefono",
        "programa", "ficha", "rol", "password", "verificado_sofia_plus",
        "fecha_verificacion", "reset_token", "reset_token_expira",
    ]
    usuarios_rows = [
        [getattr(u, col) for col in usuarios_headers]
        for u in Usuario.objects.all().order_by("documento")
    ]
    sheets.append(("Usuarios", usuarios_headers, usuarios_rows))

    # 2. Almacenes
    almacenes_headers = ["codigo_almacen", "nombre", "dimensiones", "ubicacion"]
    almacenes_rows = [
        [a.codigo_almacen, a.nombre, a.dimensiones, a.ubicacion]
        for a in Almacen.objects.all().order_by("codigo_almacen")
    ]
    sheets.append(("Almacenes", almacenes_headers, almacenes_rows))

    # 3. Estantes
    estantes_headers = ["num_estante", "codigo", "dimensiones", "codigo_almacen_id"]
    estantes_rows = [
        [e.num_estante, e.codigo, e.dimensiones, e.codigo_almacen_id]
        for e in Estante.objects.all().order_by("num_estante")
    ]
    sheets.append(("Estantes", estantes_headers, estantes_rows))

    # 4. Proveedores
    proveedores_headers = [
        "codigo_proveedor", "nit_proveedor", "telefono_contacto",
        "correo_proveedor", "descripcion",
    ]
    proveedores_rows = [
        [p.codigo_proveedor, p.nit_proveedor, p.telefono_contacto, p.correo_proveedor, p.descripcion]
        for p in Proveedor.objects.all().order_by("codigo_proveedor")
    ]
    sheets.append(("Proveedores", proveedores_headers, proveedores_rows))

    # 5. Suministros
    suministros_headers = [
        "codigo_suministro", "codigo_proveedor_id", "fecha", "cantidad", "observaciones",
    ]
    suministros_rows = [
        [s.codigo_suministro, s.codigo_proveedor_id, s.fecha, s.cantidad, s.observaciones]
        for s in Suministro.objects.all().order_by("codigo_suministro")
    ]
    sheets.append(("Suministros", suministros_headers, suministros_rows))

    # 6. Categorías de Herramienta
    categorias_headers = [
        "codigo_categoria", "tipo_herramienta", "nombre_categoria", "descripcion",
    ]
    categorias_rows = [
        [c.codigo_categoria, c.tipo_herramienta, c.nombre_categoria, c.descripcion]
        for c in CategoriaHerramienta.objects.all().order_by("codigo_categoria")
    ]
    sheets.append(("Categorias", categorias_headers, categorias_rows))

    # 7. Herramientas
    herramientas_headers = [
        "codigo_herramienta", "codigo_sku", "nombre_herramienta", "descripcion",
        "disponibilidad", "fecha_ingreso", "codigo_categoria_id",
        "codigo_suministro_id", "estado", "estante_id",
    ]
    herramientas_rows = [
        [
            h.codigo_herramienta, h.codigo_sku, h.nombre_herramienta, h.descripcion,
            h.disponibilidad, h.fecha_ingreso, h.codigo_categoria_id,
            h.codigo_suministro_id, h.estado, h.estante_id,
        ]
        for h in Herramienta.objects.all().order_by("codigo_herramienta")
    ]
    sheets.append(("Herramientas", herramientas_headers, herramientas_rows))

    # 8. Préstamos
    prestamos_headers = [
        "codigo_prestamo", "documento_id", "fecha", "ficha", "estado", "observaciones",
    ]
    prestamos_rows = [
        [p.codigo_prestamo, p.documento_id, p.fecha, p.ficha, p.estado, p.observaciones]
        for p in Prestamo.objects.all().order_by("codigo_prestamo")
    ]
    sheets.append(("Prestamos", prestamos_headers, prestamos_rows))

    # 9. Detalles de Préstamo
    det_prestamo_headers = [
        "numeros_detalle", "codigo_prestamo_id", "codigo_herramienta_id",
        "cantidad", "observaciones",
    ]
    det_prestamo_rows = [
        [d.numeros_detalle, d.codigo_prestamo_id, d.codigo_herramienta_id, d.cantidad, d.observaciones]
        for d in DetallePrestamo.objects.all().order_by("numeros_detalle")
    ]
    sheets.append(("Detalles_Prestamo", det_prestamo_headers, det_prestamo_rows))

    # 10. Devoluciones
    devoluciones_headers = [
        "codigo_devolucion", "codigo_prestamo_id", "codigo_recibe_id",
        "fecha", "observaciones",
    ]
    devoluciones_rows = [
        [dv.codigo_devolucion, dv.codigo_prestamo_id, dv.codigo_recibe_id, dv.fecha, dv.observaciones]
        for dv in DevolucionHerramienta.objects.all().order_by("codigo_devolucion")
    ]
    sheets.append(("Devoluciones", devoluciones_headers, devoluciones_rows))

    # 11. Traslados
    traslados_headers = [
        "codigo_traslado", "fecha_movimiento", "dimensiones",
        "tipo_movimiento", "num_estante_origen_id", "observaciones",
    ]
    traslados_rows = [
        [
            t.codigo_traslado, t.fecha_movimiento, t.dimensiones,
            t.tipo_movimiento, t.num_estante_origen_id, t.observaciones,
        ]
        for t in Traslado.objects.all().order_by("codigo_traslado")
    ]
    sheets.append(("Traslados", traslados_headers, traslados_rows))

    # 12. Detalles de Traslado
    det_traslado_headers = [
        "codigo_detalle", "codigo_traslado_id", "codigo_herramienta_id",
        "cantidad", "observaciones",
    ]
    det_traslado_rows = [
        [dt.codigo_detalle, dt.codigo_traslado_id, dt.codigo_herramienta_id, dt.cantidad, dt.observaciones]
        for dt in DetalleTraslado.objects.all().order_by("codigo_detalle")
    ]
    sheets.append(("Detalles_Traslado", det_traslado_headers, det_traslado_rows))

    # 13. Mantenimientos
    mantenimientos_headers = [
        "num_mantenimiento", "codigo_herramienta_id", "tipo_mantenimiento",
        "fecha_ingreso", "fecha_salida", "descripcion", "observaciones",
    ]
    mantenimientos_rows = [
        [
            m.num_mantenimiento, m.codigo_herramienta_id, m.tipo_mantenimiento,
            m.fecha_ingreso, m.fecha_salida, m.descripcion, m.observaciones,
        ]
        for m in Mantenimiento.objects.all().order_by("num_mantenimiento")
    ]
    sheets.append(("Mantenimientos", mantenimientos_headers, mantenimientos_rows))

    # 14. Detalles de Mantenimiento
    det_mant_headers = [
        "detalle_mantenimiento", "num_mantenimiento_id", "codigo_detalle_traslado_id",
        "accion_realizada", "materiales_usados", "fecha_mantenimiento", "observacion",
    ]
    det_mant_rows = [
        [
            dm.detalle_mantenimiento, dm.num_mantenimiento_id, dm.codigo_detalle_traslado_id,
            dm.accion_realizada, dm.materiales_usados, dm.fecha_mantenimiento, dm.observacion,
        ]
        for dm in DetalleMantenimiento.objects.all().order_by("detalle_mantenimiento")
    ]
    sheets.append(("Detalles_Mantenimiento", det_mant_headers, det_mant_rows))

    # 15. Bitácoras de Estado
    bitacoras_headers = [
        "codigo_bitacora", "num_mantenimiento_id", "codigo_herramienta_id",
        "documento_id", "documento_tecnico", "es_inutilisable",
        "descripcion", "observaciones",
    ]
    bitacoras_rows = [
        [
            b.codigo_bitacora, b.num_mantenimiento_id, b.codigo_herramienta_id,
            b.documento_id, b.documento_tecnico, b.es_inutilisable,
            b.descripcion, b.observaciones,
        ]
        for b in BitacoraEstado.objects.all().order_by("codigo_bitacora")
    ]
    sheets.append(("Bitacoras_Estado", bitacoras_headers, bitacoras_rows))

    return sheets


def exportar_backup_excel(guardar_en_disco: bool = True) -> tuple[bytes, str]:
    """
    Genera el archivo Excel (.xlsx) con toda la copia de seguridad.
    Si guardar_en_disco=True, guarda también una copia en la carpeta backups/.
    Retorna (xlsx_bytes, filename).
    """
    sheets = obtener_hojas_sistema()
    xlsx_bytes = build_xlsx_bytes(sheets)
    sello = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    entorno = "nube" if connection.vendor == "postgresql" else "local"
    filename = f"backup_bodega_minera_{entorno}_{sello}.xlsx"

    if guardar_en_disco:
        try:
            carpeta = Path(settings.BASE_DIR) / "backups"
            carpeta.mkdir(exist_ok=True)
            (carpeta / filename).write_bytes(xlsx_bytes)
        except Exception as exc:
            logger.warning("No se pudo guardar copia en carpeta backups/: %s", exc)

    return xlsx_bytes, filename


def listar_backups_excel() -> list[dict[str, Any]]:
    """Lista los archivos .xlsx disponibles en la carpeta backups/ ordenados del más reciente al más antiguo."""
    carpeta = Path(settings.BASE_DIR) / "backups"
    if not carpeta.exists():
        return []
    archivos = []
    for f in sorted(carpeta.glob("*.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True):
        stat = f.stat()
        archivos.append({
            "nombre": f.name,
            "tamano_kb": round(stat.st_size / 1024, 1),
            "fecha": datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M:%S"),
        })
    return archivos


# ─────────────────────────────────────────────────────────────
#  Conversiones seguras de tipos para la importación
# ─────────────────────────────────────────────────────────────
def _to_str(val: Any, default: str | None = None) -> str | None:
    if val is None:
        return default
    s = str(val).strip()
    if s == "" or s.lower() == "none":
        return default
    # Si Excel convirtió un documento numérico en flotante (ej. "10523456.0")
    if s.endswith(".0") and s[:-2].lstrip("-").isdigit():
        s = s[:-2]
    return s


def _to_int(val: Any, default: int | None = None) -> int | None:
    if val is None or str(val).strip() == "":
        return default
    try:
        return int(float(str(val).strip()))
    except (ValueError, TypeError):
        return default


def _to_float(val: Any, default: float = 0.0) -> float:
    if val is None or str(val).strip() == "":
        return default
    try:
        return float(str(val).strip())
    except (ValueError, TypeError):
        return default


def _to_bool(val: Any, default: bool = False) -> bool:
    if val is None or str(val).strip() == "":
        return default
    if isinstance(val, bool):
        return val
    s = str(val).strip().upper()
    return s in ("1", "TRUE", "SI", "SÍ", "YES", "VERDADERO")


def _to_date(val: Any, default: datetime.date | None = None) -> datetime.date | None:
    if val is None or str(val).strip() == "":
        return default
    if isinstance(val, datetime.datetime):
        return val.date()
    if isinstance(val, datetime.date):
        return val
    # Si es un número serial de fecha de Excel (ej. 45900)
    if isinstance(val, (int, float)) and 20000 <= val <= 80000:
        return datetime.date(1899, 12, 30) + datetime.timedelta(days=int(val))
    s = str(val).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y"):
        try:
            return datetime.datetime.strptime(s[:19], fmt).date()
        except ValueError:
            continue
    return default


def _to_datetime(val: Any, default: datetime.datetime | None = None) -> datetime.datetime | None:
    if val is None or str(val).strip() == "":
        return default
    if isinstance(val, datetime.datetime):
        return val
    s = str(val).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S"):
        try:
            dt = datetime.datetime.strptime(s[:19], fmt)
            return dt.replace(tzinfo=datetime.timezone.utc)
        except ValueError:
            continue
    return default


def _sincronizar_secuencias_bd() -> None:
    """Actualiza las secuencias de autoincremento (PostgreSQL) tras insertar IDs explícitos."""
    modelos = [
        Almacen, Estante, Proveedor, Suministro, CategoriaHerramienta,
        Herramienta, Prestamo, DetallePrestamo, DevolucionHerramienta,
        Traslado, DetalleTraslado, Mantenimiento, DetalleMantenimiento,
        BitacoraEstado,
    ]
    try:
        sql_list = connection.ops.sequence_reset_sql(no_style(), modelos)
        if sql_list:
            with connection.cursor() as cursor:
                for sql in sql_list:
                    cursor.execute(sql)
    except Exception as exc:
        logger.warning("No fue necesario o falló el reinicio de secuencias: %s", exc)


# ─────────────────────────────────────────────────────────────
#  Importación incremental ("subir lo que falte")
# ─────────────────────────────────────────────────────────────
def importar_backup_excel(file_obj_or_bytes: Any) -> dict[str, Any]:
    """
    Lee un archivo .xlsx de copia de seguridad e inserta únicamente los registros
    que FALTEN en la base de datos activa, respetando llaves primarias, llaves únicas
    y relaciones foráneas, sin borrar ni sobrescribir la información existente.
    """
    data = parse_xlsx_file(file_obj_or_bytes)

    insertados: dict[str, int] = {}
    omitidos: dict[str, int] = {}

    def _inc_ins(tabla: str):
        insertados[tabla] = insertados.get(tabla, 0) + 1

    def _inc_omi(tabla: str):
        omitidos[tabla] = omitidos.get(tabla, 0) + 1

    # Mapas de traducción de llaves primarias (por si un registro ya existía por clave natural con otro ID)
    map_almacen: dict[int, int] = {}
    map_estante: dict[int, int] = {}
    map_proveedor: dict[int, int] = {}
    map_suministro: dict[int, int] = {}
    map_categoria: dict[int, int] = {}
    map_herramienta: dict[int, int] = {}
    map_prestamo: dict[int, int] = {}
    map_traslado: dict[int, int] = {}
    map_det_traslado: dict[int, int] = {}
    map_mantenimiento: dict[int, int] = {}

    with transaction.atomic():
        # 1. USUARIOS
        for row in data.get("Usuarios", []):
            doc = _to_str(row.get("documento"))
            if not doc:
                continue
            if Usuario.objects.filter(documento=doc).exists():
                _inc_omi("Usuarios")
                continue
            Usuario.objects.create(
                documento=doc,
                tipo_documento=_to_str(row.get("tipo_documento"), "CC") or "CC",
                primer_nombre=_to_str(row.get("primer_nombre"), "Usuario") or "Usuario",
                segundo_nombre=_to_str(row.get("segundo_nombre"), ""),
                primer_apellido=_to_str(row.get("primer_apellido"), "Sistema") or "Sistema",
                segundo_apellido=_to_str(row.get("segundo_apellido"), ""),
                correo_personal=_to_str(row.get("correo_personal")),
                telefono=_to_str(row.get("telefono")),
                programa=_to_str(row.get("programa")),
                ficha=_to_str(row.get("ficha")),
                rol=_to_str(row.get("rol"), "Usuario") or "Usuario",
                password=_to_str(row.get("password")),
                verificado_sofia_plus=_to_bool(row.get("verificado_sofia_plus"), False),
                fecha_verificacion=_to_datetime(row.get("fecha_verificacion")),
                reset_token=_to_str(row.get("reset_token"), "") or "",
                reset_token_expira=_to_float(row.get("reset_token_expira"), 0.0),
            )
            _inc_ins("Usuarios")

        # 2. ALMACENES
        for row in data.get("Almacenes", []):
            old_id = _to_int(row.get("codigo_almacen"))
            nombre = _to_str(row.get("nombre"))
            if not nombre:
                continue
            existente = None
            if old_id and Almacen.objects.filter(codigo_almacen=old_id).exists():
                existente = Almacen.objects.get(codigo_almacen=old_id)
            else:
                existente = Almacen.objects.filter(nombre__iexact=nombre).first()

            if existente:
                if old_id:
                    map_almacen[old_id] = existente.codigo_almacen
                _inc_omi("Almacenes")
                continue

            kwargs_alm: dict[str, Any] = {
                "nombre": nombre,
                "dimensiones": _to_str(row.get("dimensiones")),
                "ubicacion": _to_str(row.get("ubicacion")),
            }
            if old_id and not Almacen.objects.filter(codigo_almacen=old_id).exists():
                kwargs_alm["codigo_almacen"] = old_id
            nuevo = Almacen.objects.create(**kwargs_alm)
            if old_id:
                map_almacen[old_id] = nuevo.codigo_almacen
            _inc_ins("Almacenes")

        # 3. ESTANTES
        for row in data.get("Estantes", []):
            old_id = _to_int(row.get("num_estante"))
            codigo = _to_str(row.get("codigo"))
            raw_alm_id = _to_int(row.get("codigo_almacen_id") or row.get("codigo_almacen"))
            alm_id = map_almacen.get(raw_alm_id, raw_alm_id) if raw_alm_id else None
            if not codigo or not alm_id or not Almacen.objects.filter(codigo_almacen=alm_id).exists():
                continue

            existente = None
            if old_id and Estante.objects.filter(num_estante=old_id).exists():
                existente = Estante.objects.get(num_estante=old_id)
            else:
                existente = Estante.objects.filter(codigo__iexact=codigo, codigo_almacen_id=alm_id).first()

            if existente:
                if old_id:
                    map_estante[old_id] = existente.num_estante
                _inc_omi("Estantes")
                continue

            kwargs_est: dict[str, Any] = {
                "codigo": codigo,
                "dimensiones": _to_str(row.get("dimensiones")),
                "codigo_almacen_id": alm_id,
            }
            if old_id and not Estante.objects.filter(num_estante=old_id).exists():
                kwargs_est["num_estante"] = old_id
            nuevo = Estante.objects.create(**kwargs_est)
            if old_id:
                map_estante[old_id] = nuevo.num_estante
            _inc_ins("Estantes")

        # 4. PROVEEDORES
        for row in data.get("Proveedores", []):
            old_id = _to_int(row.get("codigo_proveedor"))
            nit = _to_str(row.get("nit_proveedor"))
            if not nit:
                continue
            existente = None
            if old_id and Proveedor.objects.filter(codigo_proveedor=old_id).exists():
                existente = Proveedor.objects.get(codigo_proveedor=old_id)
            else:
                existente = Proveedor.objects.filter(nit_proveedor__iexact=nit).first()

            if existente:
                if old_id:
                    map_proveedor[old_id] = existente.codigo_proveedor
                _inc_omi("Proveedores")
                continue

            kwargs_prov: dict[str, Any] = {
                "nit_proveedor": nit,
                "telefono_contacto": _to_str(row.get("telefono_contacto")),
                "correo_proveedor": _to_str(row.get("correo_proveedor")),
                "descripcion": _to_str(row.get("descripcion")),
            }
            if old_id and not Proveedor.objects.filter(codigo_proveedor=old_id).exists():
                kwargs_prov["codigo_proveedor"] = old_id
            nuevo = Proveedor.objects.create(**kwargs_prov)
            if old_id:
                map_proveedor[old_id] = nuevo.codigo_proveedor
            _inc_ins("Proveedores")

        # 5. SUMINISTROS
        for row in data.get("Suministros", []):
            old_id = _to_int(row.get("codigo_suministro"))
            raw_prov_id = _to_int(row.get("codigo_proveedor_id") or row.get("codigo_proveedor"))
            prov_id = map_proveedor.get(raw_prov_id, raw_prov_id) if raw_prov_id else None
            if not prov_id or not Proveedor.objects.filter(codigo_proveedor=prov_id).exists():
                continue

            if old_id and Suministro.objects.filter(codigo_suministro=old_id).exists():
                map_suministro[old_id] = old_id
                _inc_omi("Suministros")
                continue

            kwargs_sum: dict[str, Any] = {
                "codigo_proveedor_id": prov_id,
                "fecha": _to_date(row.get("fecha")),
                "cantidad": _to_int(row.get("cantidad")),
                "observaciones": _to_str(row.get("observaciones")),
            }
            if old_id:
                kwargs_sum["codigo_suministro"] = old_id
            nuevo = Suministro.objects.create(**kwargs_sum)
            if old_id:
                map_suministro[old_id] = nuevo.codigo_suministro
            _inc_ins("Suministros")

        # 6. CATEGORÍAS
        for row in data.get("Categorias", []):
            old_id = _to_int(row.get("codigo_categoria"))
            nombre_cat = _to_str(row.get("nombre_categoria"))
            tipo_herr = _to_str(row.get("tipo_herramienta"), "General") or "General"
            if not nombre_cat:
                continue
            existente = None
            if old_id and CategoriaHerramienta.objects.filter(codigo_categoria=old_id).exists():
                existente = CategoriaHerramienta.objects.get(codigo_categoria=old_id)
            else:
                existente = CategoriaHerramienta.objects.filter(nombre_categoria__iexact=nombre_cat).first()

            if existente:
                if old_id:
                    map_categoria[old_id] = existente.codigo_categoria
                _inc_omi("Categorias")
                continue

            kwargs_cat: dict[str, Any] = {
                "tipo_herramienta": tipo_herr,
                "nombre_categoria": nombre_cat,
                "descripcion": _to_str(row.get("descripcion")),
            }
            if old_id and not CategoriaHerramienta.objects.filter(codigo_categoria=old_id).exists():
                kwargs_cat["codigo_categoria"] = old_id
            nuevo = CategoriaHerramienta.objects.create(**kwargs_cat)
            if old_id:
                map_categoria[old_id] = nuevo.codigo_categoria
            _inc_ins("Categorias")

        # 7. HERRAMIENTAS
        for row in data.get("Herramientas", []):
            old_id = _to_int(row.get("codigo_herramienta"))
            sku = _to_str(row.get("codigo_sku"))
            nombre_h = _to_str(row.get("nombre_herramienta"))
            if not nombre_h:
                continue

            existente = None
            if sku and Herramienta.objects.filter(codigo_sku__iexact=sku).exists():
                existente = Herramienta.objects.filter(codigo_sku__iexact=sku).first()
            elif old_id and Herramienta.objects.filter(codigo_herramienta=old_id).exists():
                existente = Herramienta.objects.get(codigo_herramienta=old_id)

            if existente:
                if old_id:
                    map_herramienta[old_id] = existente.codigo_herramienta
                _inc_omi("Herramientas")
                continue

            raw_cat = _to_int(row.get("codigo_categoria_id") or row.get("codigo_categoria"))
            cat_id = map_categoria.get(raw_cat, raw_cat) if raw_cat else None
            if cat_id and not CategoriaHerramienta.objects.filter(codigo_categoria=cat_id).exists():
                cat_id = None

            raw_sum = _to_int(row.get("codigo_suministro_id") or row.get("codigo_suministro"))
            sum_id = map_suministro.get(raw_sum, raw_sum) if raw_sum else None
            if sum_id and not Suministro.objects.filter(codigo_suministro=sum_id).exists():
                sum_id = None

            raw_est = _to_int(row.get("estante_id") or row.get("estante"))
            est_id = map_estante.get(raw_est, raw_est) if raw_est else None
            if est_id and not Estante.objects.filter(num_estante=est_id).exists():
                est_id = None

            kwargs_h: dict[str, Any] = {
                "codigo_sku": sku,
                "nombre_herramienta": nombre_h,
                "descripcion": _to_str(row.get("descripcion")),
                "disponibilidad": _to_str(row.get("disponibilidad"), "1"),
                "fecha_ingreso": _to_date(row.get("fecha_ingreso")),
                "codigo_categoria_id": cat_id,
                "codigo_suministro_id": sum_id,
                "estado": _to_str(row.get("estado"), "Disponible"),
                "estante_id": est_id,
            }
            if old_id and not Herramienta.objects.filter(codigo_herramienta=old_id).exists():
                kwargs_h["codigo_herramienta"] = old_id
            nuevo = Herramienta.objects.create(**kwargs_h)
            if old_id:
                map_herramienta[old_id] = nuevo.codigo_herramienta
            _inc_ins("Herramientas")

        # 8. PRÉSTAMOS
        for row in data.get("Prestamos", []):
            old_id = _to_int(row.get("codigo_prestamo"))
            if old_id and Prestamo.objects.filter(codigo_prestamo=old_id).exists():
                map_prestamo[old_id] = old_id
                _inc_omi("Prestamos")
                continue

            doc_id = _to_str(row.get("documento_id") or row.get("documento"))
            if doc_id and not Usuario.objects.filter(documento=doc_id).exists():
                Usuario.objects.create(
                    documento=doc_id,
                    primer_nombre="Usuario",
                    primer_apellido="Sistema",
                    tipo_documento="CC",
                    rol="Usuario",
                )

            kwargs_p: dict[str, Any] = {
                "documento_id": doc_id,
                "fecha": _to_date(row.get("fecha")) or datetime.date.today(),
                "ficha": _to_str(row.get("ficha")),
                "estado": _to_str(row.get("estado"), "PENDIENTE") or "PENDIENTE",
                "observaciones": _to_str(row.get("observaciones")),
            }
            if old_id:
                kwargs_p["codigo_prestamo"] = old_id
            nuevo = Prestamo.objects.create(**kwargs_p)
            if old_id:
                map_prestamo[old_id] = nuevo.codigo_prestamo
            _inc_ins("Prestamos")

        # 9. DETALLES DE PRÉSTAMO
        for row in data.get("Detalles_Prestamo", []):
            old_id = _to_int(row.get("numeros_detalle"))
            if old_id and DetallePrestamo.objects.filter(numeros_detalle=old_id).exists():
                _inc_omi("Detalles_Prestamo")
                continue

            raw_p = _to_int(row.get("codigo_prestamo_id") or row.get("codigo_prestamo"))
            p_id = map_prestamo.get(raw_p, raw_p) if raw_p else None
            raw_h = _to_int(row.get("codigo_herramienta_id") or row.get("codigo_herramienta"))
            h_id = map_herramienta.get(raw_h, raw_h) if raw_h else None

            if not p_id or not Prestamo.objects.filter(codigo_prestamo=p_id).exists():
                continue
            if h_id and not Herramienta.objects.filter(codigo_herramienta=h_id).exists():
                continue

            kwargs_dp: dict[str, Any] = {
                "codigo_prestamo_id": p_id,
                "codigo_herramienta_id": h_id,
                "cantidad": max(1, _to_int(row.get("cantidad"), 1) or 1),
                "observaciones": _to_str(row.get("observaciones")),
            }
            if old_id:
                kwargs_dp["numeros_detalle"] = old_id
            DetallePrestamo.objects.create(**kwargs_dp)
            _inc_ins("Detalles_Prestamo")

        # 10. DEVOLUCIONES
        for row in data.get("Devoluciones", []):
            old_id = _to_int(row.get("codigo_devolucion"))
            if old_id and DevolucionHerramienta.objects.filter(codigo_devolucion=old_id).exists():
                _inc_omi("Devoluciones")
                continue

            raw_p = _to_int(row.get("codigo_prestamo_id") or row.get("codigo_prestamo"))
            p_id = map_prestamo.get(raw_p, raw_p) if raw_p else None
            if p_id and not Prestamo.objects.filter(codigo_prestamo=p_id).exists():
                continue

            recibe_id = _to_str(row.get("codigo_recibe_id") or row.get("codigo_recibe"))
            if recibe_id and not Usuario.objects.filter(documento=recibe_id).exists():
                recibe_id = None

            kwargs_dv: dict[str, Any] = {
                "codigo_prestamo_id": p_id,
                "codigo_recibe_id": recibe_id,
                "fecha": _to_date(row.get("fecha")) or datetime.date.today(),
                "observaciones": _to_str(row.get("observaciones")),
            }
            if old_id:
                kwargs_dv["codigo_devolucion"] = old_id
            DevolucionHerramienta.objects.create(**kwargs_dv)
            _inc_ins("Devoluciones")

        # 11. TRASLADOS
        for row in data.get("Traslados", []):
            old_id = _to_int(row.get("codigo_traslado"))
            if old_id and Traslado.objects.filter(codigo_traslado=old_id).exists():
                map_traslado[old_id] = old_id
                _inc_omi("Traslados")
                continue

            raw_est = _to_int(row.get("num_estante_origen_id") or row.get("num_estante_origen"))
            est_id = map_estante.get(raw_est, raw_est) if raw_est else None
            if est_id and not Estante.objects.filter(num_estante=est_id).exists():
                est_id = None

            kwargs_tr: dict[str, Any] = {
                "fecha_movimiento": _to_date(row.get("fecha_movimiento")),
                "dimensiones": _to_str(row.get("dimensiones")),
                "tipo_movimiento": _to_str(row.get("tipo_movimiento")),
                "num_estante_origen_id": est_id,
                "observaciones": _to_str(row.get("observaciones")),
            }
            if old_id:
                kwargs_tr["codigo_traslado"] = old_id
            nuevo = Traslado.objects.create(**kwargs_tr)
            if old_id:
                map_traslado[old_id] = nuevo.codigo_traslado
            _inc_ins("Traslados")

        # 12. DETALLES DE TRASLADO
        for row in data.get("Detalles_Traslado", []):
            old_id = _to_int(row.get("codigo_detalle"))
            if old_id and DetalleTraslado.objects.filter(codigo_detalle=old_id).exists():
                map_det_traslado[old_id] = old_id
                _inc_omi("Detalles_Traslado")
                continue

            raw_t = _to_int(row.get("codigo_traslado_id") or row.get("codigo_traslado"))
            t_id = map_traslado.get(raw_t, raw_t) if raw_t else None
            raw_h = _to_int(row.get("codigo_herramienta_id") or row.get("codigo_herramienta"))
            h_id = map_herramienta.get(raw_h, raw_h) if raw_h else None

            if not t_id or not Traslado.objects.filter(codigo_traslado=t_id).exists():
                continue
            if not h_id or not Herramienta.objects.filter(codigo_herramienta=h_id).exists():
                continue

            kwargs_dt: dict[str, Any] = {
                "codigo_traslado_id": t_id,
                "codigo_herramienta_id": h_id,
                "cantidad": _to_int(row.get("cantidad")),
                "observaciones": _to_str(row.get("observaciones")),
            }
            if old_id:
                kwargs_dt["codigo_detalle"] = old_id
            nuevo = DetalleTraslado.objects.create(**kwargs_dt)
            if old_id:
                map_det_traslado[old_id] = nuevo.codigo_detalle
            _inc_ins("Detalles_Traslado")

        # 13. MANTENIMIENTOS
        for row in data.get("Mantenimientos", []):
            old_id = _to_int(row.get("num_mantenimiento"))
            if old_id and Mantenimiento.objects.filter(num_mantenimiento=old_id).exists():
                map_mantenimiento[old_id] = old_id
                _inc_omi("Mantenimientos")
                continue

            raw_h = _to_int(row.get("codigo_herramienta_id") or row.get("codigo_herramienta"))
            h_id = map_herramienta.get(raw_h, raw_h) if raw_h else None
            if not h_id or not Herramienta.objects.filter(codigo_herramienta=h_id).exists():
                continue

            kwargs_m: dict[str, Any] = {
                "codigo_herramienta_id": h_id,
                "tipo_mantenimiento": _to_str(row.get("tipo_mantenimiento")),
                "fecha_ingreso": _to_date(row.get("fecha_ingreso")),
                "fecha_salida": _to_date(row.get("fecha_salida")),
                "descripcion": _to_str(row.get("descripcion")),
                "observaciones": _to_str(row.get("observaciones")),
            }
            if old_id:
                kwargs_m["num_mantenimiento"] = old_id
            nuevo = Mantenimiento.objects.create(**kwargs_m)
            if old_id:
                map_mantenimiento[old_id] = nuevo.num_mantenimiento
            _inc_ins("Mantenimientos")

        # 14. DETALLES DE MANTENIMIENTO
        for row in data.get("Detalles_Mantenimiento", []):
            old_id = _to_int(row.get("detalle_mantenimiento"))
            if old_id and DetalleMantenimiento.objects.filter(detalle_mantenimiento=old_id).exists():
                _inc_omi("Detalles_Mantenimiento")
                continue

            raw_m = _to_int(row.get("num_mantenimiento_id") or row.get("num_mantenimiento"))
            m_id = map_mantenimiento.get(raw_m, raw_m) if raw_m else None
            if not m_id or not Mantenimiento.objects.filter(num_mantenimiento=m_id).exists():
                continue

            raw_dt = _to_int(row.get("codigo_detalle_traslado_id") or row.get("codigo_detalle_traslado"))
            dt_id = map_det_traslado.get(raw_dt, raw_dt) if raw_dt else None
            if dt_id and not DetalleTraslado.objects.filter(codigo_detalle=dt_id).exists():
                dt_id = None

            kwargs_dm: dict[str, Any] = {
                "num_mantenimiento_id": m_id,
                "codigo_detalle_traslado_id": dt_id,
                "accion_realizada": _to_str(row.get("accion_realizada")),
                "materiales_usados": _to_str(row.get("materiales_usados")),
                "fecha_mantenimiento": _to_date(row.get("fecha_mantenimiento")),
                "observacion": _to_str(row.get("observacion")),
            }
            if old_id:
                kwargs_dm["detalle_mantenimiento"] = old_id
            DetalleMantenimiento.objects.create(**kwargs_dm)
            _inc_ins("Detalles_Mantenimiento")

        # 15. BITÁCORAS DE ESTADO
        for row in data.get("Bitacoras_Estado", []):
            old_id = _to_int(row.get("codigo_bitacora"))
            if old_id and BitacoraEstado.objects.filter(codigo_bitacora=old_id).exists():
                _inc_omi("Bitacoras_Estado")
                continue

            raw_h = _to_int(row.get("codigo_herramienta_id") or row.get("codigo_herramienta"))
            h_id = map_herramienta.get(raw_h, raw_h) if raw_h else None
            if not h_id or not Herramienta.objects.filter(codigo_herramienta=h_id).exists():
                continue

            doc_id = _to_str(row.get("documento_id") or row.get("documento"))
            if not doc_id or not Usuario.objects.filter(documento=doc_id).exists():
                continue

            raw_m = _to_int(row.get("num_mantenimiento_id") or row.get("num_mantenimiento"))
            m_id = map_mantenimiento.get(raw_m, raw_m) if raw_m else None
            if m_id and not Mantenimiento.objects.filter(num_mantenimiento=m_id).exists():
                m_id = None

            kwargs_b: dict[str, Any] = {
                "num_mantenimiento_id": m_id,
                "codigo_herramienta_id": h_id,
                "documento_id": doc_id,
                "documento_tecnico": _to_str(row.get("documento_tecnico")),
                "es_inutilisable": _to_bool(row.get("es_inutilisable"), False),
                "descripcion": _to_str(row.get("descripcion")),
                "observaciones": _to_str(row.get("observaciones")),
            }
            if old_id:
                kwargs_b["codigo_bitacora"] = old_id
            BitacoraEstado.objects.create(**kwargs_b)
            _inc_ins("Bitacoras_Estado")

    _sincronizar_secuencias_bd()

    total_insertados = sum(insertados.values())
    total_omitidos = sum(omitidos.values())
    return {
        "total_insertados": total_insertados,
        "total_omitidos": total_omitidos,
        "insertados_por_tabla": insertados,
        "omitidos_por_tabla": omitidos,
    }

