import streamlit as st
import requests
from openai import OpenAI


st.set_page_config(
    page_title="今日头条AI创作工具",
    page_icon="📝"
)


# ======================
# Secrets
# ======================

DEEPSEEK_API_KEY = st.secrets["DEEPSEEK_API_KEY"]

CLOUDFLARE_API_TOKEN = st.secrets["CLOUDFLARE_API_TOKEN"]

CLOUDFLARE_ACCOUNT_ID = st.secrets["CLOUDFLARE_ACCOUNT_ID"]



# ======================
# 页面
# ======================

st.title("📝 今日头条AI创作工具")

st.write(
    "AI标题 + 原创文章 + AI真人配图"
)



topic = st.text_input(
    "请输入文章主题"
)



word_count = st.number_input(
    "目标字数",
    min_value=500,
    max_value=5000,
    value=1500
)



# ======================
# DeepSeek
# ======================

def deepseek(prompt):

    client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com"
    )


    response = client.chat.completions.create(

        model="deepseek-chat",

        messages=[

            {
                "role":"user",
                "content":prompt
            }

        ],

        temperature=0.8

    )


    return response.choices[0].message.content



# ======================
# 状态
# ======================

if "titles" not in st.session_state:

    st.session_state.titles = []


if "article" not in st.session_state:

    st.session_state.article = ""



if "selected_title" not in st.session_state:

    st.session_state.selected_title = ""



# ======================
# 生成标题
# ======================

if st.button("🔥生成爆款标题"):


    if topic:


        with st.spinner("正在生成标题..."):


            result = deepseek(f"""

你是一名今日头条爆款标题专家。

根据下面主题生成5个标题：

主题：
{topic}


要求：

1. 有吸引力
2. 有悬念
3. 不违规
4. 符合中文用户习惯


每行一个标题。

""")


            st.session_state.titles = [

                x.strip()

                for x in result.split("\n")

                if x.strip()

            ]


    else:

        st.warning(
            "请输入主题"
        )



if st.session_state.titles:


    st.subheader(
        "选择标题"
    )


    st.session_state.selected_title = st.radio(

        "标题",

        st.session_state.titles# ======================
# 生成原创文章
# ======================


if st.session_state.selected_title:


    if st.button("✍️生成原创文章"):


        with st.spinner("AI正在创作文章..."):


            article_prompt = f"""

你是一名今日头条资深原创作者。


请根据标题写一篇原创文章。


标题：

{st.session_state.selected_title}



目标字数：

{word_count}



要求：

1. 内容必须重新组织逻辑。

2. 不允许简单改写网络文章。

3. 不要有明显AI腔。


禁止使用：

近年来

随着时代发展

众所周知

不可否认

在这个快速发展的时代


4. 加入真实生活场景。

5. 加入人物故事。

6. 有自己的观点分析。

7. 适合手机阅读。

8. 分段清晰。


文章结构：


第一部分：

吸引读者的开头。


第二部分：

分析原因。


第三部分：

真实案例。


第四部分：

深入观点。


第五部分：

总结并引导评论。


不要使用：

#

**

>

等Markdown符号。


直接输出文章正文。


"""


            st.session_state.article = deepseek(
                article_prompt
            )



# ======================
# 图片生成
# ======================


def generate_ai_image(prompt):


    try:


        final_prompt = f"""

Create a realistic documentary photograph.


{prompt}



Requirements:

Real human photography.

Modern China daily life.

Real camera photo.

News documentary style.

Natural lighting.

High quality.



Negative:

Anime.

Cartoon.

Illustration.

Painting.

Fantasy.

Game character.

Ancient costume.

Ancient people.

Text.

Watermark.

Logo.


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
            f"图片错误：{e}"
        )


        return None# ======================
# 显示文章
# ======================


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



    image_prompts = [


        "一名25岁中国年轻白领晚上在出租屋电脑前工作，桌面有电脑和咖啡，真实摄影，新闻纪实风格",



        "一名30岁中国普通家庭成员在客厅整理生活账单，现代家庭环境，白天自然光，真实摄影",



        "一名年轻人在城市街道独自思考未来，现代都市背景，真实相机拍摄，新闻摄影风格"


    ]



    count = 0



    for prompt in image_prompts:



        if count >= 3:


            break



        with st.spinner(

            f"正在生成第{count+1}张图片..."

        ):



            image = generate_ai_image(

                prompt

            )



        if image:


            st.image(

                image,

                use_container_width=True

            )


            count += 1



        st.divider()



st.caption(
    "今日头条AI创作工具 | DeepSeek + Cloudflare FLUX"
)

    )
