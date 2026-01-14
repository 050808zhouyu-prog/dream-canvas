import streamlit as st
import requests
import random
import base64
from io import BytesIO
from urllib.parse import quote

# --- 页面配置 ---
st.set_page_config(
    page_title="DreamCanvas 魔法画板",
    page_icon="🎨",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- 样式美化 ---
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        border-radius: 20px;
        background-color: #4F46E5;
        color: white; 
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #4338CA;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# --- 侧边栏：API Key 设置 ---
with st.sidebar:
    st.header("🔑 魔法钥匙")
    # 优先从 Secrets 读取，如果没有则显示输入框
    if "SILICON_KEY" in st.secrets:
        api_key = st.secrets["SILICON_KEY"]
        st.success("✅ 已自动加载 API Key")
    else:
        api_key = st.text_input("请输入 SiliconFlow API Key", type="password")
        st.caption("去 cloud.siliconflow.cn 申请 Key")

# --- 核心函数：视觉分析 (Qwen-VL) ---
def analyze_image(image_bytes, prompt, key):
    # 转 Base64
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    url = "https://api.siliconflow.cn/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "Qwen/Qwen2-VL-72B-Instruct", # 使用通义千问视觉大模型
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }
        ],
        "max_tokens": 1024,
        "temperature": 0.1 # 低随机性，保证还原度
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            st.error(f"API 报错: {response.text}")
            return None
    except Exception as e:
        st.error(f"网络请求失败: {e}")
        return None

# --- 主界面 ---
st.title("🎨 Nano Banana 魔法画板")
st.caption("让孩子的涂鸦变成皮克斯大片！(Powered by SiliconFlow & Flux)")

uploaded_file = st.file_uploader("上传一张涂鸦", type=["jpg", "png", "jpeg"])

if uploaded_file:
    # 展示原图
    st.image(uploaded_file, caption="原始涂鸦", use_container_width=True)
    
    # 魔法设置
    col1, col2 = st.columns(2)
    with col1:
        mode = st.selectbox("选择模式", ["✨ 细节增强 (单图)", "🖼️ 四格漫画 (故事)"])
    with col2:
        style = st.selectbox("选择画风", ["3D 皮克斯动画", "宫崎骏二次元", "梦幻水彩", "乐高积木风"])

    # 按钮
    if st.button("✨ 开始施展魔法", type="primary"):
        if not api_key:
            st.warning("请先在左侧填入 SiliconFlow API Key 才能使用哦！")
            st.stop()

        with st.status("🧙‍♂️ 魔法师正在吟唱咒语...", expanded=True) as status:
            
            # 1. 构建提示词 (V6.0 身份锁定逻辑)
            status.write("👁️ 正在观察画作细节...")
            
            style_prompt = ""
            if style == "3D 皮克斯动画":
                style_prompt = "high-quality 3D Disney Pixar style render, C4D, octane render, cute, glossy texture, studio lighting"
            elif style == "宫崎骏二次元":
                style_prompt = "beautiful Studio Ghibli anime style, vibrant colors, detailed background, hand-drawn feel"
            elif style == "梦幻水彩":
                style_prompt = "soft watercolor painting, artistic, pastel colors, dreamy, wet-on-wet technique"
            elif style == "乐高积木风":
                style_prompt = "lego bricks style, 3d render, plastic texture, toy world"

            if mode == "✨ 细节增强 (单图)":
                system_prompt = f"""
                Analyze the attached child's sketch carefully.
                Step 1: Identify the main subject (Animal species? Human?). Be VERY specific.
                Step 2: Identify actions and objects.
                Step 3: Identify colors.
                Step 4: Write a detailed image generation prompt in English to re-imagine this EXACT scene in {style_prompt}.
                IMPORTANT: The prompt must explicitly state the animal species/character and action to prevent hallucination.
                Output ONLY the English prompt text.
                """
            else: # 四格漫画
                system_prompt = "Analyze this sketch. Write a prompt for a '4-panel comic strip' featuring THIS SPECIFIC character. Describe a funny short sequence suitable for kids. Request 'thick black outlines, comic book style, speech bubbles with simple English text'. Ensure the character looks consistent in all panels. Output ONLY the English prompt text."

            # 2. 调用视觉模型
            image_bytes = uploaded_file.getvalue()
            image_prompt = analyze_image(image_bytes, system_prompt, api_key)
            
            if image_prompt:
                status.write("🎨 正在绘制高清大图 (Flux)...")
                # print(f"Prompt: {image_prompt}") # 调试用

                # 3. 调用 Pollinations (Flux)
                seed = random.randint(0, 10000)
                encoded_prompt = quote(image_prompt)
                image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&model=flux&nologo=true&seed={seed}"
                
                status.update(label="魔法完成！", state="complete", expanded=False)
                
                # 4. 显示结果
                st.subheader("🎉 魔法完成！")
                st.image(image_url, caption=f"AI 魔法重绘 ({style})", use_container_width=True)
                
                # 下载按钮
                st.download_button(
                    label="📥 下载图片",
                    data=requests.get(image_url).content,
                    file_name="magic_art.png",
                    mime="image/png"
                )
