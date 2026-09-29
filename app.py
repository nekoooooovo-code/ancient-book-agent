from __future__ import annotations
from pathlib import Path
import pandas as pd
import streamlit as st

from src.ontology_engine import OntologyEngine
from src.rag import LocalKnowledgeBase
from src.agent import AncientBookAgent
from src import llm_client

ROOT = Path(__file__).parent
ONTOLOGY = ROOT / "data" / "天工开物古籍修复本体.rdf"
DEMO = ROOT / "data" / "demo_ontology.ttl"
KNOWLEDGE = ROOT / "knowledge"

st.set_page_config(
    page_title="古籍智护 Agent",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
.block-container {
    padding-top: 1.0rem;
    padding-bottom: 3rem;
    max-width: 1280px;
}
.hero {
    padding: 1.15rem 1.35rem;
    border: 1px solid rgba(49, 51, 63, 0.12);
    border-radius: 18px;
    background: linear-gradient(135deg, rgba(248,249,252,0.98), rgba(240,246,255,0.92));
    margin-bottom: 1rem;
}
.hero-title {
    font-size: 2.05rem;
    font-weight: 800;
    line-height: 1.25;
    margin: 0 0 .35rem 0;
}
.hero-sub {
    color: #5f6570;
    font-size: 1rem;
    margin-bottom: .8rem;
}
.badge {
    display: inline-block;
    padding: .18rem .62rem;
    border: 1px solid rgba(49,51,63,.22);
    border-radius: 999px;
    margin: 0 .35rem .3rem 0;
    font-size: .82rem;
    background: rgba(255,255,255,.8);
}
.section-note {
    color: #6b7280;
    font-size: .88rem;
}
div[data-testid="stMetric"] {
    border: 1px solid rgba(49, 51, 63, 0.10);
    padding: .72rem .82rem;
    border-radius: 14px;
    background: rgba(250,250,252,.65);
}
div[data-testid="stSidebar"] {
    border-right: 1px solid rgba(49,51,63,.08);
}
</style>
""",
    unsafe_allow_html=True,
)


def _ontology_path() -> Path:
    return ONTOLOGY if ONTOLOGY.exists() else DEMO


@st.cache_resource(show_spinner=False)
def load_builtin(path_text: str, modified_ns: int):
    # modified_ns is deliberately part of the cache key.
    # Updating the RDF in GitHub therefore invalidates the old cached ontology automatically.
    return OntologyEngine.from_path(Path(path_text))


@st.cache_resource(show_spinner=False)
def load_kb(folder_text: str, signature: tuple):
    return LocalKnowledgeBase(Path(folder_text))


def knowledge_signature(folder: Path) -> tuple:
    items = []
    if folder.exists():
        for p in sorted(folder.glob("**/*")):
            if p.is_file():
                try:
                    items.append((str(p.relative_to(folder)), p.stat().st_mtime_ns, p.stat().st_size))
                except OSError:
                    pass
    return tuple(items)


with st.sidebar:
    st.header("知识底座")
    st.caption("默认读取项目内置的真实 Protégé RDF；也可临时上传其他本体进行测试。")
    uploaded = st.file_uploader(
        "可选：上传新的 Protégé 本体（.rdf/.owl/.ttl）",
        type=["rdf", "owl", "ttl"],
    )

    if uploaded:
        try:
            engine = OntologyEngine.from_bytes(uploaded.getvalue(), uploaded.name)
            st.success(f"已载入：{uploaded.name}")
        except Exception as e:
            st.error(f"本体解析失败：{e}")
            path = _ontology_path()
            engine = load_builtin(str(path), path.stat().st_mtime_ns)
    else:
        path = _ontology_path()
        engine = load_builtin(str(path), path.stat().st_mtime_ns)
        if ONTOLOGY.exists():
            st.success("已加载：天工开物古籍修复本体.rdf")
        else:
            st.caption("当前使用项目内置 Demo 本体。")

    st.caption("属性链状态：" + ("✅ 已识别" if engine.has_property_chain() else "⚠️ 未识别"))

    st.divider()
    st.header("Agent 模式")
    if llm_client.configured():
        st.success("LLM 已连接")
        st.caption("大模型仅负责自然语言组织；事实查询与规则推理由本体执行。")
    else:
        st.info("当前为可审计规则模式")
        st.caption("无需大模型也可完成本体查询、属性链推理和知识检索。")

    st.divider()
    st.caption("专业边界：系统只提供知识组织、检索和解释性辅助，不替代古籍修复专业人员的现场判断与操作。")


kb = load_kb(str(KNOWLEDGE), knowledge_signature(KNOWLEDGE))
agent = AncientBookAgent(engine, kb)

st.markdown(
    """
<div class="hero">
  <div class="hero-title">📚 古籍智护 Agent</div>
  <div class="hero-sub">面向高校图书馆的古籍病害知识组织与可解释修复辅助决策原型</div>
  <span class="badge">真实 Protégé 本体</span>
  <span class="badge">馆员主导</span>
  <span class="badge">AI 辅助</span>
  <span class="badge">规则可审计</span>
  <span class="badge">推理可解释</span>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown("### 知识底座概览")
st.caption("当前加载本体的规模与规则覆盖情况，用于说明系统知识基础。")
stats = engine.ontology_stats()
metric_cols = st.columns(6)
for i, (k, v) in enumerate(stats.items()):
    metric_cols[i].metric(k, v)

books = engine.all_books()
if not books:
    st.warning("没有识别到“古籍文献”实例。请确认上传本体中的类名/属性名。")

tabs = st.tabs(
    ["🧭 智能分析", "📚 知识检索", "🔎 推理审计", "ℹ️ 系统说明"]
)

# 1. 智能分析：面向馆员的主工作区
with tabs[0]:
    st.markdown("#### 场景输入")
    st.caption("描述古籍与病害，系统将调用本体规则、知识库和大模型生成可解释的辅助分析结果。")
    c1, c2 = st.columns([1, 2], gap="large")
    with c1:
        selected = st.selectbox("可选：指定古籍档案", ["（自动识别）"] + books)
        st.caption("快速演示")
        if st.button("《天工开物》有水渍，模型能推荐什么？", use_container_width=True):
            st.session_state["q"] = "《天工开物》有水渍，模型能推荐什么修复工序？请解释推理路径。"
        if st.button("《天工开物》纸张发黄怎么办？", use_container_width=True):
            st.session_state["q"] = "《天工开物》纸张发黄，当前知识库能推荐什么？"
        if st.button("情景推演：史记 + 酸化", use_container_width=True):
            st.session_state["q"] = "假设史记当前存在酸化，模型能推演出什么候选修复工序？"

    with c2:
        q = st.text_area(
            "向智能体描述古籍与病害",
            value=st.session_state.get(
                "q",
                "《天工开物》存在水渍，请给出本体推理结果并解释依据。",
            ),
            height=122,
        )
        if st.button("开始分析", type="primary", use_container_width=True):
            default_book = None if selected == "（自动识别）" else selected
            st.session_state["last_result"] = agent.run(q, selected_book=default_book)

    result = st.session_state.get("last_result")
    if result:
        parsed = result["parsed"]
        recs = parsed["recommendations"]
        unresolved = parsed["unresolved"]
        hits = result["hits"]

        st.divider()
        st.markdown("## 分析结果")

        obj_col, status_col = st.columns([2, 1])
        with obj_col:
            if parsed["book"]:
                if parsed.get("book_in_ontology", False):
                    st.write(f"**分析对象：** {parsed['book']}　　**对象来源：** 本体已有古籍实例")
                else:
                    st.write(
                        f"**分析对象：** {parsed['book']}　　"
                        "**对象来源：** 用户输入（非当前本体已有古籍实例）"
                    )
            if parsed["diseases"]:
                source_label = parsed.get(
                    "disease_source",
                    "用户输入情景" if parsed["explicit_from_user"] else "本体已有病害",
                )
                st.write(f"**识别病害：** {'、'.join(parsed['diseases'])}　　**来源：** {source_label}")
        with status_col:
            if recs:
                st.success("已找到本体支持的候选工序")
            elif unresolved:
                st.warning("当前知识库暂无对应工序规则")
            else:
                st.info("未识别到可执行的病害—工序关系")

        if recs:
            st.markdown("### 本体推理结果")
            rows = []
            for r in recs:
                label = f"候选工序：{r.process}"
                if r.scenario_input:
                    label += "（情景推演）"
                with st.container(border=True):
                    st.markdown(f"#### {label}")
                    if r.scenario_input:
                        st.write(
                            f"用户临时输入“{r.book} 存在 {r.disease}”。"
                            f"当前本体已有“{r.disease} → 适用修复工序 → {r.process}”映射；"
                            f"在该情景事实成立的前提下，可由属性链得到候选工序“{r.process}”。"
                        )
                        basis = "用户输入情景 + 本体映射 + 属性链推演"
                    else:
                        st.write(
                            f"**推理路径：** {r.book} → 具有病害 → {r.disease} "
                            f"→ 适用修复工序 → {r.process} → 属性链得到“建议修复工序”。"
                        )
                        basis = "本体已有断言 + 属性链推理"
                    rows.append(
                        {
                            "古籍": r.book,
                            "病害": r.disease,
                            "候选工序": r.process,
                            "依据性质": basis,
                        }
                    )

            st.dataframe(
                pd.DataFrame(rows),
                use_container_width=True,
                hide_index=True,
            )

        if unresolved:
            st.markdown("### 知识边界")
            for d in unresolved:
                st.warning(
                    f"“{d}”在当前本体中尚未建立“适用修复工序”映射。"
                    "系统不会自行补造修复方案；需在引入权威规范、专家经验或真实馆藏案例并经人工审核后再建立规则。"
                )

        if hits:
            st.markdown("### 依据检索")
            st.caption("以下内容用于补充解释与审计，不等同于自动生成新的修复规则。")
            for h in hits:
                with st.expander(h.source, expanded=False):
                    st.write(h.text[:900].strip())
                    st.caption(f"检索匹配度：{h.score:.2f}")

        if llm_client.configured():
            with st.expander("AI 综合说明（基于本体结果）", expanded=True):
                st.markdown(result["answer"])

        st.info(
            "本系统用于知识组织、检索和解释性辅助，不替代古籍修复专业人员的现场判断与操作。"
        )

# 2. 知识检索：把“古籍档案”和“工序知识”归并为同一业务模块
with tabs[1]:
    st.markdown("#### 领域知识检索")
    st.caption("浏览本体中的古籍档案与修复工序知识，不涉及自动决策。")
    knowledge_tabs = st.tabs(["📖 古籍档案", "🧪 修复工序"])

    with knowledge_tabs[0]:
        if books:
            b = st.selectbox("选择古籍", books, key="profile_book")
            st.markdown("### 档案卡")
            profile = engine.book_profile(b)
            for k, v in profile.items():
                if k != "古籍":
                    st.write(f"**{k}：** {v}")

            st.markdown("### 结构化病害关系")
            diseases = engine.object_values(b, "具有病害")
            if diseases:
                for d in diseases:
                    ps = engine.disease_processes(d)
                    if ps:
                        st.write(f"- **{b}** —具有病害→ **{d}** —适用修复工序→ **{'、'.join(ps)}**")
                    else:
                        st.write(f"- **{b}** —具有病害→ **{d}**（暂无工序映射）")
            else:
                st.info("该古籍在当前 RDF 中暂无“具有病害”对象属性断言。")

    with knowledge_tabs[1]:
        processes = engine.all_processes()
        if processes:
            p = st.selectbox("选择工序", processes, key="process_book")
            prof = engine.process_profile(p)
            st.markdown(f"### {p}")
            for k in ["前置工序", "后续工序", "使用工具", "使用原料", "产出成品"]:
                vals = prof[k]
                st.write(f"**{k}：** " + ("、".join(vals) if vals else "—"))

# 3. 推理审计：把“推理图谱”和“Agent轨迹”归并，强调可解释/可审计
with tabs[2]:
    st.markdown("#### 推理审计")
    st.caption("查看系统如何从本体事实、属性链与工具调用得到结果，便于馆员复核。")
    audit_tabs = st.tabs(["🕸️ 推理路径", "🧰 Agent 轨迹"])

    with audit_tabs[0]:
        if books:
            b = st.selectbox("选择要查看推理路径的古籍", books, key="graph_book")
            st.graphviz_chart(engine.graphviz_for_book(b), use_container_width=True)
            st.caption("实线为 RDF 中显式断言；虚线为应用按本体属性链规则计算得到的“建议修复工序”。")

    with audit_tabs[1]:
        result = st.session_state.get("last_result")
        if not result:
            st.info("先在“智能分析”运行一次分析，这里会显示 Agent 的工具调用轨迹。")
        else:
            st.caption("展示实体理解、本体查询、规则推理、本地知识检索与大模型组织回答的执行顺序。")
            for i, step in enumerate(result["trace"], 1):
                with st.expander(f"{i}. {step['tool']}", expanded=True):
                    st.json(step)

# 4. 系统说明：保留方法、边界与技术路线
with tabs[3]:
    st.markdown(
        """
### 系统定位
本原型不是自动修复系统，而是面向高校图书馆馆员和古籍保护人员的**知识组织与辅助决策工具**。

### 功能分层
- **智能分析**：面向实际业务问题，输出候选工序、知识边界与AI综合说明；
- **知识检索**：浏览古籍档案与修复工序知识；
- **推理审计**：查看推理路径与 Agent 工具调用轨迹；
- **系统说明**：说明技术路线、专业边界和当前知识覆盖范围。

### 技术路线
1. **真实领域本体**：直接读取 Protégé 导出的 RDF，保存古籍、病害、工序、材料、工具及语义关系；
2. **规则推理**：执行 RDF 中已存在的“具有病害 o 适用修复工序 ⊑ 建议修复工序”属性链逻辑；
3. **本地知识检索**：从 `knowledge/` 检索可审计说明材料；正式应用应继续接入权威修复规范与馆内制度；
4. **LLM 辅助**：只负责自然语言理解和回答组织，本体事实与规则作为约束；
5. **可解释展示**：公开实体、规则、推理路径和 Agent 工具轨迹。

### 当前 RDF 的真实边界
- 《天工开物》显式关联“水渍”“纸张发黄”；
- “水渍 → 适用修复工序 → 水洗”已存在，因此可形成《天工开物》的属性链推理；
- “酸化 → 适用修复工序 → 脱酸”已存在；
- 当前 RDF **没有**“史记 → 具有病害 → 酸化”的显式断言。因此“史记 + 酸化”只作为用户临时输入的**情景推演**，不冒充馆藏事实；
- “纸张发黄”目前没有工序映射，系统不会自行补造；
- 若用户输入《四库全书》等当前 RDF 中不存在的古籍名称，系统会保留该书名并标注为“用户输入对象”，只进行临时情景推演，不把它写成本体馆藏事实。

### 专业边界
所有修复建议均应由修复专业人员结合纸张强度、颜料稳定性、病害原因和馆藏实物状态复核。系统遵循“馆员主导、AI 辅助”。
"""
    )
