"""Implementações da Port `Repository` (dados DO AVOA, não das issues).

- `InMemoryRepository`: padrão em dev/testes.
- `SQLiteRepository`: durável; troca-se por Postgres/Supabase sem mexer na
  lógica (o domínio é neutro). Ver docs/PERSISTENCE.md.

Ambos separam gravação *mutável* (`salvar`, upsert por id) da *append-only*
(`anexar`, para métricas/execuções — histórico que nunca é sobrescrito).
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, is_dataclass

from core.persistence.serialize import deserialize, serialize


def _tipo_nome(tipo: type) -> str:
    return tipo.__name__


def _id_de(entidade: object) -> str:
    if hasattr(entidade, "id"):
        return str(getattr(entidade, "id"))
    raise ValueError("Entidade sem atributo 'id' não pode ser salva.")


class InMemoryRepository:
    """Repositório em memória. Implementa a Port `Repository`."""

    def __init__(self) -> None:
        self._itens: dict[tuple[str, str], object] = {}
        self._log: dict[str, list[object]] = {}  # append-only por tipo

    def salvar(self, entidade: object) -> str:
        id_ = _id_de(entidade)
        self._itens[(_tipo_nome(type(entidade)), id_)] = entidade
        return id_

    def buscar(self, tipo: type, id_: str) -> object | None:
        return self._itens.get((_tipo_nome(tipo), str(id_)))

    def listar(self, tipo: type, **filtros) -> list:
        nome = _tipo_nome(tipo)
        itens = [v for (t, _), v in self._itens.items() if t == nome]
        itens += self._log.get(nome, [])
        for campo, valor in filtros.items():
            itens = [i for i in itens if getattr(i, campo, None) == valor]
        return itens

    def anexar(self, entidade: object) -> str:
        """Append-only: nunca sobrescreve — só acrescenta ao histórico."""
        self._log.setdefault(_tipo_nome(type(entidade)), []).append(entidade)
        return _id_de(entidade) if hasattr(entidade, "id") else ""


class SQLiteRepository:
    """Repositório durável em SQLite. Implementa a Port `Repository`."""

    def __init__(self, caminho: str = ":memory:") -> None:
        self._con = sqlite3.connect(caminho)
        self._con.execute(
            "CREATE TABLE IF NOT EXISTS itens "
            "(tipo TEXT, id TEXT, dados TEXT, PRIMARY KEY (tipo, id))"
        )
        self._con.execute(
            "CREATE TABLE IF NOT EXISTS log "
            "(seq INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, dados TEXT)"
        )
        self._con.commit()

    def salvar(self, entidade: object) -> str:
        id_ = _id_de(entidade)
        dados = json.dumps(serialize(entidade), ensure_ascii=False)
        self._con.execute(
            "INSERT INTO itens (tipo, id, dados) VALUES (?, ?, ?) "
            "ON CONFLICT(tipo, id) DO UPDATE SET dados=excluded.dados",
            (_tipo_nome(type(entidade)), id_, dados),
        )
        self._con.commit()
        return id_

    def buscar(self, tipo: type, id_: str) -> object | None:
        cur = self._con.execute(
            "SELECT dados FROM itens WHERE tipo=? AND id=?", (_tipo_nome(tipo), str(id_))
        )
        linha = cur.fetchone()
        return deserialize(json.loads(linha[0])) if linha else None

    def listar(self, tipo: type, **filtros) -> list:
        nome = _tipo_nome(tipo)
        itens = [
            deserialize(json.loads(d))
            for (d,) in self._con.execute("SELECT dados FROM itens WHERE tipo=?", (nome,))
        ]
        itens += [
            deserialize(json.loads(d))
            for (d,) in self._con.execute("SELECT dados FROM log WHERE tipo=?", (nome,))
        ]
        for campo, valor in filtros.items():
            itens = [i for i in itens if getattr(i, campo, None) == valor]
        return itens

    def anexar(self, entidade: object) -> str:
        """Append-only: grava numa tabela de log sem UPDATE/DELETE."""
        dados = json.dumps(serialize(entidade), ensure_ascii=False)
        self._con.execute(
            "INSERT INTO log (tipo, dados) VALUES (?, ?)",
            (_tipo_nome(type(entidade)), dados),
        )
        self._con.commit()
        return _id_de(entidade) if hasattr(entidade, "id") else ""
