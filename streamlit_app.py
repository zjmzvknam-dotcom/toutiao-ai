from __future__ import annotations

from html import escape
import json
from pathlib import Path
from uuid import uuid4

import streamlit as st

from app.config.settings import settings
from app.models.domain import Article, TaskEvent, Topic
from app.providers import CachedSearchProvider, GDELTDocumentProvider, ModelRouter, MultiModelRouter, MultiSourceTrendProvider, OpenAICompatibleProvider, PexelsImageProvider, ResilientSearchProvider, RoutedModel
from app.providers.images import WikimediaCommonsImageProvider
from app.repositories.sqlite import SQLiteRepository
from app.services.export import markdown, plain_text, word_document
from app.services.editor import revise
from app.services.readiness import assess_readiness
from app.services.topics import analyze_topic
from app.services.tracking import refresh_topic
from app.ui.copy import render_copy_button
from app.workflows import ArticleWorkflow

st.set_page_config(page_title="内容创作工作台", page_icon="✍️", layout="wide", initial_sidebar_state="collapsed")


@st.cache_resource
def repository() -> SQLiteRepository:
    return SQLiteRepository(settings.database_path)


@st.cache_resource
def search_provider() -> ResilientSearchProvider:
    return ResilientSearchProvider(CachedSearchProvider(GDELTDocumentProvider()))


@st.cache_data(ttl=900, show_spinner=False)
def live_trends_snapshot() -> tuple[list[dict], list[str], str]:
    """Refresh public trend signals at most every 15 minutes per app worker."""
    topics, warnings, refreshed_at = MultiSourceTrendProvider().fetch(limit=30)
    if not topics:
        snapshot = Path("data/hot_topics.json")
        try:
            cached = json.loads(snapshot.read_text(encoding="utf-8"))
            topics = [Topic.model_validate(row) for row in cached.get("topics", [])]
            topics = [topic.model_copy(update={"source": f"{topic.source}（每日缓存）"}) for topic in topics]
            warnings.append("实时源暂时不可用，当前展示 GitHub Actions 最近一次每日快照。")
            refreshed_at = cached.get("refreshed_at") or refreshed_at.isoformat()
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass
    refreshed_label = refreshed_at if isinstance(refreshed_at, str) else refreshed_at.isoformat()
    return [topic.model_dump(mode="json") for topic in topics], warnings, refreshed_label


def router_from_session() -> ModelRouter | MultiModelRouter:
    profiles = st.session_state.get("model_profiles", {})
    routes = st.session_state.get("model_routes", {})
    enabled_profiles = {profile_id: config for profile_id, config in profiles.items() if config.get("enabled") and config.get("api_key") and config.get("model")}
    if enabled_profiles:
        providers = {profile_id: OpenAICompatibleProvider(config["api_key"], config["base_url"]) for profile_id, config in enabled_profiles.items()}
        resolved_routes = {workflow: RoutedModel(profile_id, enabled_profiles[profile_id]["model"]) for workflow, profile_id in routes.items() if profile_id in enabled_profiles}
        if not resolved_routes:
            first_profile = next(iter(enabled_profiles))
            resolved_routes = {workflow: RoutedModel(first_profile, enabled_profiles[first_profile]["model"]) for workflow in ("analysis", "writing", "quality")}
        return MultiModelRouter(providers, resolved_routes)
    config = st.session_state.get("model_config", {})
    if not config.get("enabled") or not config.get("api_key") or not config.get("model"):
        return ModelRouter(None)
    provider = OpenAICompatibleProvider(config["api_key"], config["base_url"])
    return ModelRouter(provider, {"analysis": config["model"], "writing": config["model"], "quality": config["model"]})


def show_article(article: Article, *, context: str) -> None:
    st.subheader(article.title)
    st.caption(f"任务 ID：{article.task_id} · 状态：{article.status} · 模型：{article.model}")
    readiness = article.metadata.get("readiness")
    if readiness:
        if readiness["status"] == "READY":
            st.success("发布状态：READY（仍建议在最终发布页再次核对链接与排版）")
        else:
            st.warning("发布状态：需要人工复核")
            for blocker in readiness["blockers"]:
                st.write(f"- {blocker}")
    if article.metadata.get("warning"):
        st.warning(article.metadata["warning"])
    left, right = st.columns([1.1, 0.9])
    with left:
        if article.image.verified and article.image.url:
            st.image(article.image.url, caption=f"已确认图片 · {article.image.source}")
        elif candidates := st.session_state.get(f"image-candidates-{article.id}", []):
            st.image(candidates[0].url, caption=f"待人工确认图片候选 · {candidates[0].source}")
            st.info("这是来源候选，不会自动作为配图发布；请展开右侧“图片候选与人工审核”确认后使用。")
        st.markdown(article.body)
        copy_columns = st.columns(3)
        with copy_columns[0]:
            render_copy_button(f"{article.title}\n\n{article.body}", "复制全文")
        with copy_columns[1]:
            render_copy_button(article.title, "复制标题")
        with copy_columns[2]:
            render_copy_button(article.body, "复制正文")
        st.download_button("下载 TXT", plain_text(article), f"{article.id}.txt", "text/plain", key=f"{context}-{article.id}-txt")
        st.download_button("下载 Markdown", markdown(article), f"{article.id}.md", "text/markdown", key=f"{context}-{article.id}-md")
        st.download_button("下载 Word", word_document(article), f"{article.id}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", key=f"{context}-{article.id}-docx")
    with right:
        st.markdown("#### 手机阅读预览")
        preview_title = escape(article.title)
        preview_body = escape(article.body[:500]).replace("\n", "<br><br>")
        suffix = "…" if len(article.body) > 500 else ""
        st.markdown(f'<div style="max-width:370px;margin:auto;padding:22px;border:8px solid #252525;border-radius:28px;background:#fff;box-shadow:0 8px 25px #ddd"><h3>{preview_title}</h3><p style="line-height:1.9">{preview_body}{suffix}</p></div>', unsafe_allow_html=True)
        st.markdown("#### 5 个标题")
        for option in article.titles:
            prefix = "⭐ " if option.recommended else ""
            st.write(f"{prefix}{option.title}（{option.strategy}，准确性 {option.accuracy}）")
        st.markdown("#### 质量与风险")
        report = article.quality
        st.write(f"信息密度 {report.information_density} · 可读性 {report.readability} · 事实风险：{report.fact_risk} · 敏感风险：{report.sensitivity_risk}")
        for note in report.notes:
            st.info(note)
        st.caption(f"图片：{article.image.label}。{article.image.reason}")
        with st.expander("资料与事实核验状态"):
            st.caption(f"资料 Provider：{article.metadata.get('research_provider', '未配置')}。所有资料仅为待核验线索，不应自动视为事实。")
            for index, evidence in enumerate(article.evidence):
                st.write(f"- {evidence.claim}（{evidence.source_name}，{evidence.confidence}）")
                if evidence.source_url:
                    st.link_button("查看原始来源", evidence.source_url, key=f"{context}-{article.id}-evidence-{index}")
                if evidence.confidence != "已核验":
                    confirmed_source = st.checkbox("我已核对该来源的原文、时间、主体与正文表述", key=f"{context}-{article.id}-source-confirm-{index}")
                    if st.button("标记此来源为已核验", key=f"{context}-{article.id}-source-verify-{index}", disabled=not confirmed_source):
                        evidence_list = list(article.evidence)
                        evidence_list[index] = evidence.model_copy(update={"confidence": "已核验"})
                        refreshed = assess_readiness(evidence=evidence_list, image=article.image, image_requested=article.metadata.get("image_requested", False), quality=article.quality)
                        revised = article.model_copy(update={"evidence": evidence_list, "metadata": {**article.metadata, "readiness": refreshed.model_dump()}})
                        repository().save_article(revised)
                        if context == "current":
                            st.session_state["current_article"] = revised
                        st.success("来源已标记为人工核验。")
                        st.rerun()
        with st.expander("任务进度记录"):
            events = repository().list_task_events(article.task_id)
            if events:
                for event in events:
                    st.write(f"{event.created_at:%H:%M:%S} · {event.step}：{event.status}")
            else:
                st.caption("此文章没有可用的历史任务事件。")
        with st.expander("文章策划"):
            plan = article.metadata.get("plan")
            if plan:
                st.write(f"目标读者：{plan['audience']}")
                st.write(f"核心问题：{plan['core_question']}")
                st.write(f"核心观点：{plan['thesis']}")
                st.write("结构：" + " → ".join(plan["outline"]))
            else:
                st.caption("此文章创建于结构化策划上线前。")
        with st.expander("图片候选与人工审核"):
            pexels_key = st.session_state.get("pexels_api_key", "")
            if not pexels_key:
                st.caption("未配置 Pexels Key 时，系统使用无需 Key 的 Wikimedia Commons 公开来源候选；候选不会自动插入，必须人工确认后才会显示在文章中。")
            if st.button("搜索真实来源图片候选", key=f"{context}-{article.id}-image-search"):
                try:
                    provider = PexelsImageProvider(pexels_key) if pexels_key else WikimediaCommonsImageProvider()
                    candidates = provider.find(article.topic)
                    st.session_state[f"image-candidates-{article.id}"] = candidates
                except Exception:
                    st.warning("图片服务暂时不可用；文章仍可正常使用。")
            for index, candidate in enumerate(st.session_state.get(f"image-candidates-{article.id}", [])):
                st.image(candidate.url, caption=candidate.source)
                st.warning(candidate.reason)
                confirmed = st.checkbox("我已人工确认：图片与文章中的人物、产品、时间、事件相符，并已核对来源与许可", key=f"{context}-{article.id}-image-confirm-{index}")
                if st.button("将此图标记为已确认配图", key=f"{context}-{article.id}-image-approve-{index}", disabled=not confirmed):
                    approved = candidate.model_copy(update={"verified": True, "label": "真实来源图片（人工确认）", "reason": "已由用户人工确认来源、语义匹配与使用许可；仍建议保留来源页用于发布前复核。"})
                    revised = article.model_copy(update={"image": approved})
                    readiness = revised.metadata.get("readiness")
                    if readiness:
                        refreshed = assess_readiness(evidence=revised.evidence, image=approved, image_requested=True, quality=revised.quality)
                        revised = revised.model_copy(update={"metadata": {**revised.metadata, "readiness": refreshed.model_dump()}})
                    repository().save_article(revised)
                    if context == "current":
                        st.session_state["current_article"] = revised
                    st.success("图片已标记为人工确认配图。")
                    st.rerun()
        with st.expander("文章修改助手"):
            instruction = st.selectbox("事实保留型修改", ["更口语", "增加观点", "扩写", "缩写"], key=f"{context}-{article.id}-revision")
            if st.button("应用修改", key=f"{context}-{article.id}-revise"):
                revised = revise(article, instruction)
                repository().save_article(revised)
                if context == "current":
                    st.session_state["current_article"] = revised
                st.success("已应用本地修改；外部事实没有被新增或改写。")
                st.rerun()


def main() -> None:
    repo = repository()
    st.title("今日头条 AI 内容创作工作台")
    st.caption("以真实性、质量与可维护性为先。AI 评分为辅助估计，不保证流量、审核或“真人原创”。")
    create_tab, radar_tab, library_tab, settings_tab, cost_tab = st.tabs(["🚀 自动创作", "📡 热点雷达", "📚 我的文章", "⚙️ 模型设置", "💰 成本"])

    with create_tab:
        # Keep the latest result above the input form so a rerun never hides
        # the generated article below the fold.
        if current := st.session_state.get("current_article"):
            st.success(f"文章已生成：{current.title}。可直接复制、下载或展开右侧的手机预览与核验项。")
            show_article(current, context="current-top")
            st.divider()
        with st.form("create_article"):
            keyword = st.text_input("关键词或选题", placeholder="例如：小米汽车")
            col1, col2, col3 = st.columns(3)
            length = col1.select_slider("目标字数", options=[600, 900, 1200, 1600, 2200], value=900)
            persona = col2.selectbox("作者人格", ["理性分析型", "温和观察型", "普通人视角", "行业观察型", "知识科普型"])
            images = col3.checkbox("自动找配图候选（需人工确认）", value=True)
            requirement = st.text_area("写作要求（可选）", placeholder="例如：关注普通消费者的影响，避免未经核实的结论。")
            with st.expander("专业模式"):
                search_enabled = st.checkbox("使用 GDELT 新闻资料搜索（资料均需人工核验）", value=False)
                time_range = st.selectbox("资料时间范围", ["1h", "6h", "24h", "3d", "7d"], index=2)
                generate_variants = st.checkbox("一个选题生成 5 篇不同角度文章", value=False)
                high_risk_confirmed = st.checkbox("我确认：高风险题材仅作谨慎信息整理，发布前将人工核验事实、来源、合规与专业建议边界", value=False)
            submitted = st.form_submit_button("开始创作", type="primary")
        if submitted:
            if not keyword.strip():
                st.error("请输入关键词或选题。")
            else:
                topic = analyze_topic(keyword)
                repo.save_topic(topic)
                st.caption(f"初步选题：爆款潜力指数 {topic.potential}/100（AI 离线估计，非实时数据）；风险：{topic.risk}。")
                progress = st.status("正在准备工作流…", expanded=True)
                task_id = str(uuid4())
                task_events: list[TaskEvent] = []
                def emit(step: str, state: str) -> None:
                    progress.write(f"{step}：{state}")
                    task_events.append(TaskEvent(task_id=task_id, step=step, status=state))
                try:
                    selected_search_provider = search_provider() if search_enabled else None
                    # Compare against the same normalized topic only. A shared
                    # offline safety template must not make every new topic
                    # look like a duplicate of an older article.
                    existing_bodies = [
                        item.body
                        for item in repo.list_articles()
                        if item.topic.strip().casefold() == topic.title.strip().casefold()
                    ]
                    active_router = router_from_session()
                    workflow = ArticleWorkflow(active_router, selected_search_provider)
                    if generate_variants:
                        articles = workflow.run_many(topic, length=length, persona=persona, requirement=requirement, use_research=search_enabled, timespan=time_range, confirmed_high_risk=high_risk_confirmed, progress=emit)
                        for article in articles:
                            repo.save_article(article)
                            repo.record_task_event(TaskEvent(task_id=article.task_id, step="多角度创作", status=f"完成：{article.metadata['variant_angle']}"))
                        st.session_state["current_variants"] = articles
                        article = articles[0]
                    else:
                        article = workflow.run(topic, length=length, persona=persona, requirement=requirement, with_images=images, use_research=search_enabled, timespan=time_range, existing_bodies=existing_bodies, task_id=task_id, confirmed_high_risk=high_risk_confirmed, progress=emit)
                        if images:
                            try:
                                pexels_key = st.session_state.get("pexels_api_key", "")
                                provider = PexelsImageProvider(pexels_key) if pexels_key else WikimediaCommonsImageProvider()
                                st.session_state[f"image-candidates-{article.id}"] = provider.find(article.topic, limit=3)
                            except Exception:
                                st.session_state[f"image-candidates-{article.id}"] = []
                        repo.save_article(article)
                        for event in task_events:
                            repo.record_task_event(event)
                    if active_router.model_for("writing"):
                        provider_name = active_router.provider_for("writing") if isinstance(active_router, MultiModelRouter) else "default"
                        usage = active_router.usage_for("writing")
                        repo.record_usage(provider_name, active_router.model_for("writing"), "writing", tokens=usage.get("total_tokens", 0), task_id=article.task_id)
                    progress.update(label="创作完成", state="complete")
                    st.session_state["current_article"] = article
                except ValueError as exc:
                    repo.record_task_event(TaskEvent(task_id=task_id, step="工作流", status=f"拒绝：{exc}"))
                    progress.update(label="需要调整选题", state="error")
                    st.warning(str(exc))
                except Exception:
                    repo.record_task_event(TaskEvent(task_id=task_id, step="工作流", status="失败：发生未分类错误"))
                    progress.update(label="创作失败", state="error")
                    st.error("创作服务暂时不可用。请检查模型设置后重试；已保存的内容不会受影响。")
        if variants := st.session_state.get("current_variants"):
            st.subheader("本次生成的 5 个差异化角度")
            selected_variant = st.selectbox("查看一篇文章", variants, format_func=lambda item: item.metadata["variant_angle"], key="variant-viewer")
            show_article(selected_variant, context="variant")

    with radar_tab:
        st.subheader("今日热点雷达")
        live_rows, live_warnings, live_refreshed_at = live_trends_snapshot()
        live_topics = [Topic.model_validate(row) for row in live_rows]
        if live_topics:
            st.success(f"已接入实时趋势源：{', '.join(sorted({item.source for item in live_topics}))}。最近刷新：{live_refreshed_at.replace('T', ' ')[:19]} UTC；数据仅作为选题线索，发布前仍需核验。")
            if live_warnings:
                st.warning("；".join(live_warnings))
            if st.button("立即刷新热点（清除 15 分钟缓存）", key="refresh-live-trends"):
                live_trends_snapshot.clear()
                st.rerun()
            exploding = sum(1 for item in live_topics if item.growth >= 70)
            high_value = sum(1 for item in live_topics if item.content_value >= 70 and item.competition <= 50)
            risky = sum(1 for item in live_topics if item.risk != "低")
            metrics = st.columns(3)
            metrics[0].metric("快速上升", exploding)
            metrics[1].metric("冷门高价值", high_value)
            metrics[2].metric("高风险提醒", risky)
            st.dataframe([{"选题": item.title, "实时来源": item.source, "热度": item.heat, "增长": item.growth, "竞争": item.competition, "爆款潜力指数": item.potential, "风险": item.risk} for item in live_topics], width="stretch", hide_index=True)
        else:
            st.warning("实时趋势源暂时没有返回数据；已降级展示已保存的用户选题，不将其伪装为实时热搜。")
            if live_warnings:
                st.caption("；".join(live_warnings))

        topics = repo.list_topics()
        if topics:
            st.caption("已保存的用户选题")
            st.dataframe([{"选题": item.title, "来源": item.source, "热度": item.heat, "增长": item.growth, "竞争": item.competition, "爆款潜力指数": item.potential, "风险": item.risk, "追踪": "是" if item.tracked else "否"} for item in topics], width="stretch", hide_index=True)
            chosen_topic = st.selectbox("选择选题进行追踪", topics, format_func=lambda item: item.title, key="tracked-topic")
            if st.button("切换追踪状态", key="toggle-tracking"):
                updated = chosen_topic.model_copy(update={"tracked": not chosen_topic.tracked})
                repo.save_topic(updated)
                st.success(f"已{'开始' if updated.tracked else '停止'}追踪：{updated.title}")
                st.rerun()
            tracked_topics = [item for item in topics if item.tracked]
            if tracked_topics and st.button("刷新已追踪选题的来源信号", key="refresh-tracked"):
                progress = st.status("正在刷新来源信号…", expanded=True)
                refreshed_count = 0
                for tracked in tracked_topics:
                    try:
                        result = search_provider().search(tracked.title, timespan="24h")
                        repo.save_topic(refresh_topic(tracked, result))
                        refreshed_count += 1
                        progress.write(f"已刷新：{tracked.title}（{len(result.evidence)} 条待核验来源）")
                    except Exception:
                        progress.write(f"暂时无法刷新：{tracked.title}；保留原有选题数据")
                progress.update(label=f"已完成 {refreshed_count}/{len(tracked_topics)} 个选题的来源信号刷新", state="complete")
                st.rerun()
        else:
            st.caption("尚无选题。请从“自动创作”输入关键词。")

    with library_tab:
        query = st.text_input("搜索历史文章")
        articles = repo.list_articles(query)
        if articles:
            selected = st.selectbox("选择文章", articles, format_func=lambda item: f"{item.title} · {item.created_at:%Y-%m-%d %H:%M}")
            show_article(selected, context="library")
        else:
            st.caption("尚未保存文章。")

    with settings_tab:
        st.subheader("模型与 API 设置")
        st.warning("运行时密钥仅保存在当前浏览器会话，不会写入 SQLite、文章历史或日志。生产部署密钥请通过 Streamlit Secrets / Secret Manager 配置。")
        profiles = st.session_state.setdefault("model_profiles", {})
        st.caption(f"当前会话已有 {len(profiles)} 个模型配置档。API Key 不会持久化。")
        with st.form("model_settings"):
            profile_name = st.text_input("配置档名称", placeholder="例如：低成本分析模型")
            base_url = st.text_input("API Base URL", value="https://api.openai.com/v1")
            api_key = st.text_input("API Key", type="password")
            model = st.text_input("Model Name")
            enabled = st.checkbox("启用该配置档", value=True)
            saved = st.form_submit_button("保存到本次会话")
        if saved:
            if not all([profile_name.strip(), api_key.strip(), model.strip()]):
                st.error("请填写配置档名称、API Key 和模型名。")
            else:
                profiles[profile_name.strip()] = {"enabled": enabled, "base_url": base_url, "api_key": api_key, "model": model}
                st.success("配置档已保存到本次会话。")
        if profiles:
            st.dataframe([{"配置档": name, "模型": config["model"], "Base URL": config["base_url"], "启用": config["enabled"]} for name, config in profiles.items()], width="stretch", hide_index=True)
            choices = list(profiles)
            routes = st.session_state.setdefault("model_routes", {})
            route_columns = st.columns(3)
            for column, workflow, label in zip(route_columns, ("analysis", "writing", "quality"), ("分析", "写作", "质量")):
                default = choices.index(routes[workflow]) if routes.get(workflow) in choices else 0
                routes[workflow] = column.selectbox(f"{label}模型", choices, index=default, key=f"route-{workflow}")
        with st.form("image_settings"):
            pexels_key = st.text_input("Pexels Image API Key（可选）", value=st.session_state.get("pexels_api_key", ""), type="password")
            saved_image = st.form_submit_button("保存图片配置到本次会话")
        if saved_image:
            st.session_state["pexels_api_key"] = pexels_key
            st.success("图片配置已保存到本次会话。检索结果仍需人工审核。")
        if st.button("测试连接"):
            if not profiles:
                st.error("请先保存至少一个模型配置档。")
            else:
                selected = st.session_state.get("model_routes", {}).get("writing", next(iter(profiles)))
                cfg = profiles[selected]
                ok, message = OpenAICompatibleProvider(cfg["api_key"], cfg["base_url"]).test_connection(model=cfg["model"])
                (st.success if ok else st.error)(message)

    with cost_tab:
        st.subheader("成本监控")
        st.caption("仅记录 Provider、模型、工作流、请求次数、可用 token 与成本估算；不会存储 API Key 或完整 Prompt。当前通用兼容接口无法可靠返回 token/cost，故显示为 0。")
        total_columns = st.columns(4)
        current_article = st.session_state.get("current_article")
        totals = [repo.task_usage_totals(current_article.task_id) if current_article else {"requests": 0, "tokens": 0, "cost": 0.0}, repo.usage_totals("today"), repo.usage_totals("week"), repo.usage_totals("month")]
        for column, label, total in zip(total_columns, ("本次任务", "今日", "本周", "本月"), totals):
            column.metric(label, f"{total['requests']} 次", f"{total['tokens']} tokens · 估算 ${total['cost']:.4f}")
        summary = repo.usage_summary()
        if summary:
            st.dataframe(summary, width="stretch", hide_index=True)
        else:
            st.caption("暂无模型调用记录。")


if __name__ == "__main__":
    main()
