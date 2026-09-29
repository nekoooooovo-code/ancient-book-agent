from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import re

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None


@dataclass
class Hit:
    source: str
    text: str
    score: float


def _tokens(text: str) -> set[str]:
    text = re.sub(r"\s+", "", text.lower())
    grams = {text[i:i+2] for i in range(max(0, len(text)-1))}
    words = set(re.findall(r"[a-z0-9_\-]+", text))
    return {x for x in grams | words if x}


class LocalKnowledgeBase:
    def __init__(self, folder: str | Path):
        self.folder = Path(folder)
        self.chunks = self._load()

    def _load(self):
        chunks = []
        for path in sorted(self.folder.glob("**/*")):
            if not path.is_file():
                continue
            text = ""
            try:
                if path.suffix.lower() in {".md", ".txt"}:
                    text = path.read_text(encoding="utf-8")
                elif path.suffix.lower() == ".pdf" and PdfReader:
                    reader = PdfReader(str(path))
                    text = "\n".join((p.extract_text() or "") for p in reader.pages)
            except Exception:
                continue
            for block in re.split(r"\n\s*\n", text):
                block = block.strip()
                if len(block) >= 20:
                    chunks.append((path.name, block))
        return chunks

    def search(self, query: str, top_k: int = 3) -> list[Hit]:
        q = _tokens(query)
        scored = []
        for source, text in self.chunks:
            t = _tokens(text)
            if not q or not t:
                continue
            inter = len(q & t)
            score = inter / max(1, len(q))
            if score > 0:
                scored.append(Hit(source, text, score))
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:top_k]
