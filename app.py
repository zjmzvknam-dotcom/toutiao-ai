import streamlit as st
import requests
import json
from openai import OpenAI


# 页面设置
st.set_page_config(
    page_title="今日头条AI创作工具",
    page_icon="📝"
)


# 读取密钥
DEEPSEEK_API_KEY = st.secrets["DEEPSEEK_API_KEY"]

CLOUDFLARE_API_TOKEN = st.secrets["CLOUDFLARE_API_TOKEN"]

CLOUDFLARE_ACCOUNT_ID = st.secrets["CLOUDFLARE_ACCOUNT_ID"]


# 标题
st.title("📝 今日头条AI创作工具")

st.write(
    "AI爆款标题 + 原创文章 + 智能配图"
)


# 输入主题

topic = st.text_input(
    "请输入文章主题",
    placeholder="例如：为什么越来越多人选择租房"
)


# 字数

word_count = st.number_input(
    "目标文章字数",
    min_value=500,
    max_value=5000,
    value=1500,
    step=100
)



# DeepSeek函数

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



# 保存状态

if "titles" not in st.session_state:

    st.session_state.titles = []


if "article" not in st.session_state:
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
            "正在生成标题..."
        ):


            title_result = deepseek([

                {
                    "role": "system",
                    "content": """
你是今日头条爆款标题专家。

根据用户主题生成5个标题。

要求：

1. 高点击率
2. 有悬念
3. 有冲突感
4. 不夸大
5. 符合中文用户阅读习惯

每行输出一个标题。
不要加编号。
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
# 选择标题生成文章
# =========================


if st.session_state.titles:


    st.subheader(
        "请选择文章标题"
    )


    selected_title = st.radio(

        "标题",

        st.session_state.titles

    )



    if st.button(
        "✍️ 开始生成文章"
    ):


        with st.spinner(
            "AI正在创作文章..."
        ):


            article_result = deepseek([


                {
                    "role": "system",
                    "content": """
你是一名今日头条原创作者。


请根据标题写一篇原创文章。


写作要求：


1. 不复制网络文章。

2. 不使用AI常见模板。

3. 避免使用：

近年来

随着时代发展

众所周知

不可否认

这类高频句。


4. 重新组织观点。

5. 加入真实生活场景。

6. 增加人物故事。

7. 文章像真人写作。


字数要求：

用户设置多少字，
文章控制在上下20%范围。


例如：

1500字：

1200-1800字均可。


不要为了凑字数重复。


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



必须输出JSON格式：


{
"title":"",
"sections":[
{
"text":"",
"image_prompt":""
}
]
}


图片描述要求：


必须包含：

人物

年龄

身份

地点

动作

时间

摄影风格


禁止：

动漫

游戏人物

古代人物

幻想人物

插画

文字水印


正确：

25岁中国程序员，
晚上在出租屋修改简历，
桌上有电脑和咖啡，
窗外城市灯光，
真实新闻摄影风格。


错误：

年轻人压力。


"""
                },


                {
                    "role": "user",

                    "content": f"""
标题：

{selected_title}


目标字数：

{word_count}

"""
                }


            ])



            try:

                st.session_state.article = json.loads(
                    article_result
                )


            except Exception:

                st.error(
                    "文章解析失败，请重新生成"
                )
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

            "Bearer " + CLOUDFLARE_API_TOKEN,


            "Content-Type":

            "application/json"

        }



        # 二次优化图片提示词

        final_prompt = (

            prompt

            + """



Realistic photography.

News documentary photo style.

Modern real life scene.

Natural people.

No text.

No watermark.

No logo.

No anime.

No cartoon.

No game character.

No ancient costume.

No fantasy.



"""

        )



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


            image_data = result["result"].get(
                "image"
            )


            if image_data:


                return (

                    "data:image/png;base64,"

                    + image_data

                )



        return None



    except Exception as e:


        st.warning(

            "图片生成错误："

            + str(e)

        )


        return None# =========================
# 显示文章和图片
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



        # 显示正文

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

                    caption="AI智能配图"

                )


                image_count += 1



        st.divider()

    st.session_state.article = None
