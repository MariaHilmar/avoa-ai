"""(De)serialização genérica de dataclasses do domínio para JSON.

Permite persistir as entidades do Avoa num backend baseado em texto (SQLite
hoje, Postgres/Supabase depois) e reconstruí-las. Trata Enums, datetime e
dataclasses aninhadas via anotações de tipo. Ver docs/PERSISTENCE.md.
"""

from __future__ import annotations

import dataclasses
import enum
import typing
from datetime import datetime

from core.domain import models
from core.quality import checklists

# Registro nome->classe das dataclasses conhecidas (para reconstrução).
_REGISTRO: dict[str, type] = {}
for _mod in (models, checklists):
    for _nome in dir(_mod):
        _obj = getattr(_mod, _nome)
        if isinstance(_obj, type) and dataclasses.is_dataclass(_obj):
            _REGISTRO[_nome] = _obj


def serialize(obj):
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        d = {"__type__": type(obj).__name__}
        for f in dataclasses.fields(obj):
            d[f.name] = serialize(getattr(obj, f.name))
        return d
    if isinstance(obj, enum.Enum):
        return obj.value
    if isinstance(obj, datetime):
        return {"__dt__": obj.isoformat()}
    if isinstance(obj, list):
        return [serialize(x) for x in obj]
    if isinstance(obj, dict):
        return {k: serialize(v) for k, v in obj.items()}
    return obj


def _coagir(valor, anotacao):
    """Coage um valor bruto para o tipo anotado (Enum/dataclass/list)."""
    origem = typing.get_origin(anotacao)
    if origem in (list, typing.List) and isinstance(valor, list):
        (arg,) = typing.get_args(anotacao) or (object,)
        return [_coagir(v, arg) for v in valor]
    if isinstance(anotacao, type) and issubclass(anotacao, enum.Enum):
        return anotacao(valor)
    return deserialize(valor)


def deserialize(data):
    if isinstance(data, dict) and "__dt__" in data:
        return datetime.fromisoformat(data["__dt__"])
    if isinstance(data, dict) and "__type__" in data:
        cls = _REGISTRO[data["__type__"]]
        hints = typing.get_type_hints(cls)
        kwargs = {}
        for f in dataclasses.fields(cls):
            if f.name in data:
                kwargs[f.name] = _coagir(data[f.name], hints.get(f.name, object))
        return cls(**kwargs)
    if isinstance(data, list):
        return [deserialize(x) for x in data]
    return data
