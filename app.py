import streamlit as st
import requests
from openai import OpenAI


st.set_page_config(
    page_title="我的头条创作工具",
    page_icon="📝"
)


st.title("📝 我的头条创作工具")

st.write("AI生成文章 + 自动配图")


topic = st.text_input(
    "文章主题",
    placeholder="例如：为什么越来越多人不愿意存钱"
)


word_count = st.number_input(
    "文章字数",
    min_value=300,
    max_value=5000,
    value=1500
)


def get_images(keyword):

    url = "https://api.pexels.com/v1/search"

    headers = {
        "Authorization": st.secrets["PEXELS_API_KEY"]
    }

    params = {
        "query": keyword,
        "per_page": 3
    }

    response = requests.get(
        url,
        headers=headers,
        params=params
    )

    data = response.json()

    images = []

    for item in data.get("photos", []):
        images.append(
            item["src"]["large"]
        )

    return images



if st.button("🚀 开始生成"):

    if not topic:

        st.warning("请输入主题")

    else:

        with st.spinner("AI正在写文章..."):

            client = OpenAI(
                api_key=st.secrets["DEEPSEEK_API_KEY"],
                base_url="https://api.deepseek.com"
            )


            result = client.chat.completions.create(

                model="deepseek-chat",

                messages=[

                    {
                        "role":"system",
                        "content":
                        "你是一名今日头条爆款文章作者。"
                    },

                    {
                        "role":"user",
                        "content":
                        f"""
写一篇今日头条文章。

主题：
{topic}

字数：
{word_count}

要求：
标题吸引人，
适合手机阅读，
分段清晰。
"""
                    }

                ]

            )


            article = result.choices[0].message.content


        st.success("文章生成完成")

        st.write(article)


        st.subheader("🖼 推荐配图")


        images = get_images(topic)


        for img in images:

            st.image(img)
