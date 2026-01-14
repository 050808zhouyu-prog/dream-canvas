import streamlit as st
import google.generativeai as genai
import requests
import random
import base64
from io import BytesIO
from urllib.parse import quote
from PIL import Image

# --- 页面配置 ---
st.set_page_config(
    page_title="DreamCanvas 魔法画板",
    page_icon="🍌",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- 样式优化 ---
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        border-radius: 24px;
        background: linear-gradient(90deg, #6366f1, #8b5cf6);
        color: white; 
        font-weight: bold;
        border: none;
        padding: 0.6rem;
        transition: transform 0.1s;
    }
    .stButton>button:active {
        transform: scale(0.98);
    }
    .stStatus { border-radius: 20px !important; }
</style>
""", unsafe_allow_html=True)

# --- 自动加载 Key (优先从 Secrets 读取) ---
GEMINI_KEY = st.secrets.get("GOOGLE_API_KEY", "")
SILICON_KEY = st.secrets.get("SILICON_KEY", "")

# --- 核心函数 1: Google Gemini (大脑 - 推荐) ---
def analyze_with_gemini(image_bytes, prompt):
    try:
        genai.configure(api_key=GEMINI_KEY)
        # 指定最新稳定版模型
        model = genai.GenerativeModel('gemini-1.5-flash')
        image = Image.open(BytesIO(image_bytes))
        response = model.generate_content([prompt, image])
        return response.text
    except Exception as e:
        # 如果 Flash 失败，尝试 Pro
        try:
            model = genai.GenerativeModel('gemini-1.5-pro')
            response = model.generate_content([prompt, image])
            return response.text
        except:
            return None # 彻底失败

# --- 核心函数 2: SiliconFlow (备用大脑) ---
def analyze_with_silicon(image_bytes, prompt):
    try:
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        url = "https://api.siliconflow.cn/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {SILICON_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "Qwen/Qwen2-VL-72B-Instruct",
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
            "temperature": 0.1
        }
        response = requests.post(url, headers=headers, json=payload, timeout=40)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        return None
    except:
        return None

# --- 主界面 ---
st.title("🍌 Nano Banana")
st.caption("把涂鸦变成皮克斯电影！")

# 如果没有配置 Secrets，显示输入框
if not GEMINI_KEY and not SILICON_KEY:
    with st.expander("🔑 设置 API Key (建议在后台 Secrets 配置)"):
        input_key = st.text_input("输入 Gemini 或 SiliconFlow Key", type="password")
        if input_key.startswith("AIza"): GEMINI_KEY = input_key
        elif input_key.startswith("sk-"): SILICON_KEY = input_key

uploaded_file = st.file_uploader("上传画作", type=["jpg", "png", "jpeg"], label_visibility="collapsed")

if uploaded_file:
    # 预览图
    st.image(uploaded_file, caption="原始涂鸦", use_container_width=True)
    
    # 选项
    col1, col2 = st.columns(2)
    with col1:
        style = st.selectbox("画风", ["3D 皮克斯动画", "宫崎骏二次元", "乐高积木", "毛毡玩具"])
    with col2:
        mode = st.selectbox("模式", ["✨ 单图重绘", "🖼️ 四格漫画"])

    if st.button("开始施展魔法 🪄", type="primary"):
        if not GEMINI_KEY and not SILICON_KEY:
            st.error("请先配置 API Key！")
            st.stop()

        # 定义外部变量，防止缩进问题
        final_image_url = None
        prompt_text = None

        with st.status("🧙‍♂️ 正在施法...", expanded=True) as status:
            
            # --- 1. 刑侦级提示词 (Identity Lock) ---
            # 这里的 Prompt 专门为了防止“指鹿为马”
            
            style_desc = ""
            if style == "3D 皮克斯动画":
                style_desc = "3D Disney Pixar style render, C4D, octane render, cute, glossy texture, soft studio lighting, vivid colors, 8k"
            elif style == "宫崎骏二次元":
                style_desc = "Studio Ghibli anime style, Hayao Miyazaki, vibrant colors, detailed background, hand-drawn feel"
            elif style == "乐高积木":
                style_desc = "lego bricks style, 3d render, plastic texture, toy world, macro photography, tilt-shift"
            elif style == "毛毡玩具":
                style_desc = "felt texture, needle felting style, fuzzy, soft, craft, stop motion animation style"

            if mode == "✨ 单图重绘":
                system_prompt = f"""
                ACT AS A FORENSIC ART EXPERT. Look at the sketch extremely carefully.
                
                MANDATORY IDENTIFICATION STEPS:
                1. What exactly is the MAIN CHARACTER? (Is it a Rabbit? A Dog? A Monster?). If it has long ears, it's likely a Rabbit.
                2. What color is it? (White? Blue?).
                3. What is it doing? (Driving a car? Flying?).
                4. What objects are present? (A yellow car? A chick?).
                
                OUTPUT TASK:
                Write a highly detailed image generation prompt in English to re-imagine this scene in {style_desc}.
                
                CRITICAL RULES:
                - You MUST explicitly state the species (e.g., "A cute white rabbit with long ears").
                - You MUST describe the action exactly (e.g., "Driving a small yellow toy car").
                - Maintain the original composition and colors.
                - Output ONLY the prompt text.
                """
            else:
                system_prompt = "Analyze this sketch. Write a prompt for a '4-panel comic strip' featuring THIS SPECIFIC character. Describe a funny short sequence suitable for kids. Request 'thick black outlines, comic book style, speech bubbles with simple English text'. Ensure the character looks consistent in all panels. Output ONLY the English prompt text."

            # --- 2. 调用大脑 (优先 Gemini) ---
            image_bytes = uploaded_file.getvalue()
            
            if GEMINI_KEY:
                status.write("🧠 Google Gemini 正在识别画面...")
                prompt_text = analyze_with_gemini(image_bytes, system_prompt)
            
            # 如果 Gemini 挂了或者没配，用 SiliconFlow 补位
            if not prompt_text and SILICON_KEY:
                status.write("🧠 切换到 SiliconFlow 识别画面...")
                prompt_text = analyze_with_silicon(image_bytes, system_prompt)
            
            if not prompt_text:
                status.update(label="识别失败，请检查 Key", state="error")
                st.stop()

            # --- 3. 调用画手 (Flux) ---
            status.write(f"🎨 正在绘制 ({style})...")
            
            seed = random.randint(0, 100000)
            encoded_prompt = quote(prompt_text)
            
            # 增加 enhance=true 参数，让 Flux 自动优化细节
            # 增加 nologo=true 去水印
            final_image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&model=flux&nologo=true&seed={seed}&enhance=true"
            
            status.update(label="✨ 魔法完成！", state="complete", expanded=False)

        # --- 4. 结果展示 (移出 status 缩进) ---
        if final_image_url:
            st.image(final_image_url, caption=f"AI 重绘结果", use_container_width=True)
            
            # 调试信息 (展开看 prompt，确认 AI 到底识别出了什么)
            with st.expander("👀 看看 AI 识别到了什么？"):
                st.write(prompt_text)

            # 下载
            try:
                img_data = requests.get(final_image_url).content
                st.download_button("📥 保存图片", data=img_data, file_name="magic_art.png", mime="image/png")
            except:
                pass
