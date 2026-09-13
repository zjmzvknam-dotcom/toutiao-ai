import streamlit as st
import requests
import json
from openai import OpenAI


st.set_page_config(
    page_title="今日头条AI创作工具",
    page_icon="📝"
)


DEEPSEEK_API_KEY = st.secrets["DEEPSEEK_API_KEY"]

CLOUDFLARE_API_TOKEN = st.secrets["CLOUDFLARE_API_TOKEN"]

CLOUDFLARE_ACCOUNT_ID = st.secrets["CLOUDFLARE_ACCOUNT_ID"]



st.title("📝 今日头条AI创作工具")

st.write(
    "AI标题 + 原创文章 + AI配图"
)



topic = st.text_input(
    "文章主题",
    placeholder="例如：为什么越来越多人选择租房"
)



word_count = st.number_input(
    "目标字数",
    min_value=500,
    max_value=5000,
    value=1500,
    step=100
)



def deepseek(messages):

    client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com"
    )


    response = client.chat.completions.create(

        model="deepseek-chat",

        messages=messages,

        temperature=0.8

    )


    return response.choices[0].message.content




if "titles" not in st.session_state:

    st.session_state.titles = []



if "article" not in st.session_state:

    st.session_state.article = None




if st.button("🔥 生成爆款标题"):


    if not topic:

        st.warning(
            "请输入文章主题"
        )


    else:


        with st.spinner(
            "正在生成标题..."
        ):


            result = deepseek([

                {
                    "role":"system",
                    "content":
                    """
你是今日头条爆款标题专家。

根据主题生成5个标题。

要求：

高点击率。
有悬念。
有冲突。
不违规。

每行输出一个标题。
"""
                },

                {
                    "role":"user",
                    "content":topic
                }

            ])



            st.session_state.titles = [

                x.strip()

                for x in result.split("\n")

                if x.strip()

            ]




if st.session_state.titles:


    st.subheader(
        "请选择标题"
    )


    selected_title = st.radio(

        "标题",

        st.session_state.titles

    )



    if st.button(
        "✍️ 生成文章"
    ):


        with st.spinner(
            "正在写文章..."
        ):


            result = deepseek([

                {
                    "role":"system",
                    "content":
                    """
你是一名今日头条原创作者。

写一篇原创文章。

要求：

不要复制网络文章。

不要使用：
近年来
随着时代发展
众所周知
不可否认

这些AI高频句。

加入真实生活场景。

文章像真人写作。


输出JSON：

{
"title":"",
"sections":[
{
"text":"",
"image_prompt":""
}
]
}


要求：

5个部分。

文章字数控制在目标字数上下20%。

每个部分生成图片描述。


图片描述必须：

真实摄影。

现代生活。

人物。

地点。

动作。

时间。


禁止：

动漫。

游戏人物。

古代人物。

幻想场景。

插画。


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



            try:

    clean_result = result.strip()

    if clean_result.startswith("```"):
        clean_result = clean_result.replace("```json", "")
        clean_result = clean_result.replace("```", "")

    st.session_state.article = json.loads(clean_result)


except Exception as e:

    st.error("文章解析失败")

    st.write(result)

    st.write(e)
                )
                # =========================
# AI图片生成
# =========================


def generate_ai_image(prompt):

    try:


        url = (

            "https://api.cloudflare.com/client/v4/accounts/"

            + CLOUDFLARE_ACCOUNT_ID

            + "/ai/run/@cf/black-forest-labs/flux-1-schnell"

        )


        headers = {

            "Authorization":

            "Bearer " + CLOUDFLARE_API_TOKEN,


            "Content-Type":

            "application/json"

        }



        final_prompt = (

            prompt

            + """

Realistic photography.

News documentary style.

Modern Chinese real life.

Natural people.

No text.

No watermark.

No logo.

No anime.

No cartoon.

No game character.

No fantasy.

"""

        )



        response = requests.post(

            url,

            headers=headers,

            json={

                "prompt": final_prompt

            },

            timeout=120

        )



        if response.status_code != 200:


            st.warning(
                "图片接口失败"
            )


            st.write(
                response.text
            )


            return None



        data = response.json()



        if data.get("result"):


            image = data["result"].get(
                "image"
            )


            if image:


                return (

                    "data:image/png;base64,"

                    + image

                )



        return None



    except Exception as e:


        st.warning(

            "图片错误："

            + str(e)

        )


        return None





# =========================
# 显示文章
# =========================


if st.session_state.article:


    article = st.session_state.article



    st.divider()



    st.header(
        article["title"]
    )



    st.divider()



    image_count = 0



    for section in article["sections"]:



        st.write(
            section["text"]
        )



        if image_count < 3:



            with st.spinner(
                "正在生成AI图片..."
            ):


                image = generate_ai_image(

                    section["image_prompt"]

                )



            if image:


                st.image(
                    image,
                    caption="AI生成配图"
                )


                image_count += 1



        st.divider()
