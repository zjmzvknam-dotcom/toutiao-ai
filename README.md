# 今日头条 AI 内容创作工作台

一个可扩展、可降级的 Streamlit 内容创作 MVP。核心工作流、数据仓储、模型路由和外部服务 Provider 均已隔离；外部服务未配置或失败时，文章和本地质量检查仍可用。

## 本地运行

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run streamlit_app.py
```

在“模型设置”中配置运行时 API Key。Key 只保留在当前浏览器会话，不写入文章库、SQLite、日志或源码。生产部署应通过 Streamlit Secrets 或专用 Secret Manager 注入部署级密钥。

“专业模式”可启用 GDELT DOC 2.0 新闻资料检索。它返回的是待人工核验的来源线索，不能自动成为文章事实；网络超时、无结果或服务故障时，创作流程会保留文章生成并标记为部分成功。

涉及医疗、投资、政治敏感、未成年人、未证实爆料、犯罪指控等高风险关键词时，系统默认不自动扩写。用户须在专业模式明确确认人工核验与合规责任，工作流才会继续。

可选配置 Pexels Image API Key 以检索附带摄影师和来源页信息的真实图片候选。候选不会自动插入文章，尤其不应把素材图库图片表述为新闻现场；必须人工确认人物、产品、时间、事件语境与使用许可。[Pexels API 文档](https://www.pexels.com/api/documentation/)

搜索层对相同关键词、时间窗口和数量使用 10 分钟 TTL 缓存，并采用有限重试与短时熔断，避免外部服务持续异常造成无意义请求。模型设置可在一个会话中保存多个兼容 API 配置档，并分别路由给分析、写作和质量任务。

## 架构

- `app/providers`：模型与外部服务的可替换适配层
- `app/workflows`：结构化、可降级的文章创作流程
- `app/services`：热点、质量、风险、导出、成本等领域服务
- `app/repositories`：SQLite 数据访问层；未来可替换 PostgreSQL 实现
- `app/models`：Pydantic 领域模型
- `app/ui`：Streamlit 页面组件

SQLite 适合本地开发；Streamlit Community Cloud 的本地磁盘不保证持久化，生产环境应替换为托管数据库。

领域模型已包含 `ContentType` 和 `PlatformAdapter` 边界。第一版仅完成今日头条文章适配；视频脚本、小红书、公众号、百家号和抖音图文会以独立适配器接入，不会把文章内容误称为其他平台的成品。

## 部署前检查

- 仅提交源码、`requirements.txt`、`runtime.txt` 和 `.streamlit/config.toml`；不要提交 `.streamlit/secrets.toml`、`.env` 或 SQLite 文件。
- 在 Streamlit Community Cloud 选择 `streamlit_app.py` 作为入口；配置部署级 Secret 时使用其 Secrets 管理界面。
- 如需持久化文章库，将 `SQLiteRepository` 替换为托管 PostgreSQL 的同接口实现。

完整上线步骤见 [DEPLOYMENT.md](DEPLOYMENT.md)。

## 测试

```powershell
pytest -q
```

测试使用 Fake Provider，不会调用付费模型或外部 API。

部署前可运行：

```powershell
python scripts/check_deploy.py
```

推送到 GitHub 后，[`.github/workflows/verify.yml`](.github/workflows/verify.yml) 会在 push 和 pull request 时执行编译、测试与部署预检；CI 不需要、也不读取任何模型密钥。
