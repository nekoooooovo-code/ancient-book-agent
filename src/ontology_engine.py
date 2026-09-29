from __future__ import annotations
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Iterable, Optional
import re

from rdflib import Graph, RDF, RDFS, OWL, URIRef, Literal


def local_name(term) -> str:
    if term is None:
        return ""
    s = str(term)
    if "#" in s:
        return s.rsplit("#", 1)[-1]
    return s.rstrip("/").rsplit("/", 1)[-1]


@dataclass
class Recommendation:
    book: str
    disease: str
    process: str
    inferred: bool = True
    scenario_input: bool = False


class OntologyEngine:
    """RDF/OWL access layer for the uploaded Protégé ontology.

    The ontology already stores an OWL property chain:
      具有病害 o 适用修复工序 ⊑ 建议修复工序

    RDFLib is used for portable parsing. For the web demo, the same chain is also
    evaluated explicitly so that the application does not depend on a separate
    desktop DL reasoner at runtime.
    """

    def __init__(self, graph: Graph):
        self.g = graph
        self._name_index = {}
        for s in set(self.g.all_nodes()):
            if isinstance(s, URIRef):
                self._name_index.setdefault(local_name(s), s)

    @classmethod
    def from_path(cls, path: str | Path):
        path = Path(path)
        g = Graph()
        g.parse(path.as_posix(), format=cls._guess_format(path.name))
        return cls(g)

    @classmethod
    def from_bytes(cls, content: bytes, filename: str = "ontology.rdf"):
        g = Graph()
        g.parse(source=BytesIO(content), format=cls._guess_format(filename))
        return cls(g)

    @staticmethod
    def _guess_format(name: str) -> Optional[str]:
        n = name.lower()
        if n.endswith(".ttl"):
            return "turtle"
        if n.endswith(".nt"):
            return "nt"
        if n.endswith(".jsonld") or n.endswith(".json-ld"):
            return "json-ld"
        return "xml"

    def uri(self, name: str) -> Optional[URIRef]:
        return self._name_index.get(name)

    def names_of_type(self, class_name: str) -> list[str]:
        c = self.uri(class_name)
        if not c:
            return []
        return sorted({local_name(s) for s in self.g.subjects(RDF.type, c)})

    def object_values(self, subject_name: str, prop_name: str) -> list[str]:
        s, p = self.uri(subject_name), self.uri(prop_name)
        if not s or not p:
            return []
        return sorted({local_name(o) for o in self.g.objects(s, p) if isinstance(o, URIRef)})

    def subjects_for(self, prop_name: str, object_name: str | None = None) -> list[str]:
        p = self.uri(prop_name)
        if not p:
            return []
        o = self.uri(object_name) if object_name else None
        return sorted({local_name(s) for s in self.g.subjects(p, o) if isinstance(s, URIRef)})

    def data_values(self, subject_name: str, prop_name: str) -> list[str]:
        s, p = self.uri(subject_name), self.uri(prop_name)
        if not s or not p:
            return []
        return [str(o) for o in self.g.objects(s, p) if isinstance(o, Literal)]

    def all_books(self) -> list[str]:
        names = set(self.names_of_type("古籍文献"))
        names |= set(self.subjects_for("具有病害"))
        return sorted(names)

    def all_diseases(self) -> list[str]:
        # In the real RDF, 水渍/纸张发黄 are NamedIndividuals whose 病害 type is
        # inferable from the range of “具有病害”, rather than asserted directly.
        names = set(self.names_of_type("病害"))
        p_has = self.uri("具有病害")
        if p_has:
            names |= {local_name(o) for o in self.g.objects(None, p_has) if isinstance(o, URIRef)}
        p_app = self.uri("适用修复工序")
        if p_app:
            names |= {local_name(s) for s in self.g.subjects(p_app, None) if isinstance(s, URIRef)}
        return sorted(names)

    def all_processes(self) -> list[str]:
        names = set(self.names_of_type("现代修复工序-延伸"))
        names |= set(self.names_of_type("工序"))
        return sorted(names)

    def ontology_stats(self) -> dict:
        classes = set(self.g.subjects(RDF.type, OWL.Class))
        obj_props = set(self.g.subjects(RDF.type, OWL.ObjectProperty))
        data_props = set(self.g.subjects(RDF.type, OWL.DatatypeProperty))
        individuals = set(self.g.subjects(RDF.type, OWL.NamedIndividual))
        mappings = []
        for d in self.all_diseases():
            for p in self.disease_processes(d):
                mappings.append((d, p))
        return {
            "三元组": len(self.g),
            "类": len(classes),
            "命名个体": len(individuals),
            "对象属性": len(obj_props),
            "数据属性": len(data_props),
            "病害—工序映射": len(mappings),
        }

    def has_property_chain(self) -> bool:
        rec = self.uri("建议修复工序")
        has = self.uri("具有病害")
        applicable = self.uri("适用修复工序")
        if not rec or not has or not applicable:
            return False
        for head in self.g.objects(rec, OWL.propertyChainAxiom):
            vals = []
            cur = head
            seen = set()
            while cur and cur != RDF.nil and cur not in seen:
                seen.add(cur)
                first = self.g.value(cur, RDF.first)
                if first is not None:
                    vals.append(first)
                cur = self.g.value(cur, RDF.rest)
            if vals == [has, applicable]:
                return True
        return False

    def book_profile(self, book: str) -> dict:
        return {
            "古籍": book,
            "版本类型": "；".join(self.data_values(book, "版本类型")) or "—",
            "行款版式": "；".join(self.data_values(book, "行款版式")) or "—",
            "装帧形式": "；".join(self.data_values(book, "装帧形式")) or "—",
            "破损状况": "；".join(self.data_values(book, "破损状况")) or "—",
            "结构化病害": "、".join(self.object_values(book, "具有病害")) or "—",
        }

    def process_profile(self, process: str) -> dict:
        return {
            "工序": process,
            "使用工具": self.object_values(process, "使用工具"),
            "使用原料": self.object_values(process, "使用原料"),
            "前置工序": self.object_values(process, "前置工序"),
            "后续工序": self.object_values(process, "后续工序"),
            "产出成品": self.object_values(process, "产出成品"),
        }

    def disease_processes(self, disease: str) -> list[str]:
        return self.object_values(disease, "适用修复工序")

    def recommendations(self, book: str, diseases: Optional[Iterable[str]] = None,
                        explicit_from_user: bool = False) -> list[Recommendation]:
        asserted = set(self.object_values(book, "具有病害")) if self.uri(book) else set()
        if diseases is None:
            diseases = sorted(asserted)
        result: list[Recommendation] = []
        for disease in diseases:
            scenario = explicit_from_user and disease not in asserted
            for process in self.disease_processes(disease):
                result.append(Recommendation(
                    book=book,
                    disease=disease,
                    process=process,
                    inferred=True,
                    scenario_input=scenario,
                ))
        return result

    def unresolved_diseases(self, diseases: Iterable[str]) -> list[str]:
        return [d for d in diseases if not self.disease_processes(d)]

    def find_mentions(self, text: str) -> dict:
        books = [x for x in self.all_books() if x in text]
        diseases = [x for x in self.all_diseases() if x in text]
        processes = [x for x in self.all_processes() if x in text]
        return {"books": books, "diseases": diseases, "processes": processes}

    def infer_from_text(self, text: str, default_book: Optional[str] = None) -> dict:
        mentions = self.find_mentions(text)

        # Prefer an ontology-known title. If the user names a work that is not yet
        # an ontology individual, keep the title inside 《》 as a temporary
        # scenario object instead of dropping it.
        title_match = re.search(r"《\s*([^》]{1,80}?)\s*》", text)
        user_title = title_match.group(1).strip() if title_match else None

        if mentions["books"]:
            book = mentions["books"][0]
            book_source = "本体已有实例"
        elif default_book:
            book = default_book
            book_source = "本体已有实例" if self.uri(book) else "用户指定对象"
        elif user_title:
            book = user_title
            book_source = "用户输入对象"
        else:
            book = None
            book_source = "未指定"

        book_in_ontology = bool(book and self.uri(book))
        explicit_diseases = mentions["diseases"]

        if book and book_in_ontology and not explicit_diseases:
            diseases = self.object_values(book, "具有病害")
            explicit_from_user = False
        else:
            diseases = explicit_diseases
            explicit_from_user = bool(explicit_diseases)

        recs = self.recommendations(
            book or "未指定古籍", diseases, explicit_from_user=explicit_from_user
        ) if diseases else []
        unresolved = self.unresolved_diseases(diseases)

        return {
            "book": book,
            "book_source": book_source,
            "book_in_ontology": book_in_ontology,
            "diseases": diseases,
            "recommendations": recs,
            "unresolved": unresolved,
            "mentions": mentions,
            "explicit_from_user": explicit_from_user,
        }

    def graphviz_for_book(self, book: str) -> str:
        diseases = self.object_values(book, "具有病害")
        lines = ["digraph G {", 'rankdir="LR";', 'node [shape=box, style="rounded"];']
        safe_book = book.replace('"', '\\"')
        lines.append(f'"{safe_book}" [shape=box];')
        for d in diseases:
            sd = d.replace('"', '\\"')
            lines.append(f'"{safe_book}" -> "{sd}" [label="具有病害"];')
            for p in self.disease_processes(d):
                sp = p.replace('"', '\\"')
                lines.append(f'"{sd}" -> "{sp}" [label="适用修复工序"];')
                lines.append(f'"{safe_book}" -> "{sp}" [label="建议修复工序（属性链推理）", style=dashed];')
        lines.append("}")
        return "\n".join(lines)
