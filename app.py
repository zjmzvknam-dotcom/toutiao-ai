import streamlit as st
import requests
from openai import OpenAI
import json
import base64


# ==========================
# 页面设置
# ==========================

st.set_page_config(
    page_title="今日头条AI创作工具",
    page_icon="📝"
)


# ==========================
# 读取密钥
# ==========================

DEEPSEEK_API_KEY = st.secrets["DEEPSEEK_API_KEY"]

CLOUDFLARE_API_TOKEN = st.secrets["CLOUDFLARE_API_TOKEN"]

CLOUDFLARE_ACCOUNT_ID = st.secrets["CLOUDFLARE_ACCOUNT_ID"]



# ==========================
# 标题
# ==========================

st.title(
    "📝 今日头条AI创作工具"
)


st.caption(
    "AI标题 + 原创文章 + AI配图"
)



# ==========================
# 输入
# ==========================

topic = st.text_input(
    "请输入文章主题"
)



word_count = st.number_input(
    "文章目标字数",
    min_value=800,
    max_value=5000,
    value=1500
)



# ==========================
# DeepSeek函数
# ==========================

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



# ==========================
# 状态
# ==========================


if "titles" not in st.session_state:

    st.session_state.titles = []



if "article" not in st.session_state:

    st.session_state.article = ""



if "selected_title" not in st.session_state:

    st.session_state.selected_title = ""



# ==========================
# 生成标题
# ==========================


if st.button("🔥生成爆款标题"):


    if topic == "":


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

                    "content":"""

你是今日头条爆款标题专家。

根据主题生成5个标题。

要求：

1. 有点击欲望。

2. 有悬念。

3. 不夸张违规。

4. 符合中文用户阅读习惯。

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


    st.session_state.selected_title = st.radio(

        "标题列表",

        st.session_state.titles
        # ==========================
# 生成文章
# ==========================


if st.session_state.selected_title:


    if st.button("✍️开始生成文章"):


        with st.spinner(
            "AI正在创作文章..."
        ):


            article = deepseek([


                {

                    "role":"system",

                    "content":"""

你是一名资深今日头条原创作者。


请根据标题写一篇原创文章。


写作要求：


1. 像真人作者写作。


2. 不要出现AI模板语言。


禁止：

近年来

随着时代发展

众所周知

不可否认

在这个快速发展的时代


3. 不允许简单替换网络文章。


4. 必须重新组织观点。


5. 加入真实生活场景。


6. 加入人物故事。


7. 有自己的分析。


8. 适合手机阅读。


9. 分段清晰。


10. 不使用Markdown符号。


文章结构：


第一部分：

开头吸引读者。


第二部分：

分析事情原因。


第三部分：

加入真实案例。


第四部分：

深入观点。


第五部分：

总结并引导评论。


字数要求：

接近用户目标字数。

允许上下浮动20%。


不要为了凑字数重复废话。



"""

                },


                {

                    "role":"user",

                    "content":f"""

标题：

{st.session_state.selected_title}


目标字数：

{word_count}


"""

                }


            ])



            st.session_state.article = article
            # ==========================
# Cloudflare AI图片生成
# ==========================


def generate_ai_image(prompt):


    try:


        final_prompt = f"""


Create a realistic documentary photograph.


Scene:

{prompt}



Style requirements:


Real camera photo.

Real human beings.

Modern daily life.

News documentary photography.

Natural lighting.

High quality.

Professional photography.



Strict negative requirements:


No anime.

No cartoon.

No illustration.

No painting.

No fantasy.

No game characters.

No ancient people.

No ancient costume.

No fictional characters.

No text.

No watermark.

No logo.



"""


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
                "图片生成失败"
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
        # ==========================
# 显示文章和图片
# ==========================


if st.session_state.article:


    st.divider()


    st.header(
        st.session_state.selected_title
    )


    st.divider()



    st.write(
        st.session_state.article
    )



    st.divider()



    st.subheader(
        "AI智能配图"
    )



    # 提取图片数量

    image_prompts = [

        "现代中国年轻人在办公室工作的真实摄影照片",

        "普通家庭生活场景的新闻纪实摄影照片",

        "年轻人在城市街道生活的真实摄影照片"

    ]



    image_count = 0



    for prompt in image_prompts:



        if image_count >= 3:

            break



        with st.spinner(

            f"正在生成第{image_count+1}张图片..."

        ):


            image = generate_ai_image(

                prompt

            )



        if image:


            st.image(

                image,

                use_container_width=True

            )


            image_count += 1



        st.divider()



# ==========================
# 页面底部
# ==========================


st.caption(
    "AI创作助手 | DeepSeek + Cloudflare FLUX"
)

    )
