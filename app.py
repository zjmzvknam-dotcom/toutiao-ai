import streamlit as st
import requests
import json
import os
from openai import OpenAI


# ===============================
# 页面设置
# ===============================

st.set_page_config(
    page_title="今日头条AI创作工具",
    page_icon="🔥",
    layout="centered"
)


# ===============================
# API配置
# ===============================

DEEPSEEK_API_KEY = st.secrets.get(
    "DEEPSEEK_API_KEY",
    os.getenv("DEEPSEEK_API_KEY")
)

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)


# ===============================
# 标题生成
# ===============================

def generate_titles(topic):

    prompt = f"""
你是一名今日头条爆款作者。

请根据主题：

{topic}

生成5个适合今日头条的高点击标题。

要求：
1. 中文标题
2. 有吸引力
3. 不夸张违规
4. 符合普通读者兴趣
5. 每行一个标题

不要解释。
"""


    response = client.chat.completions.create(

        model="deepseek-chat",

        messages=[
            {
                "role":"user",
                "content":prompt
            }
        ],

        temperature=0.8
    )


    return response.choices[0].message.content



# ===============================
# 文章生成
# ===============================


def generate_article(title, word_count):

    prompt=f"""

你是一名优秀的今日头条原创作者。

请围绕标题：

《{title}》

写一篇原创文章。

要求：

字数约 {word_count} 字。

文章风格：

- 像真实作者写作
- 适合手机阅读
- 多分段
- 有故事感
- 有真实案例
- 有个人观点

禁止：

- Markdown符号
- #标题
- **加粗**
- 代码
- 图片说明
- AI提示词

直接输出文章正文。


"""


    response = client.chat.completions.create(

        model="deepseek-chat",

        messages=[
            {
                "role":"user",
                "content":prompt
            }
        ],

        temperature=0.7
    )


    return response.choices[0].message.content



# ===============================
# 图片生成
# ===============================


def generate_image(prompt):

    url="https://api.openai.com/v1/images/generations"


    return None
    # ===============================
# Streamlit界面
# ===============================


st.title("🔥 今日头条AI创作工具")

st.write(
    "AI生成爆款标题 + 原创文章 + 配图"
)



# 输入主题

topic = st.text_input(
    "请输入文章主题",
    value="为什么越来越多年轻人选择租房而不是买房"
)



# 字数

word_count = st.slider(
    "目标字数",
    min_value=800,
    max_value=3000,
    value=1500,
    step=100
)



# 保存状态

if "titles" not in st.session_state:
    st.session_state.titles = []


if "article" not in st.session_state:
    st.session_state.article = ""



# ===============================
# 生成标题按钮
# ===============================


if st.button("🔥 生成爆款标题"):

    with st.spinner("正在生成标题..."):

        try:

            result = generate_titles(topic)


            titles=[]

            for line in result.split("\n"):

                line=line.strip()

                if line:

                    titles.append(
                        line.replace(
                            "1.",
                            ""
                        ).replace(
                            "2.",
                            ""
                        ).replace(
                            "3.",
                            ""
                        ).replace(
                            "4.",
                            ""
                        ).replace(
                            "5.",
                            ""
                        )
                    )


            st.session_state.titles=titles


        except Exception as e:

            st.error(
                f"标题生成失败：{e}"
            )



# 显示标题选择


if st.session_state.titles:


    st.subheader(
        "请选择标题"
    )


    selected = st.radio(

        "标题",

        st.session_state.titles

    )


    st.session_state.selected_title=selected



    # ===============================
    # 生成文章
    # ===============================


    if st.button("✍️ 生成文章"):


        with st.spinner("正在创作文章..."):


            try:


                article = generate_article(

                    st.session_state.selected_title,

                    word_count

                )


                st.session_state.article=article



            except Exception as e:


                st.error(

                    f"文章生成失败：{e}"

                )



# ===============================
# 显示文章
# ===============================


if st.session_state.article:


    st.divider()


    st.subheader(
        "文章内容"
    )


    st.write(
        st.session_state.article
    )


    st.download_button(

        label="📥 下载文章",

        data=st.session_state.article,

        file_name="今日头条文章.txt",

        mime="text/plain"

    )
    # ===============================
# AI配图模块
# ===============================


st.divider()


if st.session_state.article:


    st.subheader(
        "🖼️ AI生成文章配图"
    )


    image_prompt = st.text_area(

        "图片描述",

        value=(
            "根据文章主题生成一张适合今日头条封面的图片，"
            "要求高清、有吸引力、符合中文自媒体风格"
        )

    )



    if st.button("🎨 生成配图"):


        with st.spinner(
            "正在生成图片..."
        ):


            try:


                image_url = generate_image(

                    image_prompt

                )


                st.image(

                    image_url,

                    caption="AI生成配图"

                )


                st.session_state.image=image_url



            except Exception as e:


                st.error(

                    f"图片生成失败：{e}"

                )



# ===============================
# 文章排版预览
# ===============================


if st.session_state.article:


    st.divider()


    st.subheader(
        "📱 今日头条排版预览"
    )


    preview = f"""

{st.session_state.selected_title}


{st.session_state.article}


"""



    st.text_area(

        "复制发布",

        preview,

        height=500

    )



# ===============================
# 页脚
# ===============================


st.divider()


st.caption(

    "今日头条AI创作工具 | DeepSeek驱动"

)
