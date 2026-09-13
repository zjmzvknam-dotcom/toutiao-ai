import streamlit as st
import requests
import json
from openai import OpenAI


# ==========================
# 页面设置
# ==========================

st.set_page_config(
    page_title="我的头条AI创作工具",
    page_icon="📝"
)


# ==========================
# Secrets
# ==========================

DEEPSEEK_API_KEY = st.secrets["DEEPSEEK_API_KEY"]

CLOUDFLARE_API_TOKEN = st.secrets["CLOUDFLARE_API_TOKEN"]

CLOUDFLARE_ACCOUNT_ID = st.secrets["CLOUDFLARE_ACCOUNT_ID"]



# ==========================
# 页面标题
# ==========================

st.title("📝 我的头条AI创作工具")

st.caption(
    "AI标题 + 原创文章 + AI真人摄影配图"
)



# ==========================
# 输入
# ==========================

topic = st.text_input(
    "输入文章主题"
)



word_count = st.number_input(
    "目标字数",
    min_value=500,
    max_value=5000,
    value=1500
)



# ==========================
# DeepSeek
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
# 状态保存
# ==========================


if "titles" not in st.session_state:

    st.session_state.titles = []



if "selected_title" not in st.session_state:

    st.session_state.selected_title = None



if "article" not in st.session_state:

    st.session_state.article = None



# ==========================
# 生成标题
# ==========================


if st.button("🔥 生成爆款标题"):


    if not topic:


        st.warning(
            "请输入主题"
        )


    else:


        with st.spinner(
            "正在生成标题..."
        ):


            result = deepseek([


                {

                    "role":"system",

                    "content":"""

你是一名今日头条爆款标题专家。

根据主题生成5个高点击标题。

要求：

有悬念。

有讨论价值。

不能夸大。

不能违规。

符合中文用户阅读习惯。

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

                for x in result.split("\n")

                if x.strip()

            ]



# ==========================
# 选择标题
# ==========================


if st.session_state.titles:


    st.subheader(
        "请选择文章标题"
    )


    st.session_state.selected_title = st.radio(

        "标题",

        st.session_state.titles
        # ==========================
# 生成文章
# ==========================


if st.session_state.selected_title:


    if st.button("✍️ 开始生成文章"):


        with st.spinner(
            "AI正在创作文章..."
        ):


            result = deepseek([


                {


                    "role":"system",


                    "content":"""

你是一名今日头条资深原创作者。


请根据标题写一篇原创文章。


严格要求：


1. 不使用网络常见AI模板。


禁止：

近年来

随着时代发展

众所周知

不可否认

在这个快速发展的时代


2. 文章必须像真人作者写作。


3. 加入真实生活场景。


4. 加入具体人物故事。


5. 有独立观点。


6. 不要简单替换同义词。


7. 不要出现AI腔。


8. 不要使用Markdown符号。


9. 不要使用：

#

**

>

代码

图片说明


10. 适合今日头条手机阅读。


11. 段落不要太长。



请严格输出JSON。


格式：


{

"title":"文章标题",

"sections":[

{

"text":"正文内容",

"image_prompt":"图片描述"

}

]

}



文章要求：


1. 分为5个部分。


第一部分：

吸引人的开头。


第二部分：

分析原因。


第三部分：

真实故事案例。


第四部分：

深入观点。


第五部分：

总结，引导评论。



2. 总字数：

按照用户要求。


3. 每部分生成一个图片描述。


图片描述要求：


必须是现代真人摄影。


包含：

人物年龄。

人物身份。

地点。

动作。

时间。


例如：

30岁男性程序员晚上在出租屋电脑前查看工资记录，桌面有电脑和账单，真实摄影，新闻纪实风格。



禁止：

动漫。

漫画。

游戏人物。

古代人物。

神话。

幻想。

插画。


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




            try:


                clean_result = result.strip()



                if clean_result.startswith("```"):


                    clean_result = clean_result.replace(
                        "```json",
                        ""
                    ).replace(
                        "```",
                        ""
                    ).strip()



                st.session_state.article = json.loads(
                    clean_result
                )



            except Exception as e:


                st.error(
                    "文章解析失败，请重新生成"
                )


                st.write(
                    result
                )
                # ==========================
# Cloudflare AI 图片生成
# ==========================


def generate_ai_image(prompt):


    try:


        # 图片提示词强化

        final_prompt = f"""


Generate a realistic documentary photograph.


{prompt}



STRICT REQUIREMENTS:


Real human photography.


Real people.


Modern China daily life.


Real camera photo.


News documentary style.


Natural lighting.


People must look like real people.


High quality photo.



NOT ALLOWED:


Anime.


Cartoon.


Illustration.


Fantasy.


Game character.


Ancient costume.


Ancient people.


Mythology.


Fictional character.


Painting style.


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

            f"Bearer {CLOUDFLARE_API_TOKEN}",


            "Content-Type":

            "application/json"

        }



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
                "图片接口调用失败"
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
        # ==========================
# 显示文章
# ==========================


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



        st.write(
            section["text"]
        )



        # 最多生成3张图片

        if image_count < 3:



            with st.spinner(
                f"正在生成第{image_count + 1}张图片..."
            ):



                image = generate_ai_image(

                    section["image_prompt"]

                )



            if image:


                st.image(

                    image,

                    use_container_width=True

                )


                image_count += 1



        st.divider()



# ==========================
# 页脚
# ==========================


st.caption(
    "AI辅助创作工具 | DeepSeek + Cloudflare AI"
)

    )
