from __future__ import annotations
from pathlib import Path
import pandas as pd
import streamlit as st

from src.ontology_engine import OntologyEngine
from src.rag import LocalKnowledgeBase
from src.agent import AncientBookAgent
from src import llm_client
from src import professional_refs

ROOT = Path(__file__).parent
ONTOLOGY = ROOT / "data" / "天工开物古籍修复本体.rdf"
DEMO = ROOT / "data" / "demo_ontology.ttl"
KNOWLEDGE = ROOT / "knowledge"

st.set_page_config(
    page_title="古籍保护知识辅助系统",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed",
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
    font-size: 1.9rem;
    font-weight: 700;
    letter-spacing: .04em;
    line-height: 1.35;
    color: var(--ink);
    margin: 0;
}
.hero-sub {
    color: var(--muted);
    font-size: 1rem;
    margin-top: .45rem;
}
.hero-meta {
    color: var(--accent);
    font-size: .84rem;
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
h1, h2, h3, h4 {
    letter-spacing: .015em;
    color: var(--ink);
}

/* ------------------------------
   字号层级
   以 15.5px 正文为基准，避免大小跳跃
------------------------------ */

/* 页面正文 */
.stMarkdown p,
.stMarkdown li,
[data-testid="stAlert"] p {
    font-size: 15.5px;
    line-height: 1.72;
}

/* 查询结果等一级内容标题 */
h2 {
    font-size: 24px !important;
    line-height: 1.35 !important;
    margin-top: 1.45rem !important;
    margin-bottom: .75rem !important;
}

/* “古籍病害查询 / 候选修复工序 / 专业参考资料” */
h3 {
    font-size: 20px !important;
    line-height: 1.4 !important;
    margin-top: 1.2rem !important;
    margin-bottom: .55rem !important;
}

/* “水洗 / 标准与专业机构资料 / 相关学术研究” */
h4 {
    font-size: 17px !important;
    line-height: 1.45 !important;
    margin-top: 1rem !important;
    margin-bottom: .4rem !important;
}

/* 辅助说明：明显小于正文，但不至于太小 */
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] p,
.stCaption {
    font-size: 12.8px !important;
    line-height: 1.55 !important;
    color: var(--muted) !important;
}

/* 表单标签 */
[data-testid="stWidgetLabel"] p {
    font-size: 14px !important;
    font-weight: 600 !important;
}

/* 输入内容 */
[data-baseweb="textarea"] textarea,
[data-baseweb="input"] input,
[data-baseweb="select"] {
    font-size: 14.5px !important;
}

/* 按钮文字 */
.stButton > button,
.stButton > button p {
    font-size: 14px !important;
    font-weight: 500 !important;
}

/* 顶部一级标签 */
button[data-baseweb="tab"] {
    font-size: 15px !important;
}

/* 折叠项标题 */
details summary,
[data-testid="stExpander"] summary p {
    font-size: 14.5px !important;
    font-weight: 600 !important;
}

/* 侧栏比主页面稍小 */
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
    font-size: 13.5px !important;
    line-height: 1.6 !important;
}

/* 强调文字不要显得过粗 */
.stMarkdown strong {
    font-weight: 600;
}

/* 表格上下留白更紧凑 */
[data-testid="stDataFrame"] {
    margin-top: .35rem;
    margin-bottom: .7rem;
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
    st.header("数据源（高级）")
    st.caption("系统默认使用内置知识库。仅在测试其他本体时需要这里的设置。")
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
    st.header("系统状态")
    if llm_client.configured():
        st.success("语言模型已连接")
        st.caption("语言模型用于整理表述；事实查询与规则推理由本体执行。")
    else:
        st.info("当前使用规则模式")
        st.caption("本体查询、属性链推理和知识检索可独立运行。")

    st.divider()
    st.caption("使用边界：系统提供知识查询与候选工序参考，最终修复决策由专业人员结合实物状态作出。")


kb = load_kb(str(KNOWLEDGE), knowledge_signature(KNOWLEDGE))
agent = AncientBookAgent(engine, kb)

st.markdown(
    """
<div class="hero">
  <div class="hero-title">古籍智护</div>
  <div class="hero-sub">古籍保护知识辅助系统</div>
  <div class="hero-meta">馆藏古籍病害查询与修复知识参考</div>
</div>
""",
    unsafe_allow_html=True,
)

books = engine.all_books()
if not books:
    st.warning("没有识别到“古籍文献”实例。请确认上传本体中的类名/属性名。")


def _friendly_disease_source(parsed: dict) -> str:
    raw = parsed.get("disease_source", "")
    mapping = {
        "用户输入，且与本体已有断言一致": "输入内容与知识库记录一致",
        "用户输入；部分与本体已有断言一致": "输入内容部分与知识库记录一致",
        "用户输入情景": "用户临时输入",
        "本体已有断言/档案": "知识库已有记录",
        "本体已有病害": "知识库已有记录",
    }
    if raw in mapping:
        return mapping[raw]
    return "用户临时输入" if parsed.get("explicit_from_user") else "知识库已有记录"


def _process_rows(process_name: str) -> list[dict]:
    prof = engine.process_profile(process_name)
    rows = []
    labels = [
        ("前置工序", "前置工序"),
        ("后续工序", "后续工序"),
        ("使用工具", "使用工具"),
        ("使用原料", "使用原料"),
        ("产出成品", "产出成品"),
    ]
    for key, label in labels:
        vals = prof.get(key, [])
        if vals:
            rows.append({"项目": label, "内容": "、".join(vals)})
    return rows



@st.cache_data(ttl=86400, show_spinner=False)
def _ai_reference_query(diseases_key: tuple, processes_key: tuple) -> tuple[str, str]:
    """
    AI may expand search terms, but it never creates bibliographic entries.
    Returned tuple: (query, method_label)
    """
    base = professional_refs.default_search_query(diseases_key, processes_key)
    if not llm_client.configured():
        return base, "规则生成检索词"

    system = (
        "You generate search keywords for academic literature retrieval. "
        "Output exactly one short English search query of 4-12 words. "
        "Focus on paper/book/library conservation. "
        "Do not output paper titles, authors, DOI, URLs, explanations or citations."
    )
    user = (
        f"Diseases: {', '.join(diseases_key) or 'unknown'}\n"
        f"Candidate processes: {', '.join(processes_key) or 'unknown'}\n"
        f"Fallback query: {base}"
    )
    try:
        raw = llm_client.chat(system, user, timeout=25)
        query = professional_refs.sanitize_ai_query(raw, base)
        if query != base:
            return query, "语言模型扩展检索词"
    except Exception:
        pass
    return base, "规则生成检索词"


@st.cache_data(ttl=3600, show_spinner=False)
def _professional_reference_search(
    diseases_key: tuple,
    processes_key: tuple,
    academic_query: str,
) -> dict:
    authority = professional_refs.authority_references(
        diseases_key,
        processes_key,
        limit=6,
    )
    academic, error = professional_refs.search_crossref(
        academic_query,
        rows=5,
        timeout=10,
    )
    return {
        "authority": authority,
        "academic": academic,
        "error": error,
    }


def _display_reference_item(ref: dict) -> None:
    category = ref.get("category", "资料")
    title = ref.get("title", "未命名资料")
    url = ref.get("url", "")
    source = ref.get("source", "")
    year = ref.get("year", "")
    authors = ref.get("authors", "")
    journal = ref.get("journal", "")
    note = ref.get("note", "")

    if url:
        st.markdown(f"**[{category}] [{title}]({url})**")
    else:
        st.markdown(f"**[{category}] {title}**")

    meta = " · ".join(x for x in [source, journal, year] if x)
    if meta:
        st.caption(meta)
    if authors:
        st.caption(f"作者：{authors}")
    if note:
        st.write(note)




tabs = st.tabs(["查询", "关于系统"])

# =========================================================
# 查询：整个网站的核心业务入口
# =========================================================
with tabs[0]:
    st.markdown("### 古籍病害查询")
    st.caption("输入古籍名称和病害情况，查询相关知识及可供专业人员参考的候选修复工序。")

    c1, c2 = st.columns([1, 2], gap="large")
    with c1:
        selected = st.selectbox(
            "已有古籍档案（可选）",
            ["（自动识别）"] + books,
            help="如果问题中已经写明古籍名称，可以保持“自动识别”。",
        )
        st.caption("示例")
        if st.button("《天工开物》 / 水渍", use_container_width=True):
            st.session_state["q"] = "《天工开物》存在水渍，请查询相关修复工序并说明依据。"
        if st.button("《天工开物》 / 纸张发黄", use_container_width=True):
            st.session_state["q"] = "《天工开物》存在纸张发黄，请查询当前知识库中的相关修复工序。"
        if st.button("情景查询：史记 / 酸化", use_container_width=True):
            st.session_state["q"] = "假设《史记》当前存在酸化，请根据现有知识关系进行情景查询。"

    with c2:
        q = st.text_area(
            "病害情况或查询问题",
            value=st.session_state.get(
                "q",
                "《天工开物》存在水渍，请查询相关修复工序并说明依据。",
            ),
            height=132,
            placeholder="例如：《天工开物》存在水渍，请查询相关修复工序。",
        )
        if st.button("查询", type="primary", use_container_width=True):
            if not q.strip():
                st.warning("请先输入古籍名称、病害情况或查询问题。")
            else:
                default_book = None if selected == "（自动识别）" else selected
                st.session_state["last_result"] = agent.run(q, selected_book=default_book)

    result = st.session_state.get("last_result")

    if result:
        parsed = result["parsed"]
        recs = parsed["recommendations"]
        unresolved = parsed["unresolved"]
        hits = result["hits"]

        st.divider()
        st.markdown("## 查询结果")

        # ----- 基本识别结果 -----
        book_name = parsed.get("book")
        if book_name:
            book_source = (
                "知识库已有档案"
                if parsed.get("book_in_ontology", False)
                else "用户临时输入，当前知识库中无此古籍档案"
            )
            st.write(f"**古籍：** {book_name}　　**来源：** {book_source}")

        if parsed.get("diseases"):
            st.write(
                f"**病害：** {'、'.join(parsed['diseases'])}　　"
                f"**来源：** {_friendly_disease_source(parsed)}"
            )

        # ----- 核心业务结果 -----
        if recs:
            st.success("已找到可供参考的候选修复工序")
            st.markdown("### 候选修复工序")

            for idx, r in enumerate(recs, 1):
                title = r.process + ("（情景查询）" if r.scenario_input else "")
                st.markdown(f"#### {title}")

                if r.scenario_input:
                    st.write(
                        f"本次将“{r.book}存在{r.disease}”作为临时查询条件。"
                        f"知识库中已存在“{r.disease}—适用修复工序→{r.process}”关系，"
                        f"因此在该条件成立的前提下，可将“{r.process}”作为候选工序参考。"
                    )
                else:
                    st.write(
                        f"知识库已记录“{r.book}—具有病害→{r.disease}”，"
                        f"并存在“{r.disease}—适用修复工序→{r.process}”关系，"
                        f"因此得到候选修复工序“{r.process}”。"
                    )

                process_rows = _process_rows(r.process)
                if process_rows:
                    st.markdown("**相关修复知识**")
                    st.dataframe(
                        pd.DataFrame(process_rows),
                        use_container_width=True,
                        hide_index=True,
                    )

                if idx < len(recs):
                    st.divider()

        elif unresolved:
            st.warning("当前知识库尚未建立对应的修复工序关系")
            for d in unresolved:
                st.write(
                    f"已识别病害“{d}”，但当前知识库中没有与之对应的“适用修复工序”关系。"
                    "系统不会根据语言模型自行补充修复工序。"
                )
        else:
            st.info("当前查询未找到可用的病害—修复工序关系。")

        # ----- 综合说明：有则提供，但不与主结果争夺视觉层级 -----
        if llm_client.configured() and result.get("answer"):
            with st.expander("补充说明", expanded=False):
                st.markdown(result["answer"])

        # ----- 把原来的知识检索、推理记录全部收进结果详情 -----
        with st.expander("查看古籍信息与知识关系", expanded=False):
            if book_name and parsed.get("book_in_ontology", False):
                profile = engine.book_profile(book_name)
                profile_rows = []
                for k, v in profile.items():
                    if k != "古籍" and v not in (None, "", [], "—"):
                        if isinstance(v, list):
                            v = "、".join(v)
                        profile_rows.append({"项目": k, "内容": v})

                if profile_rows:
                    st.markdown("**古籍档案**")
                    st.dataframe(
                        pd.DataFrame(profile_rows),
                        use_container_width=True,
                        hide_index=True,
                    )

                diseases = engine.object_values(book_name, "具有病害")
                if diseases:
                    st.markdown("**知识关系**")
                    for d in diseases:
                        ps = engine.disease_processes(d)
                        if ps:
                            st.write(
                                f"- {book_name} → 具有病害 → {d} → 适用修复工序 → {'、'.join(ps)}"
                            )
                        else:
                            st.write(
                                f"- {book_name} → 具有病害 → {d}（当前暂无工序映射）"
                            )
                else:
                    damage_text = profile.get("破损状况", "")
                    st.info("当前知识库尚未为该古籍建立结构化病害关系。")
                    if damage_text:
                        st.caption(
                            f"档案中的“破损状况”文字著录为：{damage_text}。"
                            "该文字字段目前尚未转换为可参与规则推理的病害关系。"
                        )
            elif book_name:
                st.info(
                    f"“{book_name}”为本次查询临时输入，当前知识库中没有对应的古籍档案。"
                )

        with st.expander("查看知识关系", expanded=False):
            if recs:
                for r in recs:
                    if r.scenario_input:
                        st.write(
                            f"临时条件：{r.book} 存在 {r.disease}"
                        )
                        st.write(
                            f"知识库关系：{r.disease} → 适用修复工序 → {r.process}"
                        )
                        st.write(
                            f"情景推演结果：{r.book} → 候选修复工序 → {r.process}"
                        )
                    else:
                        st.write(
                            f"{r.book} → 具有病害 → {r.disease} "
                            f"→ 适用修复工序 → {r.process}"
                        )

            elif unresolved:
                st.write(
                    "已识别病害，但由于当前知识库没有对应的病害—工序映射，"
                    "本次查询在此停止，不生成额外修复工序。"
                )
            else:
                st.write("本次查询未形成可继续推理的病害—工序关系。")

            if (
                book_name
                and parsed.get("book_in_ontology", False)
                and engine.object_values(book_name, "具有病害")
            ):
                st.markdown("**知识关系图**")
                st.graphviz_chart(
                    engine.graphviz_for_book(book_name),
                    use_container_width=True,
                )
                st.caption(
                    "实线表示知识库中的显式关系；虚线表示按属性链规则得到的候选关系。"
                )

        # ----- 专业资料检索：真实来源先检索，AI只扩展检索词 -----
        diseases_for_refs = tuple(parsed.get("diseases", []))
        processes_for_refs = tuple(dict.fromkeys(r.process for r in recs))
        academic_query, query_method = _ai_reference_query(
            diseases_for_refs,
            processes_for_refs,
        )
        ref_result = _professional_reference_search(
            diseases_for_refs,
            processes_for_refs,
            academic_query,
        )

        st.markdown("### 专业参考资料")
        st.caption(
            "优先匹配国家标准和专业机构资料，并通过 Crossref 检索真实学术元数据。"
            "语言模型仅用于扩展检索词，不生成论文标题、作者或 DOI。"
        )

        authority_refs = ref_result["authority"]
        academic_refs = ref_result["academic"]

        if authority_refs:
            st.markdown("#### 标准与专业机构资料")
            for i, ref in enumerate(authority_refs):
                _display_reference_item(ref)
                if i < len(authority_refs) - 1:
                    st.markdown("---")

        if academic_refs:
            st.markdown("#### 相关学术研究")
            for i, ref in enumerate(academic_refs):
                _display_reference_item(ref)
                if i < len(academic_refs) - 1:
                    st.markdown("---")
        elif ref_result["error"]:
            st.caption(
                "学术元数据检索暂时无法连接；上方国家标准与专业机构资料仍可正常使用。"
            )

        with st.expander("检索说明", expanded=False):
            st.write(f"**学术检索词：** {academic_query}")
            st.write(f"**检索词生成：** {query_method}")
            st.write(
                "学术论文条目来自 Crossref 元数据接口；标准和机构资料来自系统内置的已核验来源目录。"
                "检索结果用于寻找原始依据，具体内容应以链接中的原文为准。"
            )

        if hits:
            with st.expander("本地知识库说明", expanded=False):
                st.caption("以下为项目本地说明材料，不作为外部专业文献引用。")
                for h in hits:
                    st.markdown(f"**{h.source}**")
                    st.write(h.text[:700].strip())
                    st.divider()

        with st.expander("查看系统处理记录", expanded=False):
            step_names = {
                "entity_understanding": "识别古籍与病害",
                "ontology_query_and_rule": "查询知识关系与规则",
                "local_rag": "检索本地说明资料",
                "llm_generation": "整理补充说明",
            }
            for i, step in enumerate(result["trace"], 1):
                title = step_names.get(step.get("tool"), step.get("tool", "处理步骤"))
                st.markdown(f"**{i}. {title}**")
                output = step.get("output")
                if output is not None:
                    if isinstance(output, (dict, list)):
                        st.json(output)
                    else:
                        st.write(output)

        st.info(
            "候选修复工序仅用于知识查询和业务参考。完整修复方案应由专业人员结合古籍实物状态、"
            "材料稳定性及病害成因等情况作出。"
        )

# =========================================================
# 关于系统：技术信息和知识覆盖统一放到这里
# =========================================================
with tabs[1]:
    st.markdown("### 关于古籍智护")
    st.write(
        "古籍智护面向高校图书馆馆藏古籍保护工作，"
        "用于查询古籍病害相关知识，并在现有知识关系支持的情况下给出候选修复工序参考。"
        "系统不自动制定完整修复方案。"
    )

    st.markdown("#### 使用方式")
    st.write(
        "输入古籍名称和病害情况即可查询。系统先核对现有古籍与病害知识，"
        "再根据已经建立的病害—工序关系给出结果；如果知识库中没有对应规则，"
        "系统会直接说明当前知识缺口。"
    )

    st.markdown("#### 技术说明")
    st.write(
        "系统读取 Protégé 导出的 RDF 本体，以“古籍—病害—修复工序—材料—工具”等关系组织知识。"
                "候选工序由已有关系和属性链规则产生；知识关系图用于直观展示古籍、病害与修复工序之间的本体关联。"
        "专业参考资料优先匹配国家标准和专业机构来源，"
        "并通过 Crossref 检索真实学术元数据。语言模型用于理解问题、扩展检索词和整理说明，"
        "不负责自行生成修复规则或虚构参考文献。"
    )

    with st.expander("当前知识库规模", expanded=False):
        stats = engine.ontology_stats()
        stats_df = pd.DataFrame(
            [{"项目": k, "数量": v} for k, v in stats.items()]
        )
        st.dataframe(stats_df, use_container_width=True, hide_index=True)

    with st.expander("当前知识覆盖情况", expanded=False):
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
                status = "已有结构化病害，可进行部分规则查询"
            elif structured:
                status = "已有结构化病害，暂无对应工序"
            elif damage_text != "—":
                status = "仅有破损文字著录，尚未结构化"
            else:
                status = "暂无病害数据"

            coverage_rows.append(
                {
                    "古籍": book,
                    "破损状况（文字）": damage_text,
                    "结构化病害": "、".join(structured) if structured else "—",
                    "已建立病害→工序关系": "；".join(process_pairs) if process_pairs else "—",
                    "状态": status,
                }
            )

        st.dataframe(
            pd.DataFrame(coverage_rows),
            use_container_width=True,
            hide_index=True,
        )
        st.caption(
            "“破损状况”文字著录与结构化病害关系是两种不同的数据形式；"
            "只有已经建立对象关系的病害才能参与当前规则查询。"
        )

    st.markdown("#### 当前边界")
    st.write(
        "当前知识库仍属于原型阶段，病害—工序规则覆盖有限。"
        "所有候选修复工序均需由古籍修复专业人员结合纸张强度、颜料稳定性、"
        "病害原因和实物状态进行复核。"
    )
