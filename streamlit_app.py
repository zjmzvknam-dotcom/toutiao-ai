from __future__ import annotations

import os
import base64
from app.config.model_config import deployed_model
import json
from pathlib import Path
from uuid import uuid4

import streamlit as st

from app.config.settings import settings
from app.models.domain import Article, TaskEvent, Topic, ImageCandidate
from app.providers import CachedSearchProvider, GDELTDocumentProvider, ModelRouter, MultiModelRouter, MultiSourceTrendProvider, OpenAICompatibleProvider, PexelsImageProvider, ResilientSearchProvider, RoutedModel
from app.providers.images import WikimediaCommonsImageProvider
from app.providers.image_generation import configured_generator, DEFAULT_IMAGE_MODEL
from app.services.personas import PROFILES
from app.services.illustrations import illustrate, inline_content
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
    if not config.get("api_key"):
        values = dict(os.environ)
        try:
            values.update(dict(st.secrets))
        except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
            pass
        config = deployed_model(values)
    if not config.get("enabled") or not config.get("api_key") or not config.get("model"):
        return ModelRouter(None)
    provider = OpenAICompatibleProvider(config["api_key"], config["base_url"])
    return ModelRouter(provider, {"analysis": config["model"], "writing": config["model"], "quality": config["model"]})


def save_visible_article(article: Article, context: str) -> None:
    repository().save_article(article)
    current = st.session_state.get("current_article")
    if context == "current" or (current and current.id == article.id):
        st.session_state["current_article"] = article


def image_config() -> dict:
    values = dict(os.environ)
    try:
        values.update(dict(st.secrets))
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        pass
    values.update(st.session_state.get("ai_image_config", {}))
    return values


def show_article(article: Article, *, context: str) -> None:
    legacy = article.model == "本地降级模板" or "系统基于离线启发式生成的初步判断" in article.body
    if legacy:
        st.error("这条历史记录是旧版生成的通用模板，不是可使用的文章。连接写作模型后，请重新生成。")
        with st.expander("查看旧记录（保留原数据）"):
            st.text(article.body)
        return
    st.subheader(article.title)
    st.caption(f"正文 · {len(article.body)} 字 · 已保存。可直接复制正文或下载 Word。")
    render_copy_button(f"{article.title}\n\n{article.body}", "复制全文")
    st.download_button("下载 Word", word_document(article), f"{article.id}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", key=f"{context}-{article.id}-docx")
    image_report = article.metadata.get("ai_images", {})
    if image_report:
        (st.warning if image_report.get("failed") else st.caption)(image_report["status"])
    if not article.illustrations:
        st.markdown(article.body)
    else:
        for paragraph, illustrations in inline_content(article):
            st.markdown(paragraph)
            for illustration in illustrations:
                st.image(base64.b64decode(illustration.image_b64), caption=illustration.label)
    if article.image.verified and article.image.url:
        st.image(article.image.url, caption=article.image.label)
    st.divider()
    with st.expander("编辑正文 / 其他下载"):
        with st.form(f"{context}-{article.id}-edit"):
            title = st.text_input("标题", value=article.title)
            body = st.text_area("完整正文", value=article.body, height=400)
            edited = st.form_submit_button("保存修改")
        if edited:
            if title.strip() and body.strip():
                changed = body.strip() != article.body.strip()
                metadata = dict(article.metadata)
                if changed and article.illustrations:
                    metadata["ai_images"] = {"status": "正文已修改，旧 AI 配图已移除以免错位。", "failed": False}
                save_visible_article(article.model_copy(update={"title": title.strip(), "body": body.strip(), "illustrations": [] if changed else article.illustrations, "metadata": metadata}), context)
                st.rerun()
            st.error("标题和正文不能为空。")
        render_copy_button(article.body, "复制正文")
        st.download_button("下载 TXT", plain_text(article), f"{article.id}.txt", "text/plain", key=f"{context}-{article.id}-txt")
        st.download_button("下载 Markdown", markdown(article), f"{article.id}.md", "text/markdown", key=f"{context}-{article.id}-md")
    with st.expander("配图：搜索、选择或更换"):
        if article.illustrations and st.button("移除 AI 配图（保留正文）", key=f"{context}-{article.id}-remove-ai-images"):
            save_visible_article(article.model_copy(update={"illustrations": [], "metadata": {**article.metadata, "ai_images": {"status": "AI 配图已移除，正文保留。", "failed": False}}}), context)
            st.rerun()
        st.caption("请填写具体画面，如“黄昏街道”或“中年人背影”。搜索结果仅供挑选，选择后才出现在正文。")
        query = st.text_input("想要的画面", key=f"{context}-{article.id}-image-query")
        if st.button("查找配图", key=f"{context}-{article.id}-image-search"):
            if not query.strip():
                st.info("先填写想要的画面。")
            else:
                try:
                    pexels_key = st.session_state.get("pexels_api_key", "")
                    provider = PexelsImageProvider(pexels_key) if pexels_key else WikimediaCommonsImageProvider()
                    candidates = provider.find(query.strip(), limit=5)
                    st.session_state[f"image-candidates-{article.id}"] = candidates
                    if not candidates:
                        st.info("没有找到符合格式和描述的图片，请换一个具体画面。")
                except Exception:
                    st.session_state[f"image-candidates-{article.id}"] = []
                    st.warning("图片搜索暂时不可用，正文仍可复制和下载。")
        for index, candidate in enumerate(st.session_state.get(f"image-candidates-{article.id}", [])):
            st.image(candidate.url, caption=candidate.source)
            confirmed = st.checkbox("这张图适合正文，我已查看来源与使用许可", key=f"{context}-{article.id}-confirm-{index}")
            if st.button("使用这张配图", key=f"{context}-{article.id}-choose-{index}", disabled=not confirmed):
                approved = candidate.model_copy(update={"verified": True, "label": "配图（用户选择）"})
                save_visible_article(article.model_copy(update={"image": approved}), context)
                st.rerun()
        if article.image.url and st.button("移除本文配图", key=f"{context}-{article.id}-remove-image"):
            save_visible_article(article.model_copy(update={"image": ImageCandidate()}), context)
            st.rerun()
    with st.expander("参考资料与检查结果"):
        st.caption(f"写作模型：{article.model}")
        if article.metadata.get("warning"):
            st.caption(article.metadata["warning"])
        for item in article.evidence:
            if item.source_url:
                st.write(item.claim)
                st.link_button(item.source_name, item.source_url)
        for note in article.quality.notes:
            st.caption(note)


def main() -> None:
    repo = repository()
    st.title("今日头条 AI 内容创作工作台")
    st.caption("以真实性、质量与可维护性为先。AI 评分为辅助估计，不保证流量、审核或“真人原创”。")
    create_tab, radar_tab, library_tab, settings_tab, cost_tab = st.tabs(["🚀 自动创作", "📡 热点雷达", "📚 我的文章", "⚙️ 模型设置", "💰 成本"])

    with create_tab:
        active_router = router_from_session()
        if not active_router.model_for("writing"):
            st.error("尚未连接写作模型。旧版显示的通用模板无法当作文章使用，请先在下方连接模型。")
            with st.expander("连接写作模型", expanded=True):
                with st.form("quick_model_connection"):
                    quick_base = st.text_input("接口地址", value="https://api.deepseek.com")
                    quick_model = st.text_input("模型名称", value="deepseek-chat")
                    quick_key = st.text_input("API Key", type="password")
                    connect = st.form_submit_button("连接并检查")
                if connect:
                    if not quick_key.strip() or not quick_model.strip():
                        st.error("请填写 API Key 和模型名称。")
                    else:
                        ok, message = OpenAICompatibleProvider(quick_key, quick_base).test_connection(model=quick_model)
                        if ok:
                            st.session_state["model_config"] = {"enabled": True, "api_key": quick_key, "base_url": quick_base, "model": quick_model}
                            st.rerun()
                        st.error(message)
                st.caption("密钥只用于本次连接。若希望刷新网页后仍可用，可由部署者配置 Streamlit Secrets 中的 DEEPSEEK_API_KEY。")
        result_area = st.container()
        with st.form("create_article"):
            keyword = st.text_input("关键词或选题", placeholder="例如：小米汽车")
            col1, col2, col3 = st.columns(3)
            length = col1.select_slider("目标字数", options=[600, 900, 1200, 1600, 2200], value=900)
            persona = col2.selectbox("作者人格", list(PROFILES))
            images = col3.checkbox("在文章中插入 AI 配图", value=False)
            col3.caption("默认关闭，关闭时图片费用为零。开启需在模型设置配置图片服务。")
            requirement = st.text_area("写作要求（可选）", placeholder="例如：关注普通消费者的影响，避免未经核实的结论。")
            with st.expander("专业模式"):
                search_enabled = st.checkbox("使用 GDELT 新闻资料搜索（资料均需人工核验）", value=False)
                time_range = st.selectbox("资料时间范围", ["1h", "6h", "24h", "3d", "7d"], index=2)
                generate_variants = st.checkbox("一个选题生成 5 篇不同角度文章", value=False)
                st.caption("多角度模式开启配图时，只为第一篇配图，避免一次产生五倍图片费用。")
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
                        article = workflow.run(topic, length=length, persona=persona, requirement=requirement, with_images=False, use_research=search_enabled, timespan=time_range, existing_bodies=existing_bodies, task_id=task_id, confirmed_high_risk=high_risk_confirmed, progress=emit)
                        repo.save_article(article)
                        for event in task_events:
                            repo.record_task_event(event)
                    # Persist usable text before contacting an optional image service.
                    st.session_state["current_article"] = article
                    if images:
                        progress.write("正文已保存，正在按段落生成 AI 配图…")
                        article = illustrate(article, active_router, configured_generator(image_config()), enabled=True)
                        repo.save_article(article)
                        if generate_variants:
                            articles[0] = article
                    for usage in active_router.usage_log:
                        repo.record_usage(**usage, task_id=article.task_id)
                    for _ in range(article.metadata.get("ai_images", {}).get("calls", 0)):
                        cfg = image_config()
                        repo.record_usage("Hugging Face", str(cfg.get("AI_IMAGE_MODEL", DEFAULT_IMAGE_MODEL)), "AI配图", task_id=article.task_id)
                    progress.update(label="创作完成", state="complete")
                    st.session_state["current_article"] = article
                    st.session_state.pop("current_variants", None) if not generate_variants else None
                    st.rerun()
                except ValueError as exc:
                    repo.record_task_event(TaskEvent(task_id=task_id, step="工作流", status=f"拒绝：{exc}"))
                    progress.update(label="需要调整选题", state="error")
                    st.warning(str(exc))
                except Exception:
                    repo.record_task_event(TaskEvent(task_id=task_id, step="工作流", status="失败：发生未分类错误"))
                    progress.update(label="创作失败", state="error")
                    st.error("创作服务暂时不可用。请检查模型设置后重试；已保存的内容不会受影响。")
        with result_area:
            current_article = st.session_state.get("current_article")
            if current_article:
                show_article(current_article, context="current")
                st.divider()
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
        with st.expander("AI 生图配置（云端推理，无需本地 GPU）"):
            image_values = image_config()
            st.caption("采用 Hugging Face Inference Providers；与写作模型密钥独立。需要有推理权限和额度的 Token。模型和 Provider 可更换。")
            with st.form("ai_image_settings"):
                hf_token = st.text_input("Hugging Face Token", type="password", help="留空保留部署密钥；不写入文章或 GitHub。")
                image_model = st.text_input("AI 图片模型", value=str(image_values.get("AI_IMAGE_MODEL", DEFAULT_IMAGE_MODEL)), placeholder="例如 black-forest-labs/FLUX.1-schnell")
                image_provider = st.text_input("AI 图片 Provider", value=str(image_values.get("AI_IMAGE_PROVIDER", "auto")))
                save_ai_images = st.form_submit_button("保存 AI 生图配置")
            if save_ai_images:
                config = {"AI_IMAGE_MODEL": image_model.strip(), "AI_IMAGE_PROVIDER": image_provider.strip() or "auto"}
                if hf_token.strip():
                    config["HF_TOKEN"] = hf_token.strip()
                elif st.session_state.get("ai_image_config", {}).get("HF_TOKEN"):
                    config["HF_TOKEN"] = st.session_state["ai_image_config"]["HF_TOKEN"]
                st.session_state["ai_image_config"] = config
                st.success("配置已保存至本次会话。勾选配图并生成文章时才会调用生图服务。")
            st.caption("云端持久配置：HF_TOKEN、AI_IMAGE_MODEL、AI_IMAGE_PROVIDER。生成费用以 Provider 账单为准，不承诺免费。")
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
        st.caption("记录写作、局部润色、配图规划与图片请求次数，以及接口返回的 token。费用尚未接入账单，估算 0 不代表免费；实际金额以服务商账单为准。不存储密钥或完整 Prompt。")
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
