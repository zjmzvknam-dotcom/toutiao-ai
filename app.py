import streamlit as st
import requests
import json
from openai import OpenAI


# ======================
# 页面设置
# ======================

st.set_page_config(
    page_title="我的头条AI创作工具",
    page_icon="📝"
)


# ======================
# 读取Secrets
# ======================

DEEPSEEK_API_KEY = st.secrets["DEEPSEEK_API_KEY"]

CLOUDFLARE_API_TOKEN = st.secrets["CLOUDFLARE_API_TOKEN"]

CLOUDFLARE_ACCOUNT_ID = st.secrets["CLOUDFLARE_ACCOUNT_ID"]


# ======================
# 标题
# ======================

st.title("📝 我的头条AI创作工具")

st.write(
    "AI标题 + 长文章 + AI配图"
)


# ======================
# 输入
# ======================

topic = st.text_input(
    "输入文章主题"
)


word_count = st.number_input(
    "目标字数",
    min_value=500,
    max_value=5000,
    value=1500
)
# ======================
# DeepSeek AI
# ======================

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



# ======================
# 保存状态
# ======================

if "titles" not in st.session_state:

    st.session_state.titles = []


if "article" not in st.session_state:

    st.session_state.article = None



# ======================
# 生成标题
# ======================

if st.button("🔥 生成爆款标题"):


    if topic:


        with st.spinner("正在生成标题..."):


            result = deepseek([

                {
                    "role":"system",

                    "content":
                    """
你是一名今日头条爆款标题专家。

根据用户主题生成5个标题。

要求：

1. 高点击率
2. 有悬念
3. 不夸大违规
4. 符合中文用户阅读习惯

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


    else:

        st.warning("请输入主题")



# ======================
# 选择标题生成文章
# ======================

if st.session_state.titles:


    st.subheader("请选择文章标题")


    selected_title = st.radio(

        "标题",

        st.session_state.titles

    )


    if st.button("✍️ 开始生成文章"):


        with st.spinner("AI正在写文章..."):


            result = deepseek([


                {

                    "role":"system",

                    "content":
                    """
你是一名今日头条高级作者。
写作要求：

1. 不允许使用网络常见模板句。

2. 不要出现：
“近年来”
“随着时代发展”
“众所周知”
“不可否认”

这类AI高频开头。

3. 文章必须重新组织逻辑，
不能简单替换同义词。

4. 加入真实生活场景。

5. 每篇文章必须有独立观点。

6. 像一个真实作者写作，
不要有AI腔。

请严格输出JSON格式。


格式：

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

1. 文章总字数控制在目标字数±20%。

例如：
目标1500字，
允许1200-1800字。


2. 不要为了凑字数重复废话。

3. 分成5个部分。

4. 每部分内容丰富。

5. 每部分生成一个详细图片描述。


图片描述必须具体。

错误：

年轻人压力


正确：

年轻人在深夜出租屋内查看手机银行余额，
桌上放着账单和电脑，
真实摄影风格。



文章结构：

第一部分：
吸引人的开头。


第二部分：
分析原因。


第三部分：
真实故事案例。


第四部分：
深入观点分析。


第五部分：
总结并引导评论。
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

                st.session_state.article = json.loads(result)


            except:

                st.error("文章解析失败，请重新生成")
                         # ======================
# Cloudflare AI 图片生成
# ======================

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


        data = {

            "prompt": prompt

        }


        response = requests.post(

            url,

            headers=headers,

            json=data,

            timeout=120

        )


        if response.status_code != 200:

            st.warning(
                "图片接口调用失败"
            )

            st.write(response.text)

            return None



        result = response.json()



        if result.get("result"):


            image = result["result"].get("image")


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
        # ======================
# 显示文章和图片
# ======================

if st.session_state.article:


    article = st.session_state.article


    st.divider()


    st.header(
        article["title"]
    )


    st.divider()



    for index, section in enumerate(article["sections"]):


        # 显示正文

        st.write(
            section["text"]
        )


        # 生成对应图片

        with st.spinner(
            f"正在生成第{index+1}张图片..."
        ):


            image = generate_ai_image(

                section["image_prompt"]

            )



        if image:


            st.image(

                image,

                caption=section["image_prompt"]

            )


        st.divider()
