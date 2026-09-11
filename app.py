import streamlit as st
import requests
import json
from openai import OpenAI


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


    response = requests.get(
        url,
        headers=headers,
        params=params
    )


    data = response.json()


    if data.get("photos"):

        return data["photos"][0]["src"]["large"]


    return None





if st.button("🚀 开始生成"):


    if not topic:

        st.warning("请输入文章主题")


    else:


        with st.spinner("AI正在创作文章，请稍等..."):


            client = OpenAI(
                api_key=st.secrets["DEEPSEEK_API_KEY"],
                base_url="https://api.deepseek.com"
            )


            result = client.chat.completions.create(

                model="deepseek-chat",

                messages=[

                    {
                        "role": "system",
                        "content":
                        """
你是一名今日头条爆款作者。

请严格返回JSON格式。

格式：

{
"title":"文章标题",
"sections":[
{
"text":"正文段落",
"image_keyword":"具体图片关键词"
}
]
}

要求：

1. 只生成3个主要正文段落
2. 每个段落生成一个图片关键词
3. 图片关键词必须具体
4. 不要写抽象词

例如：

错误：
年轻人压力

正确：
年轻人在出租屋查看账单

错误：
经济困难

正确：
家庭计算每月生活支出
"""
                    },


                    {
                        "role": "user",
                        "content":
                        f"""
主题：

{topic}


文章字数：

{word_count}

生成适合今日头条阅读的文章。
"""
                    }

                ]

            )


            text = result.choices[0].message.content


            article = json.loads(text)




        st.success("文章生成完成！")


        st.header(article["title"])



        image_count = 0


        for section in article["sections"]:


            st.write(section["text"])



            if image_count < 3:


                image = search_image(
                    section["image_keyword"]
                )


                if image:

                    st.image(
                        image,
                        caption=section["image_keyword"]
                    )


                    image_count += 1
