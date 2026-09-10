import streamlit as st


st.set_page_config(
    page_title="我的头条创作工具",
    page_icon="📝"
)


st.title("📝 我的头条创作工具")


st.write("输入主题，自动生成今日头条文章。")


topic = st.text_input(
    "文章主题"
)


word_count = st.number_input(
    "文章字数",
    min_value=300,
    max_value=5000,
    value=1500
)


if st.button("🚀 开始生成文章"):

    if topic:

        st.success("生成成功！")

        st.write(
            f"""
你的文章主题：

{topic}


目标字数：

{word_count} 字


下一步将接入 DeepSeek AI 自动写文章。
"""
        )

    else:

        st.warning("请输入文章主题")
