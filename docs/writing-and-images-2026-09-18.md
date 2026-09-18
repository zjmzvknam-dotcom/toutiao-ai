# 写作人格与可选 AI 配图增量验收

## 修改原因

原 Writer 只收到人格名称，Planner 却给所有选题同一套新闻分析结构，导致情感和生活文章也写成“已知信息、影响、争议、待观察”。现在十种人格分别定义词汇、句长、语气、关注点、情绪、举例、开头、转折、结尾和判断；Planner 和 Writer 使用同一个 profile。

新增本地风格检查，不把单个连接词判为错误；只有连接词/模板密集、段长高度一致或连续小标题等信号才做局部编辑。最多一次额外写作调用、两段，不做默认全文重写。数字、引号内容、链接和英文专名变化会拒绝采用；润色失败保留原稿。这不是事实核查器，也不是 AI 检测规避工具。

## GitHub 研究与选择（2026-09-18）

检查了仓库 API 的许可证及最近 push 状态，维护活跃不等于本项目已经集成或调用成功。

| 项目 | 许可/维护观察 | 本次处理 |
|---|---|---|
| [blader/humanizer](https://github.com/blader/humanizer) | MIT，2026-09 有更新 | 借鉴先识别机械表达、保留观点的编辑思路，不导入其技能或复制代码 |
| [ai-zixun/humanizer-zh](https://github.com/ai-zixun/humanizer-zh) | MIT，2026-05 有更新 | 参考中文上下文、语气与节奏问题；自行编写规则及 profile |
| [ComfyUI](https://github.com/Comfy-Org/ComfyUI) | GPL-3.0，2026-09 活跃 | 适合复杂图像工作流；本次不部署服务端和 GPU |
| [comfy-python-sdk](https://github.com/Comfy-Org/comfy-python-sdk) | MIT，2026-09 活跃 | 云工作流可行，但当前单图需求无需维护 workflow JSON |
| [Diffusers](https://github.com/huggingface/diffusers) | Apache-2.0，2026-09 活跃 | 不在 Streamlit 安装 torch 和模型权重 |
| [FLUX](https://github.com/black-forest-labs/flux) | 代码 Apache-2.0，最近 push 2025-07 | 权重许可单独核验，默认可更换模型为 FLUX.1-schnell |
| [Stable Diffusion WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui) | AGPL-3.0，2026-03 有更新 | 需另管推理主机，本次不安装 |

正式集成的是官方 [huggingface_hub InferenceClient](https://huggingface.co/docs/huggingface_hub/package_reference/inference_client) 云推理接口。新增直接依赖 `huggingface_hub`，显式声明原本由 Streamlit 间接安装的 `Pillow`。不引入上述大型应用。

[FLUX.1-schnell 模型卡](https://huggingface.co/black-forest-labs/FLUX.1-schnell) 标注 Apache-2.0。HF 公共模型元数据在检查时列出 fal-ai、nscale、wavespeed 可提供 text-to-image，together 显示 error；实际可用性、额度和费用仍取决于账户。`auto` 由 HF 路由，用户也可指定 Provider。

## 图片行为

- 创作页“在文章中插入 AI 配图”默认关闭；关闭时不创建客户端、不调用规划或生图。
- 开启后：先生成并保存正文，再一次性规划段落视觉主体，验证原文摘句、索引和通用场景标志后调用图片服务。
- 按正文长度最多 1/2/3/4 张，允许更少或零张；不是每段都配。多角度模式仅第一篇配图，页面已提示。
- 写实摄影、自然光、无文字水印 logo；新闻现场/真实人物由保守关键词和规划约束跳过。语义检查不是完美识别器，发布前仍需检查实际画面。
- 每图保存段落哈希、主体、Prompt、Provider、模型和压缩 JPEG，不保存密钥。显示“AI生成示意图 · 非现场照片”，按对应段落插入。编辑正文移除旧图，导出 Word 带图片与标记。
- 不自动重试；单次图片请求 timeout 45 秒，工作流超过 120 秒后不再发新请求（在途请求仍可能占用其超时时间）。失败停止后续图片调用，正文不丢失。
- 记录文字/规划/图片请求次数；未接价格账单，费用估算 0 不代表免费。

## 配置

网页：模型设置 → AI 生图配置 → 输入有推理权限及额度的 Hugging Face Token。默认模型可修改，Provider 默认为 auto。密钥仅在 Session 使用。

云端持久配置：Streamlit Secrets 或环境变量 `HF_TOKEN`、`AI_IMAGE_MODEL`、`AI_IMAGE_PROVIDER`。请勿在聊天或 GitHub 提交真实 Token。默认图片模型为 `black-forest-labs/FLUX.1-schnell`，写作继续使用已有可配置路由。

## 中文真实模型对比

使用同一 deepseek-chat、650 字目标，分别测试情感、消费、生活三题，并额外切换退休老人和数码爱好者视角。实际字数会有浮动，不额外整篇重写凑字数。原始输出保存在本地 `outputs/writing-evaluation`（gitignored）。

| 题目/人格 | 优化前 | 修订后的观察 |
|---|---|---|
| 中年人的心酸 / 普通上班族 | 转向统计、行业与公共政策，生活情感被分析框架盖住 | 改为消息打断、通勤、饭点和家庭之间的时间挤压，短句与自嘲更明确 |
| 旧手机还能用，要不要换新手机 / 年轻消费者 | 已知信息、三层影响、行业、待观察信号 | 围绕预算、营销冲动和真正需要，口语较多，部分总结仍可人工压缩 |
| 周末去菜市场买菜 / 普通城市居民 | 大量“没有统计数据、待核验”的系统腔 | 布袋、公交、通道与采购便利；仍有关于市场/配送的泛化判断，不应当作已核验报道 |
| 中年人的心酸 / 退休老人 | 首轮优化曾虚构邻居对话和亲历，判为不通过 | 强化人格不是履历后，重跑改为精力、生活习惯、长远安心，语速比上班族舒缓，不再出现虚构老周故事；仍有抒情总结 |
| 旧手机还能用，要不要换新手机 / 数码爱好者 | — | 关注续航、存储、使用摩擦和维护，而非年轻消费者的预算焦虑。模型给出的换机阈值没有权威依据，需作为个人建议审阅，不能包装成技术标准 |

五篇修订样本的局部润色调用均为 0；风格规则没触发，不代表质量满分或事实正确。不同人格可读出关注点及语气差异，但不是作者风格的统计学验证，也不保证每次输出都自然。保留首轮失败样本，不用新结果覆盖它。

## 测试与限制

自动化覆盖：十种人格传递、连接词非一刀切、单次两段润色、事实锚点保护、润色失败；配图零调用、缺密钥、失败脱敏、敏感题材跳过、段落定位、持久化、无重复生成、Word/Markdown 带图、官方 SDK 调用契约、Streamlit 首次生成/编辑/重复生成与配图缺密钥提示。

图片成功路径使用测试图片，不能视为真实 FLUX 画质验收。当前环境没有可用图片 Token，因此真实付费推理、画面与段落的视觉核验尚未完成。没有对此宣称成功。

SQLite 仍保留现有 Cloud 临时磁盘限制，重部署可能丢失历史；本次没有扩展数据库架构。正文、图片建议及时下载。文中事实和 AI 图片发布前仍需人工核验。
