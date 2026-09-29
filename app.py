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

st.set_page_config(page_title="古籍智护 Agent", page_icon="📚", layout="wide")
st.markdown("""
<style>
.block-container {padding-top: 1.2rem; padding-bottom: 3rem;}
.big-title {font-size: 2.1rem; font-weight: 750; margin-bottom:.2rem;}
.subtle {color:#666; margin-bottom:1rem;}
.badge {display:inline-block;padding:.15rem .55rem;border:1px solid #bbb;border-radius:99px;margin-right:.35rem;font-size:.82rem;}
</style>
""", unsafe_allow_html=True)

@st.cache_resource(show_spinner=False)
def load_builtin():
    path = ONTOLOGY if ONTOLOGY.exists() else DEMO
    return OntologyEngine.from_path(path)

@st.cache_resource(show_spinner=False)
def load_kb():
    return LocalKnowledgeBase(KNOWLEDGE)

with st.sidebar:
    st.header("知识底座")
    uploaded = st.file_uploader("可选：上传新的 Protégé 本体（.rdf/.owl/.ttl）", type=["rdf", "owl", "ttl"])
    if uploaded:
        try:
            engine = OntologyEngine.from_bytes(uploaded.getvalue(), uploaded.name)
            st.success(f"已载入：{uploaded.name}")
        except Exception as e:
            st.error(f"本体解析失败：{e}")
            engine = load_builtin()
    else:
        engine = load_builtin()
        if ONTOLOGY.exists():
            st.success("已加载：天工开物古籍修复本体.rdf")
        else:
            st.caption("当前使用项目内置 Demo 本体。")

    st.caption("属性链状态：" + ("✅ 已识别" if engine.has_property_chain() else "⚠️ 未识别"))
    st.divider()
    st.header("Agent 模式")
    if llm_client.configured():
        st.success("LLM 已连接")
    else:
        st.info("当前为可审计规则模式；配置 LLM_* 环境变量后自动启用大模型生成。")
    st.caption("无论是否连接 LLM，本体查询与规则推理都在本地执行。")

kb = load_kb()
agent = AncientBookAgent(engine, kb)

st.markdown('<div class="big-title">📚 古籍智护 Agent</div>', unsafe_allow_html=True)
st.markdown('<div class="subtle">面向高校图书馆的古籍病害知识组织与可解释修复辅助决策原型</div>', unsafe_allow_html=True)
st.markdown('<span class="badge">真实 Protégé 本体</span><span class="badge">馆员主导</span><span class="badge">AI 辅助</span><span class="badge">推理可解释</span><span class="badge">知识可审计</span>', unsafe_allow_html=True)

stats = engine.ontology_stats()
metric_cols = st.columns(6)
for i, (k, v) in enumerate(stats.items()):
    metric_cols[i].metric(k, v)

books = engine.all_books()
if not books:
    st.warning("没有识别到“古籍文献”实例。请确认上传本体中的类名/属性名。")

tabs = st.tabs(["🤖 智能修复助手", "📖 古籍档案", "🧪 工序知识", "🕸️ 推理图谱", "🧰 Agent 轨迹", "ℹ️ 系统说明"])

with tabs[0]:
    c1, c2 = st.columns([1, 2])
    with c1:
        selected = st.selectbox("可选：指定古籍档案", ["（自动识别）"] + books)
        st.caption("演示问题")
        if st.button("《天工开物》有水渍，模型能推荐什么？", use_container_width=True):
            st.session_state["q"] = "《天工开物》有水渍，模型能推荐什么修复工序？请解释推理路径。"
        if st.button("《天工开物》纸张发黄怎么办？", use_container_width=True):
            st.session_state["q"] = "《天工开物》纸张发黄，当前知识库能推荐什么？"
        if st.button("情景推演：史记 + 酸化", use_container_width=True):
            st.session_state["q"] = "假设史记当前存在酸化，模型能推演出什么候选修复工序？"
    with c2:
        q = st.text_area("向智能体描述古籍与病害", value=st.session_state.get("q", "《天工开物》存在水渍，请给出本体推理结果并解释依据。"), height=120)
        if st.button("开始分析", type="primary", use_container_width=True):
            default_book = None if selected == "（自动识别）" else selected
            st.session_state["last_result"] = agent.run(q, selected_book=default_book)

    result = st.session_state.get("last_result")
    if result:
        st.markdown("### 分析结果")
        st.markdown(result["answer"])
        recs = result["parsed"]["recommendations"]
        if recs:
            rows = [{
                "古籍": r.book,
                "病害": r.disease,
                "候选工序": r.process,
                "依据性质": "用户输入情景" if r.scenario_input else "本体已有断言+属性链推理",
            } for r in recs]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

with tabs[1]:
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
                st.write(f"- **{b}** —具有病害→ **{d}**" + (f" —适用修复工序→ **{'、'.join(ps)}**" if ps else "（暂无工序映射）"))
        else:
            st.info("该古籍在当前 RDF 中暂无“具有病害”对象属性断言。")

with tabs[2]:
    processes = engine.all_processes()
    if processes:
        p = st.selectbox("选择工序", processes, key="process_book")
        prof = engine.process_profile(p)
        st.markdown(f"### {p}")
        for k in ["前置工序", "后续工序", "使用工具", "使用原料", "产出成品"]:
            vals = prof[k]
            st.write(f"**{k}：** " + ("、".join(vals) if vals else "—"))
        if p == "水洗":
            st.caption("当前 RDF 中可见：水洗使用排笔，前置工序为拆页；水渍映射到水洗。")

with tabs[3]:
    if books:
        b = st.selectbox("选择要查看推理路径的古籍", books, key="graph_book")
        st.graphviz_chart(engine.graphviz_for_book(b), use_container_width=True)
        st.caption("实线为 RDF 中显式断言；虚线为应用按本体属性链规则计算得到的“建议修复工序”。")

with tabs[4]:
    result = st.session_state.get("last_result")
    if not result:
        st.info("先在“智能修复助手”运行一次分析，这里会显示 Agent 的工具调用轨迹。")
    else:
        for i, step in enumerate(result["trace"], 1):
            with st.expander(f"{i}. {step['tool']}", expanded=True):
                st.json(step)

with tabs[5]:
    st.markdown("""
### 系统定位
本原型不是自动修复系统，而是面向高校图书馆馆员/古籍保护人员的**知识组织与辅助决策工具**。

### 技术路线
1. **真实领域本体**：直接读取 Protégé 导出的 RDF，保存古籍、病害、工序、材料、工具及语义关系；
2. **规则推理**：执行 RDF 中已存在的“具有病害 o 适用修复工序 ⊑ 建议修复工序”属性链逻辑；
3. **本地知识检索**：从 `knowledge/` 检索可审计说明材料；正式参赛版应继续加入权威修复规范与馆内制度；
4. **可选 LLM**：只负责自然语言理解和组织回答，本体事实与规则作为约束；
5. **可解释展示**：公开实体、规则、推理路径和 Agent 工具轨迹。

### 当前 RDF 的真实边界
- 《天工开物》显式关联“水渍”“纸张发黄”；
- “水渍→适用修复工序→水洗”已存在，因此可形成《天工开物》的属性链推理；
- “酸化→适用修复工序→脱酸”已存在；
- 当前 RDF **没有**“史记→具有病害→酸化”的显式断言。因此“史记+酸化”只作为用户临时输入的**情景推演**，不冒充馆藏事实；
- “纸张发黄”目前没有工序映射，系统不会自行补造。

### 专业边界
所有修复建议均应由修复专业人员结合纸张强度、颜料稳定性、病害原因和馆藏实物状态复核。系统遵循“馆员主导、AI辅助”。
    """)
