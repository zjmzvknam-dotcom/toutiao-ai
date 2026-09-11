import streamlit as st
import requests
import json
import base64
from openai import OpenAI


st.set_page_config(
    page_title="我的头条创作工具",
    page_icon="📝"
)


st.title("📝 我的头条创作工具")

st.write("AI爆款标题 + 长文章生成 + AI智能配图")


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



# =========================
# DeepSeek文章生成
# =========================

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




# =========================
# Cloudflare FLUX 图片生成
# =========================

def generate_ai_image(prompt):

    try:

        url = (
            "https://api.cloudflare.com/client/v4/accounts/"
            + CLOUDFLARE_ACCOUNT_ID
            + "/ai/run/"
            + "@cf/black-forest-labs/flux-1-kontext-pro"
        )


        headers = {
            "Authorization": 
            f"Bearer {CLOUDFLARE_API_TOKEN}",
            "Content-Type": "application/json"
        }


        json_data = {
            "prompt": prompt
        }


        response = requests.post(
            url,
            headers=headers,
            json=json_data,
            timeout=60
        )


        if response.status_code != 200:
            return None


        result = response.json()


        if result.get("result"):

            image_data = result["result"].get("image")


            if image_data:

                return (
                    "data:image/jpeg;base64,"
                    + image_data
                )


        return None


    except Exception as e:

        st.write(e)

        return None



        result = response.json()
        st.write(result)



        if result.get("result"):

            image_data = result["result"].get("image")


            if image_data:

                return (
                    "data:image/jpeg;base64,"
                    + image_data
                )



        return None



    except Exception:

        return None



# =========================
# 状态保存
# =========================


if "titles" not in st.session_state:

    st.session_state.titles = []



if "article" not in st.session_state:

    st.session_state.article = None
# =========================
# 生成爆款标题
# =========================

if st.button("🔥 生成爆款标题"):


    if topic:


        with st.spinner("正在生成标题..."):


            text = deepseek([

                {
                    "role":"system",
                    "content":
                    """
你是今日头条爆款标题专家。

根据主题生成5个高点击标题。

要求：
1. 有吸引力
2. 有悬念
3. 不违规
4. 符合今日头条用户习惯

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

                for x in text.split("\n")

                if x.strip()

            ]


    else:

        st.warning("请输入文章主题")





# =========================
# 选择标题并生成文章
# =========================


if st.session_state.titles:


    st.subheader("请选择文章标题")


    selected_title = st.radio(

        "标题",

        st.session_state.titles

    )



    if st.button("✍️ 开始生成文章"):


        with st.spinner("AI正在创作长文章..."):


            result = deepseek([


                {
                    "role":"system",

                    "content":
                    """
你是一名今日头条高级作者。

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

1. 总字数接近用户要求。
2. 分成5个正文部分。
3. 每部分内容丰富。
4. image_prompt必须是详细图片描述。


图片描述要求：

不要写：
年轻人压力


必须写：

年轻人在出租屋晚上查看手机银行余额，
桌面有账单和电脑，
现实摄影风格。


文章结构：

第一部分：
吸引读者的开头。

第二部分：
分析原因。

第三部分：
真实案例。

第四部分：
深入分析。

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

                st.error("文章格式解析失败，请重新生成")





# =========================
# 显示文章和AI图片
# =========================


if st.session_state.article:


    article = st.session_state.article



    st.header(article["title"])



    for section in article["sections"]:



        st.write(section["text"])



        image = generate_ai_image(

            section["image_prompt"]

        )



        if image:


            st.image(

                image,

                caption=section["image_prompt"]

            )
