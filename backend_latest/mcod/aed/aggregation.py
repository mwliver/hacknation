"""
National AED dataset: normalisation, deduplication and merging of rows from many sources (pure functions).

Deduplication rules:
  1. the same pair (zrodlo_danych, zrodlo_id) is the same AED;
  2. rows from different sources (different resources) closer than 25 m, with the same locality
     (and the same street when both are known) are duplicates;
  3. when merging, the row from the source with a higher priority wins
     (WLASCICIEL > JST > APLIKACJA > INNE > OSM), on a tie – the newer data_aktualizacji;
     empty fields of the winner are filled from the other rows in the same order.
Clusters are built with union-find, so duplicates are transitive (A~B and B~C => A, B, C are one AED).
"""

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from mcod.aed import schema
from mcod.aed.geo import close_pairs

DUPLICATE_RADIUS_M = 25.0
_SPACES = re.compile(r"\s+")
_POSTAL_DIGITS = re.compile(r"^(\d{2})-?(\d{3})$")
_STREET_PREFIX = re.compile(r"^(ul|al|pl|os|aleja|ulica|plac|osiedle)\.?\s+")


@dataclass
class SourceRow:
    """One validated row of one source file."""

    resource_id: Optional[int]
    data: Dict[str, str]

    @property
    def source_key(self) -> Optional[Tuple[str, str]]:
        source_id = self.data.get("zrodlo_id")
        return (self.data.get("zrodlo_danych", ""), source_id) if source_id else None

    @property
    def point(self) -> Tuple[float, float]:
        return float(self.data["szerokosc_geograficzna"]), float(self.data["dlugosc_geograficzna"])


@dataclass
class MergedRecord:
    data: Dict[str, str]
    rows: List[SourceRow] = field(default_factory=list)

    @property
    def sources_count(self) -> int:
        return len(self.rows)


def normalize_row(raw: Dict[str, str]) -> Dict[str, str]:
    """Trim, single spaces, upper-case dictionary values, postal code as NN-NNN, booleans as true/false."""
    enums = schema.enums()
    known = set(schema.all_field_names())
    row = {}
    for name in known:
        value = _SPACES.sub(" ", str(raw.get(name, "") or "").strip())
        f = schema.field(name)
        if name in enums or name == "zrodlo_danych":
            value = value.upper()
        elif f["type"] == "boolean" and value:
            value = value.lower()
        elif name == "kod_pocztowy":
            match = _POSTAL_DIGITS.match(value)
            if match:
                value = "{}-{}".format(*match.groups())
        row[name] = value
    return row


def _comparable(text: str) -> str:
    text = (text or "").strip().lower().replace("ł", "l")
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _comparable_street(text: str) -> str:
    return _STREET_PREFIX.sub("", _comparable(text)).strip()


def _same_place(a: SourceRow, b: SourceRow) -> bool:
    if _comparable(a.data.get("miejscowosc")) != _comparable(b.data.get("miejscowosc")):
        return False
    street_a, street_b = _comparable_street(a.data.get("ulica")), _comparable_street(b.data.get("ulica"))
    return not (street_a and street_b) or street_a == street_b


class _UnionFind:
    def __init__(self, size: int):
        self.parent = list(range(size))

    def find(self, i: int) -> int:
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return i

    def union(self, a: int, b: int) -> None:
        root_a, root_b = self.find(a), self.find(b)
        if root_a != root_b:
            self.parent[max(root_a, root_b)] = min(root_a, root_b)


def cluster(rows: Sequence[SourceRow]) -> List[List[int]]:
    """Returns clusters as lists of row indexes (in input order)."""
    uf = _UnionFind(len(rows))
    by_source_key: Dict[Tuple[str, str], int] = {}
    for idx, row in enumerate(rows):
        key = row.source_key
        if key is None:
            continue
        if key in by_source_key:
            uf.union(by_source_key[key], idx)
        else:
            by_source_key[key] = idx
    for i, j, _ in close_pairs([r.point for r in rows], DUPLICATE_RADIUS_M):
        if rows[i].resource_id != rows[j].resource_id and _same_place(rows[i], rows[j]):
            uf.union(i, j)
    groups: Dict[int, List[int]] = {}
    for idx in range(len(rows)):
        groups.setdefault(uf.find(idx), []).append(idx)
    return list(groups.values())


# Fields describing where a row comes from are never mixed between sources.
IDENTITY_FIELDS = ("id_aed", "dysponent", "zrodlo_danych", "zrodlo_id")


def _source_rank(row: SourceRow) -> int:
    order = schema.source_priority()
    source = row.data.get("zrodlo_danych", "")
    return order.index(source) if source in order else len(order)


def order_by_priority(rows: Sequence[SourceRow]) -> List[SourceRow]:
    """Higher source priority first; on a tie the newer data_aktualizacji first (ISO dates sort as text)."""
    by_date = sorted(rows, key=lambda r: r.data.get("data_aktualizacji", ""), reverse=True)
    return sorted(by_date, key=_source_rank)  # stable sort keeps the date order within a rank


def merge(rows: Sequence[SourceRow]) -> MergedRecord:
    ordered = order_by_priority(rows)
    merged = dict(ordered[0].data)
    for other in ordered[1:]:
        for name, value in other.data.items():
            if name not in IDENTITY_FIELDS and not merged.get(name) and value:
                merged[name] = value
    return MergedRecord(data=merged, rows=ordered)


def aggregate(rows: Sequence[SourceRow]) -> List[MergedRecord]:
    normalized = [SourceRow(r.resource_id, normalize_row(r.data)) for r in rows]
    return [merge([normalized[i] for i in group]) for group in cluster(normalized)]
