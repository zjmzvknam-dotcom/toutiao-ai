import streamlit as st
import requests
import json
from openai import OpenAI


st.set_page_config(
    page_title="我的头条创作工具",
    page_icon="📝"
)


st.title("📝 我的头条创作工具")

st.write("AI爆款标题 + 文章生成 + 智能配图")


topic = st.text_input(
    "输入文章主题",
    placeholder="例如：为什么越来越多人不愿意存钱"
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




def ai_request(messages):

    client = OpenAI(
        api_key=st.secrets["DEEPSEEK_API_KEY"],
        base_url="https://api.deepseek.com"
    )


    result = client.chat.completions.create(

        model="deepseek-chat",

        messages=messages

    )


    return result.choices[0].message.content




if "titles" not in st.session_state:

    st.session_state.titles = []



if "article" not in st.session_state:

    st.session_state.article = None





if st.button("🔥 生成爆款标题"):


    if topic:


        with st.spinner("AI正在想标题..."):


            titles = ai_request([

                {
                    "role":"system",
                    "content":
                    """
你是今日头条爆款标题专家。

根据主题生成5个高点击标题。

要求：
1. 有吸引力
2. 不夸张违规
3. 符合今日头条风格

只输出标题，每行一个。
"""
                },

                {
                    "role":"user",
                    "content":topic
                }

            ])


            st.session_state.titles = titles.split("\n")


    else:

        st.warning("请输入主题")





if st.session_state.titles:


    st.subheader("请选择一个标题")


    selected = st.radio(

        "标题列表",

        st.session_state.titles

    )



    if st.button("✍️ 开始写文章"):


        with st.spinner("AI正在创作文章..."):


            article = ai_request([

                {
                    "role":"system",
                    "content":
                    """
你是一名今日头条资深作者。

返回JSON格式：

{
"title":"",
"sections":[
{
"text":"",
"image_keyword":""
}
]
}

要求：
3个正文部分。
每部分对应一个具体图片关键词。
"""
                },

                {
                    "role":"user",
                    "content":
                    f"""
标题：

{selected}

字数：

{word_count}
"""
                }

            ])


            st.session_state.article = json.loads(article)





if st.session_state.article:


    data = st.session_state.article


    st.header(data["title"])


    image_num = 0


    for section in data["sections"]:


        st.write(section["text"])


        if image_num < 3:


            img = search_image(
                section["image_keyword"]
            )


            if img:

                st.image(
                    img,
                    caption=section["image_keyword"]
                )

                image_num += 1
