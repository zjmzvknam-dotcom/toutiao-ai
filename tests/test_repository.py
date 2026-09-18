from app.models.domain import Article, QualityReport, TaskEvent
from app.repositories.sqlite import SQLiteRepository
from app.services.topics import analyze_topic


def test_sqlite_repository_round_trip(tmp_path) -> None:
    repo = SQLiteRepository(tmp_path / "test.sqlite3")
    topic = analyze_topic("测试选题")
    repo.save_topic(topic)
    article = Article(topic=topic.title, title="测试标题", body="测试正文", quality=QualityReport(information_density=1, readability=1, duplication_risk="低", fact_risk="低", sensitivity_risk="低", template_risk="低"))
    repo.save_article(article)
    assert repo.list_topics()[0].title == "测试选题"
    assert repo.list_articles()[0].title == "测试标题"
    repo.record_task_event(TaskEvent(task_id=article.task_id, step="写作", status="完成"))
    assert repo.list_task_events(article.task_id)[0].step == "写作"
    repo.record_usage("test", "model", "writing", tokens=12, estimated_cost=0.001, task_id=article.task_id)
    assert repo.usage_totals("today")["tokens"] == 12
    assert repo.task_usage_totals(article.task_id)["requests"] == 1
