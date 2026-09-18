# 部署到 GitHub 与 Streamlit Community Cloud

## 1. GitHub

1. 在 GitHub 创建一个空仓库，不要勾选自动生成 README。
2. 在本地工作区确认预检通过：

   ```powershell
   python scripts/check_deploy.py
   python -m pytest -q
   ```

3. 提交源码时，不要提交 `data/`、`.env`、`.streamlit/secrets.toml` 或任何 API Key。项目的 `.gitignore` 已覆盖这些文件。
4. 推送后，GitHub Actions 会执行 `.github/workflows/verify.yml`。

## 2. Streamlit Community Cloud

1. 连接该 GitHub 仓库。
2. 入口文件选择 `streamlit_app.py`，Python 版本由 `runtime.txt` 指定。
3. 初次部署可不填写模型密钥：应用会使用本地降级工作流，且不会伪造实时检索或模型结果。
4. 若配置部署级 Provider 密钥，应仅在 Streamlit 的 Secrets 管理界面保存。不要将密钥提交到仓库。

## 3. 持久化限制

当前 SQLite 仓储适合本地开发和演示。Streamlit Community Cloud 的本地磁盘不是可靠的长期数据库，因此生产环境应实现与 `SQLiteRepository` 同接口的 PostgreSQL 仓储。

## 4. 上线后验证

1. 打开首页，确认五个主 Tab 可用。
2. 不配置密钥完成一次离线创作，确认降级提示、导出和文章库工作正常。
3. 使用测试用模型密钥验证连接；确认密钥只显示为密码输入框且不出现在文章历史、日志或 GitHub。
4. 启用专业模式的资料搜索，确认来源被标为待人工核验。
5. 对高风险选题确认系统在未勾选人工核验前停止自动写作。
