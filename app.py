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
    page_title="古籍保护知识辅助系统",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
:root {
    --paper: #fbfaf6;
    --paper-deep: #f3f0e8;
    --ink: #292722;
    --muted: #777268;
    --line: #d8d2c7;
    --accent: #7a3730;
}

[data-testid="stAppViewContainer"] {
    background: var(--paper);
    color: var(--ink);
}

.block-container {
    padding-top: 1.25rem;
    padding-bottom: 3rem;
    max-width: 1180px;
}

[data-testid="stSidebar"] {
    background: var(--paper-deep);
    border-right: 1px solid var(--line);
}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: var(--ink);
}

/* 顶部题签：去掉渐变、胶囊标签和大圆角 */
.hero {
    padding: 0.9rem 0 1rem 0;
    margin-bottom: 1.2rem;
    border-bottom: 2px solid var(--accent);
}
.hero-title {
    font-family: "Noto Serif SC", "Songti SC", "STSong", serif;
    font-size: 2rem;
    font-weight: 700;
    letter-spacing: .04em;
    line-height: 1.35;
    color: var(--ink);
    margin: 0;
}
.hero-sub {
    color: var(--muted);
    font-size: .98rem;
    margin-top: .45rem;
}
.hero-meta {
    color: var(--accent);
    font-size: .86rem;
    margin-top: .55rem;
    letter-spacing: .03em;
}

/* 降低“AI SaaS 卡片感” */
div[data-testid="stMetric"] {
    border: 0;
    border-bottom: 1px solid var(--line);
    padding: .45rem .1rem;
    border-radius: 0;
    background: transparent;
}

div[data-testid="stVerticalBlockBorderWrapper"] {
    border-color: var(--line) !important;
    border-radius: 4px !important;
}

/* 按钮更像馆内业务系统 */
.stButton > button {
    border-radius: 3px;
    border: 1px solid #aaa397;
    background: #fffdfa;
    color: var(--ink);
    box-shadow: none;
}
.stButton > button:hover {
    border-color: var(--accent);
    color: var(--accent);
}
.stButton > button[kind="primary"] {
    background: var(--accent);
    border-color: var(--accent);
    color: white;
}

/* 输入框、选择框收敛圆角 */
[data-baseweb="select"] > div,
[data-baseweb="textarea"] textarea,
[data-baseweb="input"] input {
    border-radius: 3px !important;
}

/* 标签页更克制 */
button[data-baseweb="tab"] {
    font-weight: 500;
    padding-left: .75rem;
    padding-right: .75rem;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: var(--accent);
}

/* 标题更接近文献/档案系统 */
h1, h2, h3 {
    letter-spacing: .015em;
}
h2, h3 {
    color: var(--ink);
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
    st.header("知识库")
    st.caption("默认读取项目内置本体；需要时可临时上传其他 RDF / OWL / TTL 文件。")
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
    st.header("运行状态")
    if llm_client.configured():
        st.success("语言模型已连接")
        st.caption("语言模型用于整理表述；事实查询与规则推理由本体执行。")
    else:
        st.info("当前使用规则模式")
        st.caption("本体查询、属性链推理和知识检索可独立运行。")

    st.divider()
    st.caption("专业边界：系统只提供知识组织、检索和解释性辅助，不替代古籍修复专业人员的现场判断与操作。")


kb = load_kb(str(KNOWLEDGE), knowledge_signature(KNOWLEDGE))
agent = AncientBookAgent(engine, kb)

st.markdown(
    """
<div class="hero">
  <div class="hero-title">古籍智护</div>
  <div class="hero-sub">古籍保护知识辅助系统</div>
  <div class="hero-meta">用于馆藏古籍病害信息查询与修复知识辅助</div>
</div>
""",
    unsafe_allow_html=True,
)

books = engine.all_books()
if not books:
    st.warning("没有识别到“古籍文献”实例。请确认上传本体中的类名/属性名。")

tabs = st.tabs(
    ["辅助分析", "知识检索", "推理记录", "系统说明"]
)

# 1. 辅助分析：面向馆员的主工作区
with tabs[0]:
    st.markdown("#### 场景输入")
    st.caption("面向馆藏古籍病害问题，提供知识检索、关联分析与候选修复工序的可解释辅助建议。")
    c1, c2 = st.columns([1, 2], gap="large")
    with c1:
        selected = st.selectbox("可选：指定古籍档案", ["（自动识别）"] + books)
        st.caption("示例问题")
        if st.button("《天工开物》：水渍", use_container_width=True):
            st.session_state["q"] = "《天工开物》有水渍，模型能推荐什么修复工序？请解释推理路径。"
        if st.button("《天工开物》：纸张发黄", use_container_width=True):
            st.session_state["q"] = "《天工开物》纸张发黄，当前知识库能推荐什么？"
        if st.button("情景推演：史记 / 酸化", use_container_width=True):
            st.session_state["q"] = "假设史记当前存在酸化，模型能推演出什么候选修复工序？"

    with c2:
        q = st.text_area(
            "输入古籍与病害情况",
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
                st.success("已找到本体支持的候选修复工序")
            elif unresolved:
                st.warning("当前知识库暂无对应工序规则")
            else:
                st.info("未识别到可执行的病害—工序关系")

        if recs:
            st.markdown("### 本体推理结果")
            rows = []
            for r in recs:
                label = f"候选修复工序：{r.process}"
                if r.scenario_input:
                    label += "（情景推演）"
                with st.container(border=True):
                    st.markdown(f"#### {label}")
                    if r.scenario_input:
                        st.write(
                            f"用户临时输入“{r.book} 存在 {r.disease}”。"
                            f"当前本体已有“{r.disease} → 适用修复工序 → {r.process}”映射；"
                            f"在该情景事实成立的前提下，可由属性链得到候选修复工序“{r.process}”。"
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
                            "候选修复工序": r.process,
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
                    "系统不会自行补造候选修复工序；需在引入权威规范、专家经验或真实馆藏案例并经人工审核后再建立规则。"
                )

        if hits:
            st.markdown("### 依据检索")
            st.caption("以下内容用于补充解释与审计，不等同于自动生成新的修复规则。")
            for h in hits:
                with st.expander(h.source, expanded=False):
                    st.write(h.text[:900].strip())
                    st.caption(f"检索匹配度：{h.score:.2f}")

        if llm_client.configured():
            with st.expander("综合说明", expanded=True):
                st.markdown(result["answer"])

        st.info(
            "本系统不自动制定完整修复方案。候选修复工序仅作为知识辅助结果，"
            "最终修复决策应由专业人员结合古籍实物状态进行复核。"
        )

# 2. 知识检索：把“古籍档案”和“工序知识”归并为同一业务模块
with tabs[1]:
    st.markdown("#### 领域知识检索")
    st.caption("浏览本体中的古籍档案、病害关系与修复工序知识。")
    knowledge_tabs = st.tabs(["古籍档案", "修复工序"])

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
    st.markdown("#### 推理记录")
    st.caption("查看本体事实、属性链推理及系统处理过程，便于复核结果来源。")
    audit_tabs = st.tabs(["推理路径", "覆盖检查", "处理记录"])

    with audit_tabs[0]:
        if books:
            b = st.selectbox("选择要查看推理路径的古籍", books, key="graph_book")
            diseases = engine.object_values(b, "具有病害")
            profile = engine.book_profile(b)
            damage_text = profile.get("破损状况", "")

            if diseases:
                st.graphviz_chart(engine.graphviz_for_book(b), use_container_width=True)
                st.caption("实线为 RDF 中显式断言；虚线为应用按本体属性链规则计算得到的“建议修复工序”。")

                st.markdown("### 当前结构化关系")
                for d in diseases:
                    processes = engine.disease_processes(d)
                    if processes:
                        st.success(
                            f"{b} → 具有病害 → {d} → 适用修复工序 → {'、'.join(processes)}"
                        )
                    else:
                        st.warning(
                            f"{b} → 具有病害 → {d}；但“{d}”目前尚未建立适用修复工序映射。"
                        )
            else:
                st.info(
                    f"当前本体中，“{b}”暂无结构化“具有病害”对象属性关系，"
                    "因此没有可展示的修复推理路径。"
                )

                if damage_text:
                    st.warning(
                        f"档案中的“破损状况”文字著录为：{damage_text}。"
                        "该内容目前仅作为数据属性文本保存，尚未结构化为病害节点，"
                        "所以不会自动进入“具有病害 → 适用修复工序”的属性链推理。"
                    )
                else:
                    st.caption("该古籍档案中目前也没有“破损状况”文字著录。")

                st.markdown(
                    "**如需测试：** 可前往“辅助分析”输入一个临时病害情景。"
                    "系统会明确标记为“情景推演”，不会把临时输入冒充为本体中的馆藏事实。"
                )

    with audit_tabs[1]:
        st.markdown("### 古籍病害结构化覆盖检查")
        st.caption(
            "用于检查哪些古籍已经建立结构化病害关系、哪些仍只有文字著录，"
            "便于后续扩充本体。"
        )

        coverage_rows = []
        for book in books:
            profile = engine.book_profile(book)
            damage_text = profile.get("破损状况", "—") or "—"
            structured = engine.object_values(book, "具有病害")

            process_pairs = []
            for d in structured:
                ps = engine.disease_processes(d)
                if ps:
                    process_pairs.extend([f"{d}→{p}" for p in ps])

            if structured and process_pairs:
                status = "已有结构化病害，部分/全部可推理"
            elif structured:
                status = "已有结构化病害，暂无工序映射"
            elif damage_text != "—":
                status = "仅有破损文字著录，尚未结构化"
            else:
                status = "暂无病害数据"

            coverage_rows.append(
                {
                    "古籍": book,
                    "破损状况（文字）": damage_text,
                    "结构化病害": "、".join(structured) if structured else "—",
                    "已建立病害→工序映射": "；".join(process_pairs) if process_pairs else "—",
                    "状态": status,
                }
            )

        st.dataframe(
            pd.DataFrame(coverage_rows),
            use_container_width=True,
            hide_index=True,
        )
        st.info(
            "注意：“破损状况”文字著录不等于结构化病害关系。"
            "只有通过“具有病害”等对象属性建立的节点关系，才能参与当前属性链推理。"
        )

    with audit_tabs[2]:
        result = st.session_state.get("last_result")
        if not result:
            st.info("先在“辅助分析”运行一次分析，这里会显示系统处理记录。")
        else:
            st.caption("展示实体识别、本体查询、规则推理、知识检索与语言整理的执行顺序。")
            for i, step in enumerate(result["trace"], 1):
                with st.expander(f"{i}. {step['tool']}", expanded=True):
                    st.json(step)

# 4. 系统说明：保留方法、边界与技术路线
with tabs[3]:
    st.markdown("### 当前知识底座")
    stats = engine.ontology_stats()
    stats_df = pd.DataFrame(
        [{"项目": k, "数量": v} for k, v in stats.items()]
    )
    st.dataframe(stats_df, use_container_width=True, hide_index=True)
    st.caption("以上为当前加载本体的规模与规则覆盖情况。")

    st.markdown(
        """
### 系统定位
本系统通过领域本体组织古籍、病害、修复工序、材料与工具等知识，为高校图书馆馆员和古籍保护人员提供**知识检索、关联分析和候选修复工序的可解释辅助建议**。系统不自动制定完整修复方案，最终修复决策仍由专业人员结合古籍实物状态作出。

### 功能分层
- **辅助分析**：面向馆藏古籍病害问题，提供知识检索、关联分析、候选修复工序与综合说明；
- **知识检索**：浏览古籍档案与修复工序知识；
- **推理记录**：查看推理路径、结构化覆盖情况与系统处理记录；
- **系统说明**：说明技术路线、专业边界和当前知识覆盖范围。

### 技术路线
1. **真实领域本体**：直接读取 Protégé 导出的 RDF，保存古籍、病害、工序、材料、工具及语义关系；
2. **规则推理**：执行 RDF 中已存在的“具有病害 o 适用修复工序 ⊑ 建议修复工序”属性链逻辑，用于形成候选修复工序；
3. **本地知识检索**：从 `knowledge/` 检索可审计说明材料；正式应用应继续接入权威修复规范与馆内制度；
4. **LLM 辅助**：只负责自然语言理解和回答组织，本体事实与规则作为约束；
5. **可解释展示**：公开实体、规则、推理路径和处理记录。

### 当前 RDF 的真实边界
- 《天工开物》显式关联“水渍”“纸张发黄”；
- “水渍 → 适用修复工序 → 水洗”已存在，因此可形成《天工开物》的属性链推理；
- “酸化 → 适用修复工序 → 脱酸”已存在；
- 当前 RDF **没有**“史记 → 具有病害 → 酸化”的显式断言。因此“史记 + 酸化”只作为用户临时输入的**情景推演**，不冒充馆藏事实；
- “纸张发黄”目前没有工序映射，系统不会自行补造；
- 若用户输入《四库全书》等当前 RDF 中不存在的古籍名称，系统会保留该书名并标注为“用户输入对象”，只进行临时情景推演，不把它写成本体馆藏事实。

### 专业边界
所有候选修复工序均应由修复专业人员结合纸张强度、颜料稳定性、病害原因和馆藏实物状态复核。系统遵循“馆员主导、AI 辅助”，不替代专业修复决策。
"""
    )
