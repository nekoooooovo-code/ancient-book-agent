# 古籍智护 Agent · 比赛 MVP

这是面向高校图书馆“AI+管理服务”大赛的可运行 Web 原型：

**真实 Protégé 本体 + 可解释规则推理 + 本地知识检索 + 可选 LLM + Streamlit 前端**。

## 已接入你的真实 RDF
项目默认读取：

`data/天工开物古籍修复本体.rdf`

程序已核验：233 个三元组、12 个类、57 个命名个体、9 个对象属性、4 个数据属性，并识别到本体中的属性链：

`具有病害 o 适用修复工序 ⊑ 建议修复工序`

## 本地启动（Windows）

直接双击：`start_windows.bat`

或：

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## 推荐现场演示

1. 《天工开物》有水渍，模型能推荐什么？
   - 返回“水洗”并显示属性链推理依据。
2. 《天工开物》纸张发黄怎么办？
   - 返回“当前知识库暂无规则”，展示不乱编。
3. 情景推演：史记 + 酸化
   - 返回“脱酸（情景推演）”，同时明确：真实 RDF 中没有“史记→酸化”断言。
4. 打开“工序知识”查看“水洗”：显示其工具“排笔”和前置工序“拆页”。
5. 打开“Agent 轨迹”，展示实体理解、本体查询与规则、RAG、可选 LLM 的调用链。

## 接入大模型（可选）

配置：

```text
LLM_BASE_URL=兼容接口根地址
LLM_API_KEY=Key
LLM_MODEL=模型名
```

没有 LLM 时也能运行完整的可审计规则版。

## 公网部署
见 `submission/公网部署步骤.md`。
