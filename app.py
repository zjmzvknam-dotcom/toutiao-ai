import streamlit as st
import requests
from openai import OpenAI
import json


st.set_page_config(
    page_title="我的头条创作工具",
    page_icon="📝"
)


st.title("📝 我的头条创作工具")

st.write("AI生成文章 + 智能匹配配图")


topic = st.text_input(
    "文章主题",
    placeholder="请输入文章主题"
)


word_count = st.number_input(
    "文章字数",
    min_value=500,
    max_value=5000,
    value=1500
)



def search_image(keyword):

    url = "https://api.pexels.com/v1/search"

    headers = {
        "Authorization": st.secrets["PEXELS_API_KEY"]
    }

    params = {
        "query": keyword,
        "per_page": 1
    }


    r = requests.get(
        url,
        headers=headers,
        params=params
    )


    data = r.json()


    if data.get("photos"):

        return data["photos"][0]["src"]["large"]

    return None




if st.button("🚀 开始生成"):


    if not topic:

        st.warning("请输入主题")


    else:


        with st.spinner("AI正在规划文章和图片..."):


            client = OpenAI(
                api_key=st.secrets["DEEPSEEK_API_KEY"],
                base_url="https://api.deepseek.com"
            )


            response = client.chat.completions.create(

                model="deepseek-chat",

                messages=[

                    {
                        "role":"system",
                        "content":
                        """
你是一名今日头条爆款作者。

请返回JSON格式。

必须包含：

title:
文章标题

sections:
文章段落数组，每个段落包含：
text:正文
image_keyword:对应图片关键词

例如：
[
{
"text":"正文内容",
"image_keyword":"年轻人看工资账单"
}
]

不要输出其它文字。
"""
                    },


                    {
                        "role":"user",
                        "content":
                        f"""
主题：
{topic}

字数：
{word_count}

生成适合今日头条的文章。
"""
                    }

                ]

            )


            content = response.choices[0].message.content


            article_data = json.loads(content)



        st.success("生成完成！")


        st.header(article_data["title"])


        for section in article_data["sections"]:


            st.write(section["text"])


            img = search_image(
                section["image_keyword"]
            )


            if img:

                st.image(
                    img,
                    caption=section["image_keyword"]
                )
