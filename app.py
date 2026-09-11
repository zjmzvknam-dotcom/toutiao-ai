import streamlit as st
from openai import OpenAI


st.set_page_config(
    page_title="我的头条创作工具",
    page_icon="📝"
)


st.title("📝 我的头条创作工具")


st.write("输入主题，AI自动生成今日头条文章。")


topic = st.text_input(
    "文章主题",
    placeholder="例如：为什么现在越来越多人不愿意存钱了"
)


word_count = st.number_input(
    "文章字数",
    min_value=300,
    max_value=5000,
    value=1500
)


if st.button("🚀 开始生成文章"):

    if not topic:

        st.warning("请输入文章主题")

    else:

        with st.spinner("AI正在创作，请稍等..."):

            client = OpenAI(
                api_key=st.secrets["DEEPSEEK_API_KEY"],
                base_url="https://api.deepseek.com"
            )


            result = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {
                        "role": "system",
                        "content": "你是一名优秀的今日头条作者，擅长写爆款中文文章。"
                    },
                    {
                        "role": "user",
                        "content": f"""
请写一篇今日头条文章。

主题：
{topic}

字数：
{word_count}字

要求：
1. 标题吸引人
2. 开头抓住读者
3. 内容分段清晰
4. 适合手机阅读
"""
                    }
                ]
            )


            article = result.choices[0].message.content


            st.success("文章生成完成！")

            st.write(article)
