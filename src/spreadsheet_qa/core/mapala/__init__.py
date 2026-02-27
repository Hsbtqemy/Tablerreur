"""Mapala core — mapping de tableurs."""

from .template_builder import TemplateBuilderConfig, ZoneSpec, build_output
from .io_excel import list_sheets, load_sheet, save_output as save_mapala_output
from .config import ConcatSource, LaConcordeError as MapalaError

__all__ = [
    "TemplateBuilderConfig",
    "ZoneSpec",
    "build_output",
    "list_sheets",
    "load_sheet",
    "save_mapala_output",
    "ConcatSource",
    "MapalaError",
]
