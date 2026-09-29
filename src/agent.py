from __future__ import annotations
from dataclasses import asdict
from .ontology_engine import OntologyEngine
from .rag import LocalKnowledgeBase
from . import llm_client

SYSTEM = """你是高校图书馆古籍保护辅助智能体。回答必须严格受提供的本体事实与本地知识检索内容约束。

规则：
1. 先给出结论，再简要解释本体推理依据。
2. 不要机械重复整段知识库原文，不要把检索结果逐条照抄。
3. 本体事实、用户临时情景与知识库补充说明必须区分清楚。
4. 不得把模型验证映射包装成普遍适用的专业修复规范。
5. 若当前本体没有病害—工序映射，明确说明“当前知识库暂无规则”，不得自行补造工序。
6. 若用户输入的病害与本体已有断言一致，应说明“用户输入与本体已有断言一致”。
7. 若用户输入一个本体中不存在的古籍或不存在的病害断言，只能称为“情景推演”，不得称为馆藏事实。
8. 始终强调馆员/修复专业人员主导，AI只负责自然语言理解、知识组织、检索与解释性辅助。
9. 默认用2—4段简洁中文回答，除非确有必要，不使用长列表。
"""


class AncientBookAgent:
    def __init__(self, engine: OntologyEngine, kb: LocalKnowledgeBase):
        self.engine = engine
        self.kb = kb

    def run(self, question: str, selected_book: str | None = None) -> dict:
        trace = []
        trace.append({"tool": "entity_understanding", "input": question})
        parsed = self.engine.infer_from_text(question, default_book=selected_book)

        # Reconcile user-entered diseases with ontology assertions so the UI can
        # distinguish "new scenario" from "user input that matches known facts".
        ontology_diseases = set()
        if parsed.get("book") and parsed.get("book_in_ontology", False):
            ontology_diseases = set(self.engine.object_values(parsed["book"], "具有病害"))

        entered = set(parsed.get("diseases", []))
        if parsed["explicit_from_user"]:
            if entered and entered.issubset(ontology_diseases):
                disease_source = "用户输入，且与本体已有断言一致"
            elif entered & ontology_diseases:
                disease_source = "用户输入；部分与本体已有断言一致"
            else:
                disease_source = "用户输入情景"
        else:
            disease_source = "本体已有断言/档案"

        parsed["disease_source"] = disease_source

        trace[-1]["output"] = {
            "book": parsed["book"],
            "diseases": parsed["diseases"],
            "mentions": parsed["mentions"],
            "disease_source": disease_source,
        }

        trace.append({"tool": "ontology_query_and_rule", "input": {"book": parsed["book"], "diseases": parsed["diseases"]}})
        recs = [asdict(r) for r in parsed["recommendations"]]
        trace[-1]["output"] = {
            "property_chain_present": self.engine.has_property_chain(),
            "recommendations": recs,
            "unresolved": parsed["unresolved"],
        }

        trace.append({"tool": "local_rag", "input": question})
        hits = self.kb.search(question + " " + " ".join(parsed["diseases"]), top_k=3)
        trace[-1]["output"] = [{"source": h.source, "score": round(h.score, 3)} for h in hits]

        answer = self._template_answer(parsed, hits)
        if llm_client.configured():
            trace.append({"tool": "llm_generation", "input": "ontology facts + local knowledge hits"})
            context = self._context(parsed, hits)
            try:
                answer = llm_client.chat(
                    SYSTEM,
                    f"""用户问题：{question}

可用事实：
{context}

请基于以上事实生成面向馆员的简洁说明：
- 第一段直接说明当前本体得到的候选工序或“暂无规则”；
- 第二段说明推理依据及事实来源；
- 最后一两句说明专业边界；
- 不要逐条复述知识库检索结果，不要引入可用事实之外的新修复步骤。"""
                )
                trace[-1]["output"] = "LLM response generated"
            except Exception as e:
                trace[-1]["output"] = f"LLM failed; fallback template used: {type(e).__name__}"

        return {"answer": answer, "parsed": parsed, "hits": hits, "trace": trace}

    def _context(self, parsed, hits):
        lines = []
        if parsed["book"]:
            lines.append(f"古籍：{parsed['book']}")
        lines.append("病害：" + ("、".join(parsed["diseases"]) or "未识别"))
        for r in parsed["recommendations"]:
            if r.scenario_input:
                lines.append(f"情景推演：用户将 {r.book} 的当前病害设为 {r.disease}；本体中 {r.disease} —适用修复工序→ {r.process}，因此在临时加入该病害事实后，属性链可推出候选工序 {r.process}。")
            else:
                lines.append(f"本体属性链：{r.book} —具有病害→ {r.disease} —适用修复工序→ {r.process}；因此 {r.book} —建议修复工序→ {r.process}。")
        for d in parsed["unresolved"]:
            lines.append(f"病害 {d}：当前本体未建立适用修复工序映射。")
        for h in hits:
            lines.append(f"知识库[{h.source}]（仅作补充说明）：{h.text[:260]}")
        return "\n".join(lines)

    def _template_answer(self, parsed, hits):
        lines = []
        if parsed["book"]:
            lines.append(f"**分析对象：{parsed['book']}**")
        if parsed["diseases"]:
            src = "用户输入的情景病害" if parsed["explicit_from_user"] else "本体档案中的结构化病害"
            lines.append(f"{src}：" + "、".join(parsed["diseases"]))
        else:
            lines.append("未识别到病害实体。请明确输入病害名称，或选择一个已有古籍档案。")

        if parsed["recommendations"]:
            lines.append("\n**本体规则得到的候选工序：**")
            for r in parsed["recommendations"]:
                if r.scenario_input:
                    lines.append(f"- **{r.process}（情景推演）**：用户输入“{r.book} 存在 {r.disease}”；本体已有“{r.disease} →适用修复工序→ {r.process}”。临时加入病害事实后，可由属性链推出候选工序。")
                else:
                    lines.append(f"- **{r.process}**：{r.book} →具有病害→ {r.disease} →适用修复工序→ {r.process}，再由属性链得到“建议修复工序”。")
        if parsed["unresolved"]:
            lines.append("\n**当前知识库暂无规则：**" + "、".join(parsed["unresolved"]))
            lines.append("这些病害需要补充权威规范、专家经验或真实馆藏案例后才能建立可审计映射。")

        if hits:
            lines.append("\n**本地知识库检索：**")
            for h in hits:
                lines.append(f"- {h.source}：{h.text[:180].strip()}")

        lines.append("\n> 本系统用于知识组织、检索和解释性辅助，不替代古籍修复专业人员的现场判断与操作。")
        return "\n".join(lines)
