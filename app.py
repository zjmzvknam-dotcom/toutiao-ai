import streamlit as st
import requests
import json
from openai import OpenAI


# =========================
# 页面设置
# =========================

st.set_page_config(
    page_title="今日头条AI创作工具",
    page_icon="📝",
    layout="centered"
)


# =========================
# 读取密钥
# =========================

DEEPSEEK_API_KEY = st.secrets["DEEPSEEK_API_KEY"]

CLOUDFLARE_API_TOKEN = st.secrets["CLOUDFLARE_API_TOKEN"]

CLOUDFLARE_ACCOUNT_ID = st.secrets["CLOUDFLARE_ACCOUNT_ID"]



# =========================
# 标题
# =========================

st.title("📝 今日头条AI创作工具")

st.write(
    "AI爆款标题 + AI原创文章 + AI配图"
)



# =========================
# 输入区域
# =========================


topic = st.text_input(
    "请输入文章主题",
    placeholder="例如：为什么越来越多人选择租房而不是买房"
)



word_count = st.number_input(
    "目标文章字数",
    min_value=500,
    max_value=5000,
    value=1500,
    step=100
)



# =========================
# DeepSeek函数
# =========================


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



# =========================
# 保存状态
# =========================


if "titles" not in st.session_state:

    st.session_state.titles = []



if "article" not in st.session_state:

    st.session_state.article = None
    # =========================
# 生成爆款标题
# =========================


if st.button("🔥 生成爆款标题"):


    if not topic:

        st.warning(
            "请输入文章主题"
        )


    else:


        with st.spinner(
            "正在生成爆款标题..."
        ):


            title_result = deepseek([


                {

                    "role": "system",

                    "content": """

你是一名今日头条爆款标题专家。

根据用户提供的主题，
生成5个高点击标题。


要求：

1. 有吸引力
2. 有悬念
3. 不使用虚假夸张词
4. 符合今日头条用户阅读习惯
5. 不违反平台规则


每行输出一个标题。
不要添加编号。

"""

                },


                {

                    "role": "user",

                    "content": topic

                }


            ])



            st.session_state.titles = [

                x.strip()

                for x in title_result.split("\n")

                if x.strip()

            ]





# =========================
# 显示标题选择
# =========================


if st.session_state.titles:


    st.subheader(
        "请选择文章标题"
    )


    selected_title = st.radio(

        "标题列表",

        st.session_state.titles

    )



    if st.button(
        "✍️ 开始生成原创文章"
    ):


        with st.spinner(
            "AI正在创作文章..."
        ):



            article_result = deepseek([



                {


                    "role": "system",

                    "content": """

你是一名优秀的今日头条原创作者。


请根据标题创作一篇原创文章。


重要要求：


【原创要求】

1. 不复制网络文章结构。

2. 不使用常见AI模板。

3. 不出现：

近年来

随着时代发展

众所周知

不可否认

这类AI高频词。


4. 重新组织观点。

5. 加入真实生活场景。

6. 像真实作者表达观点。



【字数要求】

文章目标字数：

由用户提供。


允许误差：

上下20%。


例如：

目标1500字：

1200-1800字都可以。


不要为了凑字数重复内容。



【结构要求】

分成5个部分。


第一部分：

开头吸引读者。


第二部分：

分析事情原因。


第三部分：

加入真实人物案例。


第四部分：

深入分析观点。


第五部分：

总结并引导评论。



【输出格式】

必须严格输出JSON。


格式：
# =========================
# Cloudflare AI 图片生成
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

            f"Bearer {CLOUDFLARE_API_TOKEN}",


            "Content-Type":

            "application/json"

        }



        final_prompt = f"""

{prompt}


要求：

真实摄影照片。

新闻纪实摄影风格。

现代社会场景。

中国现实生活环境。

人物自然。

禁止：

文字。

水印。

logo。

动漫。

漫画。

游戏人物。

古代人物。

幻想场景。

"""



        data = {


            "prompt": final_prompt

        }



        response = requests.post(


            url,


            headers=headers,


            json=data,


            timeout=120


        )



        if response.status_code != 200:


            st.warning(
                "图片生成接口失败"
            )


            st.write(
                response.text
            )


            return None




        result = response.json()



        if result.get("result"):


            image = result["result"].get(
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

            f"图片生成错误：{e}"

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



    for index, section in enumerate(

        article["sections"]

    ):



        # 显示正文


        st.write(

            section["text"]

        )



        # 只生成3张图片

        if image_count < 3:



            with st.spinner(

                f"正在生成第{image_count+1}张图片..."

            ):



                image = generate_ai_image(

                    section["image_prompt"]

                )



            if image:


                st.image(

                    image,

                    caption="AI配图"

                )


                image_count += 1



        st.divider()
