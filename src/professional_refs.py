from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Iterable

import requests


@dataclass(frozen=True)
class ProfessionalReference:
    category: str
    title: str
    source: str
    year: str
    url: str
    note: str = ""
    authors: str = ""
    journal: str = ""
    doi: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# Verified, stable authority pages. These are matched by topic;
# the language model never invents or constructs these citations.
_AUTHORITY_REFERENCES = [
    {
        "tags": {"古籍", "修复", "水洗", "脱酸", "水渍", "酸化", "纸张发黄"},
        "category": "国家标准",
        "title": "GB/T 21712-2008 古籍修复技术规范与质量要求",
        "source": "全国标准信息公共服务平台 / 国家标准",
        "year": "2008",
        "url": "https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=DE2DAA4125A5C0A5FBC8C5507FC52EF8",
        "note": "古籍修复领域的基础性国家标准，可用于核对修复技术要求和质量控制边界。",
    },
    {
        "tags": {"脱酸", "酸化"},
        "category": "国家标准化指导性技术文件",
        "title": "GB/Z 42964-2023 图书馆纸质文献脱酸工艺有效性评价方法",
        "source": "全国标准信息公共服务平台 / 国家标准",
        "year": "2023",
        "url": "https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=A488B94EE0988E4CF02FEAA845BE9031",
        "note": "面向图书馆纸质文献脱酸工艺有效性与均匀性评价，适合在涉及“酸化—脱酸”时优先查阅。",
    },
    {
        "tags": {"脱酸", "酸化"},
        "category": "专业机构资料",
        "title": "Mass Deacidification",
        "source": "Library of Congress Preservation",
        "year": "",
        "url": "https://www.loc.gov/preservation/scientists/projects/mass_deacid.html",
        "note": "美国国会图书馆关于纸质文献酸化与批量脱酸研究的专题资料。",
    },
    {
        "tags": {"酸化", "脱酸", "纸张发黄"},
        "category": "专业机构资料",
        "title": "The Deterioration and Preservation of Paper: Some Essential Facts",
        "source": "Library of Congress Preservation",
        "year": "",
        "url": "https://www.loc.gov/preservation/care/deterioratebrochure.html",
        "note": "介绍纸张劣化、酸化及保存干预的基础资料，可辅助理解病害成因与保护边界。",
    },
    {
        "tags": {"水洗", "脱酸", "酸化"},
        "category": "专业机构指南",
        "title": "Conservation Treatment for Bound Materials of Value",
        "source": "Northeast Document Conservation Center (NEDCC)",
        "year": "",
        "url": "https://www.nedcc.org/free-resources/preservation-leaflets/7.-conservation-procedures/7.6-conservation-treatment-for-bound-materials-of-value",
        "note": "涉及书页水洗、脱酸及处理前的材料稳定性判断，适合装帧文献保护场景参考。",
    },
    {
        "tags": {"水洗", "脱酸"},
        "category": "专业机构指南",
        "title": "Conservation Treatment for Works of Art and Unbound Artifacts on Paper",
        "source": "Northeast Document Conservation Center (NEDCC)",
        "year": "",
        "url": "https://www.nedcc.org/free-resources/preservation-leaflets/7.-conservation-procedures/7.5-conservation-treatment-for-works-of-art-and-unbound-artifacts-on-paper",
        "note": "介绍纸质材料的水洗、碱化/脱酸等处理，并强调处理前测试介质的水敏感性。",
    },
    {
        "tags": {"水渍", "水害"},
        "category": "专业机构指南",
        "title": "Emergency Salvage of Wet Books and Records",
        "source": "Northeast Document Conservation Center (NEDCC)",
        "year": "",
        "url": "https://www.nedcc.org/free-resources/preservation-leaflets/3.-emergency-management/3.6-emergency-salvage-of-wet-books-and-records",
        "note": "针对受水影响的图书与档案提供应急稳定和恢复原则，可辅助区分水害应急与后续修复处理。",
    },
    {
        "tags": {"水渍", "水害", "霉斑", "酸化", "纸张发黄"},
        "category": "专业机构资料",
        "title": "Caring for paper objects",
        "source": "Canadian Conservation Institute (CCI)",
        "year": "",
        "url": "https://www.canada.ca/en/conservation-institute/services/preventive-conservation/guidelines-collections/paper-objects.html",
        "note": "加拿大保护研究所关于纸质藏品劣化因素、环境风险和预防性保护的综合指南。",
    },
    {
        "tags": {"水渍", "水害", "霉斑"},
        "category": "专业机构资料",
        "title": "Basic care – Books",
        "source": "Canadian Conservation Institute (CCI)",
        "year": "2018",
        "url": "https://www.canada.ca/en/conservation-institute/services/care-objects/paper-books/basic-care-books.html",
        "note": "面向图书类藏品的基础保护资料，包含受潮、霉变、水害后的基本处置原则和专业求助边界。",
    },
    {
        "tags": {"古籍", "修复", "水洗", "脱酸", "酸化", "水渍", "纸张发黄"},
        "category": "国内专业机构",
        "title": "中国古籍保护网：古籍修复与文献保护相关资源",
        "source": "国家图书馆 / 中国古籍保护网",
        "year": "",
        "url": "https://www.nlc.cn/pcab/gjxf/gjxf_xfs/20250716_2647048.shtml",
        "note": "国家图书馆古籍保护专业平台的修复与文献保护资源，可用于继续追查国内研究和实践案例。",
    },
]


_TERM_MAP = {
    "脱酸": ["paper deacidification", "library materials", "conservation"],
    "酸化": ["acidic paper", "deacidification", "conservation"],
    "水洗": ["paper conservation washing", "book pages", "conservation"],
    "水渍": ["water damaged paper", "book conservation", "washing"],
    "水害": ["water damaged books", "paper conservation", "salvage"],
    "纸张发黄": ["paper deterioration", "yellowing", "conservation"],
    "霉斑": ["mold paper conservation", "books", "preservation"],
    "虫蛀": ["insect damage books", "paper conservation", "preservation"],
    "絮化": ["fragile paper", "paper deterioration", "conservation"],
    "书脑开裂": ["book binding repair", "spine damage", "conservation"],
}


def _unique(items: Iterable[str]) -> list[str]:
    seen = set()
    out = []
    for item in items:
        value = str(item).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def default_search_query(diseases: Iterable[str], processes: Iterable[str]) -> str:
    """Build a conservative English bibliographic query for Crossref."""
    terms: list[str] = []
    for item in list(diseases) + list(processes):
        terms.extend(_TERM_MAP.get(str(item), []))

    if not terms:
        terms = ["paper conservation", "rare books", "preservation"]

    # Keep the query compact and strongly anchored in conservation.
    terms = _unique(terms)
    query = " ".join(terms[:8])
    if "conservation" not in query.lower() and "preservation" not in query.lower():
        query += " paper conservation"
    return query


def sanitize_ai_query(value: str, fallback: str) -> str:
    """Accept only a short, plain search string from the LLM."""
    if not value:
        return fallback
    value = value.strip().splitlines()[0]
    value = re.sub(r"^[\-\*\d\.\)\s]+", "", value)
    value = value.strip("`\"' ")
    value = re.sub(r"\s+", " ", value)
    if len(value) < 5 or len(value) > 160:
        return fallback
    # A search query should not look like a fabricated citation.
    forbidden = ["doi:", "http://", "https://", "参考文献", "citation"]
    if any(x in value.lower() for x in forbidden):
        return fallback
    return value


def authority_references(
    diseases: Iterable[str],
    processes: Iterable[str],
    limit: int = 6,
) -> list[dict]:
    topics = set(str(x).strip() for x in list(diseases) + list(processes) if str(x).strip())
    topics.add("古籍")
    topics.add("修复")

    ranked = []
    for row in _AUTHORITY_REFERENCES:
        matched = topics & set(row["tags"])
        if not matched:
            continue

        score = len(matched)
        # Topic-specific standards and institution pages should appear before generic items.
        if "脱酸" in topics and "脱酸" in row["tags"]:
            score += 3
        if "水洗" in topics and "水洗" in row["tags"]:
            score += 3
        if "水渍" in topics and "水渍" in row["tags"]:
            score += 2
        if row["category"].startswith("国家"):
            score += 2

        ranked.append((score, row))

    ranked.sort(key=lambda x: x[0], reverse=True)

    out = []
    seen = set()
    for _, row in ranked:
        if row["url"] in seen:
            continue
        seen.add(row["url"])
        out.append({k: v for k, v in row.items() if k != "tags"})
        if len(out) >= limit:
            break
    return out


def _year_from_item(item: dict) -> str:
    for key in ("published-print", "published-online", "published", "issued", "created"):
        parts = item.get(key, {}).get("date-parts")
        if parts and parts[0]:
            return str(parts[0][0])
    return ""


def _authors_from_item(item: dict) -> str:
    authors = []
    for a in item.get("author", [])[:4]:
        family = str(a.get("family", "")).strip()
        given = str(a.get("given", "")).strip()
        name = " ".join(x for x in [given, family] if x)
        if name:
            authors.append(name)
    if len(item.get("author", [])) > 4:
        authors.append("et al.")
    return ", ".join(authors)


def search_crossref(
    query: str,
    rows: int = 5,
    timeout: int = 10,
) -> tuple[list[dict], str]:
    """
    Retrieve real scholarly metadata from Crossref.
    Returns (references, error_message). No citation is generated by an LLM.
    """
    params = {
        "query.bibliographic": query,
        "filter": "type:journal-article",
        "rows": max(1, min(int(rows), 8)),
        "select": "DOI,title,author,published-print,published-online,published,issued,created,container-title,URL,publisher,type",
    }
    headers = {
        "User-Agent": "AncientBookKnowledgeAssistant/1.0 (professional-reference-search)"
    }

    try:
        response = requests.get(
            "https://api.crossref.org/works",
            params=params,
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
        items = response.json().get("message", {}).get("items", [])
    except Exception as exc:
        return [], f"{type(exc).__name__}: {exc}"

    results = []
    seen_titles = set()

    for item in items:
        title_list = item.get("title") or []
        title = str(title_list[0]).strip() if title_list else ""
        if not title:
            continue

        norm = re.sub(r"\W+", "", title.lower())
        if not norm or norm in seen_titles:
            continue
        seen_titles.add(norm)

        journal_list = item.get("container-title") or []
        journal = str(journal_list[0]).strip() if journal_list else ""
        doi = str(item.get("DOI", "")).strip()
        url = f"https://doi.org/{doi}" if doi else str(item.get("URL", "")).strip()

        ref = ProfessionalReference(
            category="学术论文",
            title=title,
            source=str(item.get("publisher", "")).strip() or "Crossref",
            year=_year_from_item(item),
            url=url,
            authors=_authors_from_item(item),
            journal=journal,
            doi=doi,
            note="该条目来自 Crossref 学术元数据检索；请通过 DOI/原始页面核对摘要与全文后再用于专业判断。",
        )
        results.append(ref.to_dict())

    return results, ""
