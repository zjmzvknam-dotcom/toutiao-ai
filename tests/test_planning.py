from app.models.domain import Evidence
from app.services.planning import build_plan
from app.services.topics import analyze_topic


def test_plan_has_auditable_structure_and_source_constraints() -> None:
    plan = build_plan(analyze_topic("新能源汽车"), persona="行业观察型", evidence=[Evidence(claim="来源线索", source_name="测试")])
    assert len(plan.outline) == 5
    assert plan.persona == "行业观察型"
    assert any("核验" in rule for rule in plan.source_constraints)
