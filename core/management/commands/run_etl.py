"""ETL de Mine Inventory: CSV/Excel -> PostgreSQL.

Uso::

    python manage.py run_etl --file datos/herramientas.xlsx --type herramientas
    python manage.py run_etl --file datos/herramientas.xlsx --type herramientas --dry-run

Tipos: herramientas, categorias, almacenes, estantes, proveedores.

Este comando es global: vive en `core` y NO importa modelos de otras apps al
cargar el módulo. Cada loader declara su modelo como 'app.Modelo' y se resuelve
con `apps.get_model()` solo cuando se usa (--type). Requiere 'core' en
INSTALLED_APPS para que Django descubra el comando.

Flujo:
    Extract   -> pandas lee todo como texto (dtype=str).
    Transform -> en memoria, SIN tocar la BD. Si algo falla, aborta aquí.
    Load      -> una sola transaction.atomic(); cualquier error = rollback total.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, ClassVar

import pandas as pd
from django.apps import apps
from django.core.exceptions import MultipleObjectsReturned, ValidationError
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.core.validators import validate_email
from django.db import DatabaseError, connection, models, transaction

NULL_TOKENS = frozenset({"nan", "none", "null", "n/a"})
EXCEL_SUFFIXES = frozenset({".xlsx", ".xlsm", ".xls"})
DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y-%m-%d %H:%M:%S",
    "%d/%m/%Y",
    "%d/%m/%Y %H:%M:%S",
    "%d-%m-%Y",
    "%Y/%m/%d",
)
DEFAULT_TIPO_HERRAMIENTA = "Sin clasificar"
NO_DISPONIBLE = "No disponible"
MAX_ERRORS_SHOWN = 25


# --------------------------------------------------------------------------
# Tipos auxiliares
# --------------------------------------------------------------------------
class RowError(Exception):
    """Fila inválida. Se reporta con su número de fila y aborta la carga."""


@dataclass
class Stats:
    rows_read: int = 0
    duplicates_dropped: int = 0
    created: int = 0
    updated: int = 0
    related_created: Counter[str] = field(default_factory=Counter)
    errors: list[str] = field(default_factory=list)


@dataclass
class Record:
    """Fila ya validada. `fields` = campos del modelo; `refs` = nombres de FKs."""

    line: int
    fields: dict[str, Any]
    refs: dict[str, str] = field(default_factory=dict)


# --------------------------------------------------------------------------
# Funciones de limpieza (puras, sin BD)
# --------------------------------------------------------------------------
def normalize_header(name: object) -> str:
    """'  Categoría Herramienta ' -> 'categoria_herramienta'."""
    ascii_text = (
        unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode()
    )
    return re.sub(r"[^a-z0-9]+", "_", ascii_text.lower()).strip("_")


def clean_text(value: object) -> str:
    """strip + espacios múltiples colapsados; nulos de todo tipo -> ''."""
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return ""
    text = re.sub(r"\s+", " ", str(value)).strip()
    return "" if text.casefold() in NULL_TOKENS else text


def capitalize_first(text: str) -> str:
    """Solo sube la 1ra letra; respeta siglas y medidas ('PVC', '3/8')."""
    return text[:1].upper() + text[1:]


def title_case(text: str) -> str:
    """'bodega CENTRAL' -> 'Bodega Central' (para nombres de catálogos/FK)."""
    return " ".join(word.capitalize() for word in text.split(" "))


def parse_stock(raw: str) -> str:
    """Devuelve el texto que espera Herramienta.disponibilidad.

    Vacío -> '0'. Solo enteros >= 0 o 'No disponible'. Se rechaza '1.000'
    porque no se puede saber si es mil o uno con decimales.
    """
    if not raw:
        return "0"
    if raw.casefold() == NO_DISPONIBLE.casefold():
        return NO_DISPONIBLE
    match = re.fullmatch(r"(\d+)(?:[.,]0)?", raw)
    if match is None:
        raise RowError(
            f"'disponibilidad': se esperaba entero >= 0 sin separador de miles, "
            f"llegó '{raw}'"
        )
    return str(int(match.group(1)))


def parse_date(raw: str, column: str) -> date:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise RowError(
        f"'{column}': fecha inválida '{raw}' (use AAAA-MM-DD o DD/MM/AAAA)"
    )


def check_length(model: type[models.Model], field_name: str, value: str) -> None:
    """Evita el DataError de PostgreSQL validando max_length antes de insertar."""
    max_length = model._meta.get_field(field_name).max_length
    if max_length is not None and len(value) > max_length:
        raise RowError(
            f"'{field_name}' excede {max_length} caracteres ({len(value)})"
        )


def check_lengths(model: type[models.Model], fields: dict[str, Any]) -> None:
    for name, value in fields.items():
        if isinstance(value, str):
            check_length(model, name, value)


def describe(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        return "; ".join(exc.messages)
    return str(exc)


# --------------------------------------------------------------------------
# Resolución de claves foráneas (get_or_create + caché)
# --------------------------------------------------------------------------
class RelationResolver:
    """Crea/recupera Categoría, Almacén y Estante una sola vez por valor único."""

    def __init__(self, stats: Stats) -> None:
        self._stats = stats
        self._categorias: dict[str, models.Model] = {}
        self._almacenes: dict[str, models.Model] = {}
        self._estantes: dict[tuple[str, str], models.Model] = {}

    def clear(self) -> None:
        """Vaciar caché tras un rollback de savepoint (objetos pudieron desaparecer)."""
        self._categorias.clear()
        self._almacenes.clear()
        self._estantes.clear()

    def _count(self, name: str, created: bool) -> None:
        if created:
            self._stats.related_created[name] += 1

    def categoria(self, nombre: str) -> models.Model:
        key = nombre.casefold()
        if key not in self._categorias:
            model = apps.get_model("herramienta", "CategoriaHerramienta")
            check_length(model, "nombre_categoria", nombre)
            obj, created = model.objects.get_or_create(
                nombre_categoria__iexact=nombre,
                defaults={
                    "nombre_categoria": nombre,
                    "tipo_herramienta": DEFAULT_TIPO_HERRAMIENTA,
                },
            )
            self._count("categorias", created)
            self._categorias[key] = obj
        return self._categorias[key]

    def almacen(self, nombre: str) -> models.Model:
        key = nombre.casefold()
        if key not in self._almacenes:
            model = apps.get_model("almacen", "Almacen")
            check_length(model, "nombre", nombre)
            obj, created = model.objects.get_or_create(
                nombre__iexact=nombre,
                defaults={"nombre": nombre},
            )
            self._count("almacenes", created)
            self._almacenes[key] = obj
        return self._almacenes[key]

    def estante(self, codigo: str, almacen: str = "") -> models.Model:
        cache_key = (codigo.casefold(), almacen.casefold())
        if cache_key in self._estantes:
            return self._estantes[cache_key]

        model = apps.get_model("almacen", "Estante")
        if almacen:
            check_length(model, "codigo", codigo)
            obj, created = model.objects.get_or_create(
                codigo__iexact=codigo,
                codigo_almacen=self.almacen(almacen),
                defaults={"codigo": codigo},
            )
            self._count("estantes", created)
        else:
            # Estante.codigo NO es único entre almacenes: sin almacén solo
            # se acepta si hay exactamente uno.
            matches = list(model.objects.filter(codigo__iexact=codigo)[:2])
            if not matches:
                raise RowError(
                    f"estante '{codigo}' no existe; agregue columna 'almacen' "
                    f"para crearlo"
                )
            if len(matches) > 1:
                raise RowError(
                    f"estante '{codigo}' existe en varios almacenes; agregue "
                    f"columna 'almacen'"
                )
            obj = matches[0]
        self._estantes[cache_key] = obj
        return obj


# --------------------------------------------------------------------------
# Loaders: uno por --type. Agregar tipo nuevo = agregar clase + registrarla.
# --------------------------------------------------------------------------
class BaseLoader:
    label: ClassVar[str]
    model_label: ClassVar[str]  # 'app.Modelo', se resuelve al instanciar
    lookup_field: ClassVar[str]
    unique_columns: ClassVar[tuple[str, ...]]
    required: ClassVar[tuple[str, ...]]
    # columna canónica -> alias aceptados en el archivo (ya normalizados)
    aliases: ClassVar[dict[str, tuple[str, ...]]] = {}
    # solo al CREAR (en update no pisan lo existente)
    create_only_defaults: ClassVar[dict[str, Any]] = {}

    def __init__(self, resolver: RelationResolver) -> None:
        self.resolver = resolver
        self.model: type[models.Model] = apps.get_model(self.model_label)

    def prepare_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Hook: normalizar columnas clave antes de deduplicar."""
        return frame

    def build(self, row: dict[str, str], line: int) -> Record:
        raise NotImplementedError

    def resolve(self, record: Record) -> None:
        """Hook: resolver FKs (usa BD). Por defecto no hace nada."""

    def upsert(self, record: Record) -> bool:
        """update_or_create por código único (insensible a mayúsculas).

        La clave solo se escribe al CREAR: en update no se renombran registros
        existentes (evita cambiar 'abc-1' -> 'ABC-1' sin que nadie lo pida).
        """
        updates = {k: v for k, v in record.fields.items() if k != self.lookup_field}
        _, created = self.model._default_manager.update_or_create(
            defaults=updates,
            create_defaults={**self.create_only_defaults, **record.fields},
            **{f"{self.lookup_field}__iexact": record.fields[self.lookup_field]},
        )
        return created


class HerramientaLoader(BaseLoader):
    label = "herramientas"
    model_label = "herramienta.Herramienta"
    lookup_field = "codigo_sku"
    unique_columns = ("codigo_sku",)
    required = ("codigo_sku", "nombre_herramienta")
    aliases = {
        "codigo_sku": ("codigo", "sku"),
        "nombre_herramienta": ("nombre", "herramienta"),
        "disponibilidad": ("stock", "cantidad", "existencias", "stock_disponible"),
        "fecha_ingreso": ("fecha", "fecha_de_ingreso"),
        "categoria": ("nombre_categoria", "categoria_herramienta"),
        "almacen": ("bodega",),
        "estante": ("codigo_estante",),
    }
    create_only_defaults = {"disponibilidad": "0"}

    def build(self, row: dict[str, str], line: int) -> Record:
        nombre = capitalize_first(row["nombre_herramienta"])
        if not nombre:
            raise RowError("'nombre_herramienta' vacío")

        fields: dict[str, Any] = {
            "codigo_sku": row["codigo_sku"].upper(),
            "nombre_herramienta": nombre,
        }
        # Columna presente pero vacía -> '0'. Columna ausente -> no se toca.
        if "disponibilidad" in row:
            fields["disponibilidad"] = parse_stock(row["disponibilidad"])
        if row.get("fecha_ingreso"):
            fields["fecha_ingreso"] = parse_date(row["fecha_ingreso"], "fecha_ingreso")
        if row.get("descripcion"):
            fields["descripcion"] = row["descripcion"]
        if row.get("estado"):
            fields["estado"] = capitalize_first(row["estado"])
        check_lengths(self.model, fields)

        refs: dict[str, str] = {}
        estante, almacen = row.get("estante", "").upper(), row.get("almacen", "")
        if almacen and not estante:
            raise RowError("hay 'almacen' pero falta 'estante'")
        if row.get("categoria"):
            refs["categoria"] = title_case(row["categoria"])
        if estante:
            refs["estante"] = estante
            refs["almacen"] = title_case(almacen)
        return Record(line, fields, refs)

    def resolve(self, record: Record) -> None:
        refs = record.refs
        if "categoria" in refs:
            record.fields["codigo_categoria"] = self.resolver.categoria(
                refs["categoria"]
            )
        if "estante" in refs:
            record.fields["estante"] = self.resolver.estante(
                refs["estante"], refs["almacen"]
            )


class CategoriaLoader(BaseLoader):
    label = "categorias"
    model_label = "herramienta.CategoriaHerramienta"
    lookup_field = "nombre_categoria"
    unique_columns = ("nombre_categoria",)
    required = ("nombre_categoria",)
    aliases = {
        "nombre_categoria": ("categoria", "nombre"),
        "tipo_herramienta": ("tipo",),
    }
    create_only_defaults = {"tipo_herramienta": DEFAULT_TIPO_HERRAMIENTA}

    def build(self, row: dict[str, str], line: int) -> Record:
        fields: dict[str, Any] = {
            "nombre_categoria": title_case(row["nombre_categoria"])
        }
        if row.get("tipo_herramienta"):
            fields["tipo_herramienta"] = title_case(row["tipo_herramienta"])
        if row.get("descripcion"):
            fields["descripcion"] = row["descripcion"]
        check_lengths(self.model, fields)
        return Record(line, fields)


class AlmacenLoader(BaseLoader):
    label = "almacenes"
    model_label = "almacen.Almacen"
    lookup_field = "nombre"
    unique_columns = ("nombre",)
    required = ("nombre",)
    aliases = {
        "nombre": ("almacen", "bodega", "nombre_almacen"),
        "ubicacion": ("direccion",),
    }

    def build(self, row: dict[str, str], line: int) -> Record:
        fields: dict[str, Any] = {"nombre": title_case(row["nombre"])}
        for name in ("dimensiones", "ubicacion"):
            if row.get(name):
                fields[name] = row[name]
        check_lengths(self.model, fields)
        return Record(line, fields)


class EstanteLoader(BaseLoader):
    label = "estantes"
    model_label = "almacen.Estante"
    lookup_field = "codigo"  # no se usa: upsert propio (clave = codigo + almacén)
    unique_columns = ("codigo", "almacen")
    required = ("codigo", "almacen")
    aliases = {
        "codigo": ("estante", "codigo_estante"),
        "almacen": ("bodega", "nombre_almacen"),
    }

    def build(self, row: dict[str, str], line: int) -> Record:
        fields: dict[str, Any] = {"codigo": row["codigo"].upper()}
        if row.get("dimensiones"):
            fields["dimensiones"] = row["dimensiones"]
        check_lengths(self.model, fields)
        return Record(line, fields, {"almacen": title_case(row["almacen"])})

    def resolve(self, record: Record) -> None:
        record.fields["codigo_almacen"] = self.resolver.almacen(record.refs["almacen"])

    def upsert(self, record: Record) -> bool:
        fields = dict(record.fields)
        almacen = fields.pop("codigo_almacen")
        codigo = fields.pop("codigo")
        _, created = self.model._default_manager.update_or_create(
            codigo__iexact=codigo,
            codigo_almacen=almacen,
            defaults=fields,
            create_defaults={"codigo": codigo, **fields},
        )
        return created


class ProveedorLoader(BaseLoader):
    label = "proveedores"
    model_label = "herramienta.Proveedor"
    lookup_field = "nit_proveedor"
    unique_columns = ("nit_proveedor",)
    required = ("nit_proveedor",)
    aliases = {
        "nit_proveedor": ("nit",),
        "telefono_contacto": ("telefono", "celular"),
        "correo_proveedor": ("correo", "email", "correo_electronico"),
        # Proveedor no tiene campo 'nombre': razón social va en descripcion.
        "descripcion": ("nombre", "razon_social"),
    }

    def prepare_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        # '900.123.456-7' y '900123456-7' son el mismo NIT.
        frame["nit_proveedor"] = frame["nit_proveedor"].str.replace(
            r"[.\s]", "", regex=True
        )
        return frame

    def build(self, row: dict[str, str], line: int) -> Record:
        fields: dict[str, Any] = {"nit_proveedor": row["nit_proveedor"]}
        for name in ("telefono_contacto", "descripcion"):
            if row.get(name):
                fields[name] = row[name]
        if row.get("correo_proveedor"):
            email = row["correo_proveedor"].lower()
            try:
                validate_email(email)
            except ValidationError:
                raise RowError(f"'correo_proveedor' inválido: '{email}'") from None
            fields["correo_proveedor"] = email
        check_lengths(self.model, fields)
        return Record(line, fields)


LOADERS: dict[str, type[BaseLoader]] = {
    loader.label: loader
    for loader in (
        HerramientaLoader,
        CategoriaLoader,
        AlmacenLoader,
        EstanteLoader,
        ProveedorLoader,
    )
}


# --------------------------------------------------------------------------
# Comando
# --------------------------------------------------------------------------
class Command(BaseCommand):
    help = "ETL: carga CSV/Excel a PostgreSQL con upsert, FKs automáticas y rollback."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--file", required=True, type=Path, help="CSV o Excel.")
        parser.add_argument(
            "--type",
            required=True,
            choices=sorted(LOADERS),
            help="Qué entidad cargar.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Ejecuta todo y muestra resultados, pero hace rollback al final.",
        )
        parser.add_argument(
            "--allow-non-postgres",
            action="store_true",
            help="Permitir BD distinta de PostgreSQL (por defecto se bloquea).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        path: Path = options["file"]
        dry_run: bool = options["dry_run"]

        self._check_database(options["allow_non_postgres"])
        if not path.is_file():
            raise CommandError(f"No existe el archivo: {path}")

        stats = Stats()
        resolver = RelationResolver(stats)
        try:
            loader = LOADERS[options["type"]](resolver)
        except LookupError as exc:  # app/modelo no instalado
            raise CommandError(
                f"El tipo '{options['type']}' necesita {LOADERS[options['type']].model_label}, "
                f"pero no está en INSTALLED_APPS: {exc}"
            ) from exc
        tag = " [DRY-RUN]" if dry_run else ""
        self.stdout.write(
            self.style.MIGRATE_HEADING(f"ETL '{loader.label}' <- {path.name}{tag}")
        )

        raw = self._extract(path)
        stats.rows_read = len(raw)
        records = self._transform(raw, loader, stats)
        if stats.errors:  # errores de formato: ni se abre la transacción
            self._report_errors(stats.errors)
            raise CommandError("Errores en el archivo. No se tocó la BD.")

        self._load(records, loader, resolver, stats, dry_run)
        self._summary(stats, dry_run)

    # ---------------------------------------------------------------- Extract
    @staticmethod
    def _extract(path: Path) -> pd.DataFrame:
        suffix = path.suffix.lower()
        try:
            if suffix == ".csv":
                return Command._read_csv(path)
            if suffix in EXCEL_SUFFIXES:
                return pd.read_excel(path, dtype=str, keep_default_na=False)
        except ImportError as exc:
            raise CommandError(
                f"Falta dependencia: {exc}. Instale openpyxl (.xlsx) o xlrd (.xls)."
            ) from exc
        except (pd.errors.ParserError, pd.errors.EmptyDataError, ValueError) as exc:
            raise CommandError(f"No se pudo leer '{path.name}': {exc}") from exc
        raise CommandError(f"Extensión '{suffix}' no soportada.")

    @staticmethod
    def _read_csv(path: Path) -> pd.DataFrame:
        # sep=None detecta ',' o ';' (Excel en español exporta con ';').
        for encoding in ("utf-8-sig", "cp1252"):
            try:
                return pd.read_csv(
                    path,
                    dtype=str,
                    keep_default_na=False,
                    sep=None,
                    engine="python",
                    encoding=encoding,
                )
            except UnicodeDecodeError:
                continue
        raise CommandError("Codificación no reconocida (use UTF-8 o Windows-1252).")

    # -------------------------------------------------------------- Transform
    def _transform(
        self, raw: pd.DataFrame, loader: BaseLoader, stats: Stats
    ) -> list[Record]:
        frame = raw.rename(columns=normalize_header)
        rename = {
            alias: canonical
            for canonical, aliases in loader.aliases.items()
            for alias in aliases
            if alias in frame.columns
        }
        frame = frame.rename(columns=rename)

        repeated = frame.columns[frame.columns.duplicated()].tolist()
        if repeated:
            raise CommandError(f"Columnas repetidas tras normalizar: {repeated}")
        missing = [col for col in loader.required if col not in frame.columns]
        if missing:
            raise CommandError(
                f"Faltan columnas {missing}. Encabezados detectados: "
                f"{list(frame.columns)}"
            )

        frame = frame.apply(lambda column: column.map(clean_text))
        frame["_line"] = frame.index + 2  # fila 1 = encabezado
        has_data = (frame.drop(columns="_line") != "").any(axis=1)
        frame = loader.prepare_frame(frame[has_data].copy())

        unique = list(loader.unique_columns)
        no_key = (frame[unique] == "").any(axis=1)
        for line in frame.loc[no_key, "_line"]:
            stats.errors.append(f"fila {line}: falta {' + '.join(unique)}")
        frame = frame[~no_key]

        # Duplicados dentro del archivo: gana la ÚLTIMA aparición.
        keys = frame[unique].apply(lambda column: column.str.casefold())
        is_duplicate = keys.duplicated(keep="last")
        stats.duplicates_dropped = int(is_duplicate.sum())
        frame = frame[~is_duplicate]

        records: list[Record] = []
        for row in frame.to_dict("records"):
            line = int(row.pop("_line"))
            try:
                records.append(loader.build(row, line))
            except RowError as exc:
                stats.errors.append(f"fila {line}: {exc}")
        return records

    # ------------------------------------------------------------------- Load
    def _load(
        self,
        records: list[Record],
        loader: BaseLoader,
        resolver: RelationResolver,
        stats: Stats,
        dry_run: bool,
    ) -> None:
        try:
            with transaction.atomic():
                for record in records:
                    try:
                        # Savepoint por fila: un error de BD no "envenena"
                        # la transacción y podemos reportar TODAS las filas malas.
                        with transaction.atomic():
                            loader.resolve(record)
                            created = loader.upsert(record)
                    except (
                        RowError,
                        ValidationError,
                        MultipleObjectsReturned,
                        DatabaseError,
                    ) as exc:
                        stats.errors.append(f"fila {record.line}: {describe(exc)}")
                        resolver.clear()
                        continue
                    if created:
                        stats.created += 1
                    else:
                        stats.updated += 1

                if stats.errors:
                    self._report_errors(stats.errors)
                    raise CommandError("Hubo errores. Rollback completo: nada se guardó.")
                if dry_run:
                    transaction.set_rollback(True)
        except DatabaseError as exc:
            raise CommandError(f"Error de BD, rollback completo: {exc}") from exc

    # ---------------------------------------------------------------- Salida
    def _check_database(self, allow_non_postgres: bool) -> None:
        cfg = connection.settings_dict
        self.stdout.write(
            f"BD destino: {connection.vendor} | {cfg.get('NAME')} "
            f"@ {cfg.get('HOST') or 'local'}"
        )
        if connection.vendor != "postgresql" and not allow_non_postgres:
            raise CommandError(
                "La BD activa no es PostgreSQL (¿settings cayó al fallback SQLite?). "
                "Use --allow-non-postgres solo si es intencional."
            )

    def _report_errors(self, errors: list[str]) -> None:
        self.stdout.write(self.style.ERROR(f"\n{len(errors)} error(es):"))
        for message in errors[:MAX_ERRORS_SHOWN]:
            self.stdout.write(self.style.ERROR(f"  - {message}"))
        hidden = len(errors) - MAX_ERRORS_SHOWN
        if hidden > 0:
            self.stdout.write(self.style.ERROR(f"  ... y {hidden} más"))

    def _summary(self, stats: Stats, dry_run: bool) -> None:
        rows = [
            ("Filas leídas", stats.rows_read),
            ("Duplicados descartados (archivo)", stats.duplicates_dropped),
            ("Se crearían" if dry_run else "Creados", stats.created),
            ("Se actualizarían" if dry_run else "Actualizados", stats.updated),
        ]
        rows += [
            (f"FK nuevas: {name}", count)
            for name, count in sorted(stats.related_created.items())
        ]
        self.stdout.write(self.style.MIGRATE_HEADING("\nResumen"))
        for label, value in rows:
            self.stdout.write(f"  {label:<34}{value:>6}")
        if dry_run:
            self.stdout.write(
                self.style.WARNING("\nDRY-RUN: rollback forzado. No se guardó nada.")
            )
        else:
            self.stdout.write(self.style.SUCCESS("\nCommit OK."))