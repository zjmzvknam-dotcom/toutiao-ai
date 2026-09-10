import streamlit as st

st.set_page_config(
    page_title="我的头条创作工具",
    page_icon="📝",
)

st.title("📝 我的头条创作工具")

st.write("输入一个主题，自动生成今日头条文章和配图。")

topic = st.text_input(
    "文章主题",
    placeholder="例如：为什么现在越来越多人不愿意存钱了",
)

word_count = st.number_input(
    "文章字数",
    min_value=300,
    max_value=5000,
    value=1500,
    step=100,
)

if st.button("🚀 开始生成文章", use_container_width=True):

    if not topic.strip():

        st.warning("请先输入文章主题。")

    else:

        st.success("网页已经正常工作！")

        st.info(
            f"你输入的主题是：{topic}\n\n"
            f"文章字数：{word_count} 字"
        )

        st.write(
            "下一步我们会把 DeepSeek AI 和 Pexels 配图接进来。"
        )
