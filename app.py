import streamlit as st
import requests
import json
from openai import OpenAI


st.set_page_config(
    page_title="我的头条创作工具",
    page_icon="📝"
)


st.title("📝 我的头条创作工具")

st.write("AI爆款标题 + 长文章生成 + 智能配图")


topic = st.text_input(
    "文章主题",
    placeholder="例如：为什么现在越来越多人不愿意存钱了"
)


word_count = st.number_input(
    "目标字数",
    min_value=800,
    max_value=5000,
    value=1500
)



def deepseek(messages):

    client = OpenAI(
        api_key=st.secrets["DEEPSEEK_API_KEY"],
        base_url="https://api.deepseek.com"
    )


    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages
    )

    return response.choices[0].message.content



def search_image(keyword):

    try:

        url = "https://api.pexels.com/v1/search"

        headers = {
            "Authorization": st.secrets["PEXELS_API_KEY"]
        }

        params = {
            "query": keyword,
            "per_page": 1
        }


        result = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=10
        )


        if result.status_code != 200:
            return None


        data = result.json()


        if data.get("photos"):

            return data["photos"][0]["src"]["large"]


        return None


    except Exception:

        return None

    url = "https://api.pexels.com/v1/search"


    headers = {
        "Authorization": st.secrets["PEXELS_API_KEY"]
    }


    params = {
        "query": keyword,
        "per_page": 1
    }


    result = requests.get(
        url,
        headers=headers,
        params=params
    )


    data = result.json()


    if data.get("photos"):

        return data["photos"][0]["src"]["large"]


    return None



if "titles" not in st.session_state:
    st.session_state.titles = []


if "article" not in st.session_state:
    st.session_state.article = None



# 第一步：生成标题

if st.button("🔥 生成爆款标题"):


    if topic:


        with st.spinner("正在生成标题..."):


            text = deepseek([

                {
                    "role":"system",
                    "content":
                    """
你是今日头条爆款标题专家。

生成5个标题。

要求：
- 高点击率
- 有悬念
- 不违规
- 符合中文用户阅读习惯

每行一个标题。
"""
                },

                {
                    "role":"user",
                    "content":topic
                }

            ])


            st.session_state.titles = [
                x.strip()
                for x in text.split("\n")
                if x.strip()
            ]



    else:

        st.warning("请输入主题")





# 选择标题

if st.session_state.titles:


    st.subheader("选择文章标题")


    selected_title = st.radio(
        "标题",
        st.session_state.titles
    )



    if st.button("✍️ 开始生成文章"):


        with st.spinner("正在创作长文章..."):


            result = deepseek([

                {
                    "role":"system",
                    "content":
                    """
你是一名今日头条高级作者。

请严格输出JSON。

格式：

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

1. 总字数接近用户要求。
2. 分成5个正文部分。
3. 每部分内容丰富。
4. image_keyword必须是具体画面。

例如：

不要：
年轻人压力

要：
年轻人在出租屋晚上查看工资余额


文章需要：
开头吸引读者，
中间有故事和分析，
结尾引导评论。
"""
                },


                {
                    "role":"user",
                    "content":
                    f"""
标题：

{selected_title}


目标字数：

{word_count}
"""
                }

            ])



            st.session_state.article = json.loads(result)




# 显示文章

if st.session_state.article:


    article = st.session_state.article


    st.header(article["title"])


    image_count = 0


    for section in article["sections"]:


        st.write(section["text"])


        if image_count < 3:


            img = search_image(
                section["image_keyword"]
            )


            if img:

                st.image(
                    img,
                    caption=section["image_keyword"]
                )


                image_count += 1
