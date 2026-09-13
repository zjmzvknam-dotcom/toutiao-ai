import streamlit as st
import requests
import json
from openai import OpenAI


# ==========================
# 页面设置
# ==========================

st.set_page_config(
    page_title="今日头条AI创作工具",
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

st.title("📝 今日头条AI创作工具")

st.write(
    "AI爆款标题 + 原创长文章 + AI智能配图"
)



# ==========================
# 输入区域
# ==========================

topic = st.text_input(
    "请输入文章主题",
    placeholder="例如：为什么越来越多人选择租房"
)


word_count = st.number_input(
    "目标字数",
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

        temperature=0.85

    )


    return response.choices[0].message.content



# ==========================
# 状态保存
# ==========================

if "titles" not in st.session_state:

    st.session_state.titles = []


if "article" not in st.session_state:

    st.session_state.article = None
    # ==========================
# 生成爆款标题
# ==========================

if st.button("🔥 生成爆款标题"):

    if not topic:

        st.warning("请输入文章主题")

    else:

        with st.spinner("正在生成爆款标题..."):

            title_result = deepseek([

                {
                    "role": "system",

                    "content": """
你是一名今日头条爆款标题专家。

根据用户提供的主题，
生成5个高点击标题。

要求：

1. 有吸引力。
2. 有悬念。
3. 符合今日头条用户阅读习惯。
4. 不使用夸张违规词。
5. 不制造虚假信息。

每个标题单独一行输出。

不要添加序号。
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



# ==========================
# 显示标题选择
# ==========================

if st.session_state.titles:


    st.subheader("请选择文章标题")


    selected_title = st.radio(

        "标题",

        st.session_state.titles

    )


    st.session_state.selected_title = selected_title
    # ==========================
# 生成原创文章
# ==========================


if "selected_title" in st.session_state:


    if st.button("✍️ 开始生成原创文章"):


        with st.spinner("AI正在创作文章..."):


            article_result = deepseek([


                {

                    "role": "system",

                    "content": """

你是一名资深今日头条原创作者。


请根据标题创作一篇原创文章。


重要要求：

1. 必须重新构建观点和逻辑。

2. 不允许简单改写网络文章。

3. 避免AI常见表达。


禁止出现：

近年来

随着时代发展

众所周知

不可否认

在这个快速发展的时代


4. 使用真实生活场景。

5. 增加人物、事件、细节。

6. 像真人作者写作。

7. 不要出现AI提示词。

8. 不要使用Markdown符号。


输出必须是JSON格式：


{

"title":"",

"sections":[

{

"text":"",

"image_prompt":""

}

]

}



文章要求：


1. 总字数接近用户目标。

2. 分成3个部分。

3. 每部分内容完整。

4. 三个部分观点不能重复。


图片要求：

每部分生成一张图片描述。


image_prompt必须包含：


人物：
年龄、身份


地点：
具体环境


动作：
正在做什么


时间：
白天或者晚上


风格：
真实摄影、新闻纪实


禁止：

动漫

游戏角色

古代人物

幻想人物

插画风格



错误：

年轻人压力


正确：

28岁男性程序员晚上坐在出租屋电脑前查看工资账单，桌面有咖啡和文件，真实摄影风格。


"""

                },


                {


                    "role": "user",


                    "content": f"""

文章标题：

{st.session_state.selected_title}



目标字数：

{word_count}

"""

                }

            ])



            try:


                # 防止DeepSeek返回markdown代码框

                clean_result = article_result.strip()


                if clean_result.startswith("```"):


                    clean_result = clean_result.replace(
                        "```json",
                        ""
                    )

                    clean_result = clean_result.replace(
                        "```",
                        ""
                    )


                st.session_state.article = json.loads(
                    clean_result
                )


            except Exception as e:


                st.error(
                    "文章解析失败，请重新生成"
                )

                st.write(e)
                # ==========================
# Cloudflare AI图片生成
# ==========================


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



        final_prompt = f"""

{prompt}


要求：

真实摄影照片。

新闻纪实摄影风格。

现代中国真实生活环境。

人物自然。

高清照片。


禁止：

文字。

水印。

logo。

动漫。

漫画。

游戏角色。

幻想场景。

古代人物。

"""


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
            "图片错误："
            + str(e)
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



    for section in article["sections"]:


        st.write(
            section["text"]
        )


        # 限制最多3张图片

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
