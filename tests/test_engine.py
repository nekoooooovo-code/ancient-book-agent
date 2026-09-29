from pathlib import Path
from src.ontology_engine import OntologyEngine

ROOT = Path(__file__).resolve().parents[1]
ENGINE = OntologyEngine.from_path(ROOT / "data" / "天工开物古籍修复本体.rdf")


def test_real_ontology_stats():
    s = ENGINE.ontology_stats()
    assert s["三元组"] == 233
    assert s["类"] == 12
    assert s["命名个体"] == 57
    assert s["对象属性"] == 9
    assert s["数据属性"] == 4


def test_property_chain_present():
    assert ENGINE.has_property_chain()


def test_diseases_inferred_from_property_range_usage():
    ds = ENGINE.all_diseases()
    assert "水渍" in ds
    assert "纸张发黄" in ds
    assert "酸化" in ds


def test_tiangong_water_stain_inference():
    r = ENGINE.infer_from_text("《天工开物》有水渍")
    assert [x.process for x in r["recommendations"]] == ["水洗"]
    assert not r["recommendations"][0].scenario_input


def test_yellowing_is_unresolved_only():
    r = ENGINE.infer_from_text("《天工开物》纸张发黄怎么办")
    assert not r["recommendations"]
    assert r["unresolved"] == ["纸张发黄"]


def test_shiji_acidification_is_scenario_not_asserted_fact():
    assert "酸化" not in ENGINE.object_values("史记", "具有病害")
    r = ENGINE.infer_from_text("假设史记存在酸化")
    assert [x.process for x in r["recommendations"]] == ["脱酸"]
    assert r["recommendations"][0].scenario_input


def test_water_process_profile():
    p = ENGINE.process_profile("水洗")
    assert "排笔" in p["使用工具"]
    assert "拆页" in p["前置工序"]
