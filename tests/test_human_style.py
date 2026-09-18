import json

from app.services.human_style import inspect_style, improve_locally
from app.services.personas import PROFILES, resolve_persona, writer_prompt
from app.services.planning import build_plan
from app.models.domain import Topic


def test_ten_distinct_profiles_reach_writer():
    topic = Topic(title="中年人的心酸")
    prompts = []
    for name, profile in PROFILES.items():
        plan = build_plan(topic, persona=name, evidence=[])
        prompt = writer_prompt(topic, plan, 650, "", [])
        assert profile.instruction() in prompt
        assert "禁止编造老周" in prompt
        assert profile.opening in plan.outline
        prompts.append(prompt)
    assert len(set(prompts)) == 10
    assert resolve_persona("普通人视角").name == "普通上班族"


def test_single_natural_connector_not_banned():
    assert not inspect_style("最后一班车到站了。\n\n人慢慢散了。")['issues']


def test_only_one_call_two_paragraphs_and_preserve_numeric_facts():
    body = "首先，预算是200元，够不够得看买什么。\n\n其次，菜要新鲜，也不必买太多。\n\n最后，提回家太沉就不方便了。"
    class Router:
        calls = 0
        def generate(self, workflow, prompt):
            self.calls += 1
            assert "提回家" not in prompt
            return json.dumps([{"paragraph": 0, "text": "预算改成300元就好，够不够得看买什么。"}, {"paragraph": 1, "text": "菜买新鲜的，吃得完就行，别塞满冰箱。"}], ensure_ascii=False)
    router = Router()
    result, report = improve_locally(body, "普通城市居民", router)
    assert router.calls == 1
    assert "200元" in result and "300元" not in result
    assert report["accepted"] == [1]


def test_style_timeout_keeps_original():
    class Broken:
        def generate(self, *args):
            raise TimeoutError("secret")
    body = "首先，看看预算。\n\n其次，检查需求。\n\n最后，做个选择。"
    result, report = improve_locally(body, "年轻消费者", Broken())
    assert result == body
    assert "secret" not in str(report)
