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
        padding: 0.5rem;
    }
    .stButton>button:hover {
        background-color: #4338CA;
        color: white;
        border-color: #4338CA;
    }
    .stSpinner > div {
        border-top-color: #4F46E5 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 侧边栏：配置 ---
with st.sidebar:
    st.header("🧠 大脑设置")
    
    # 选择模型提供商
    provider = st.radio("选择视觉模型 (大脑)", ["Google Gemini (推荐)", "SiliconFlow (备用)"])
    
    st.divider()
    
    gemini_key = ""
    silicon_key = ""

    # 根据选择显示对应的 Key 输入框
    if provider == "Google Gemini (推荐)":
        if "GOOGLE_API_KEY" in st.secrets:
            gemini_key = st.secrets["GOOGLE_API_KEY"]
            st.success("✅ Gemini Key 已加载")
        else:
            gemini_key = st.text_input("输入 Google Gemini Key", type="password")
            st.caption("免费申请: aistudio.google.com")
            
    else:
        if "SILICON_KEY" in st.secrets:
            silicon_key = st.secrets["SILICON_KEY"]
            st.success("✅ SiliconFlow Key 已加载")
        else:
            silicon_key = st.text_input("输入 SiliconFlow Key", type="password")

# --- 核心函数 1: Google Gemini (你的最爱) ---
def analyze_with_gemini(image_bytes, prompt, api_key):
    try:
        genai.configure(api_key=api_key)
        # Gemini 1.5 Flash 是目前的性价比之王，看图极准
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 转换图片格式
        image = Image.open(BytesIO(image_bytes))
        
        response = model.generate_content([prompt, image])
        return response.text
    except Exception as e:
        st.error(f"Google Gemini 报错: {e}")
        return None

# --- 核心函数 2: SiliconFlow (备用) ---
def analyze_with_silicon(image_bytes, prompt, api_key):
    try:
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        url = "https://api.siliconflow.cn/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
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
        else:
            st.error(f"SiliconFlow 报错: {response.text}")
            return None
    except Exception as e:
        st.error(f"网络请求失败: {e}")
        return None

# --- 主界面 ---
st.title("🍌 Nano Banana 魔法画板")
st.caption("上传孩子的涂鸦，让 AI 施展魔法！")

uploaded_file = st.file_uploader("点击上传图片", type=["jpg", "png", "jpeg"])

if uploaded_file:
    # 布局：左边原图，右边结果
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.image(uploaded_file, caption="原始涂鸦", use_container_width=True)
        
        st.write("---")
        st.subheader("🎨 魔法配方")
        mode = st.radio("模式", ["✨ 细节增强 (单图)", "🖼️ 四格漫画 (故事)"], horizontal=True)
        style = st.selectbox("画风", ["3D 皮克斯动画", "宫崎骏二次元", "梦幻水彩", "乐高积木风", "写实油画"])
        
        start_btn = st.button("开始施展魔法 🪄", type="primary")

    if start_btn:
        active_key = gemini_key if "Google" in provider else silicon_key
        if not active_key:
            st.error(f"请先在左侧填入 {provider} 的 API Key！")
            st.stop()

        with col2:
            status_container = st.status("🧙‍♂️ 魔法师正在观察画作...", expanded=True)
            
            # --- 1. 构建提示词 (Prompt Engineering) ---
            # 这里使用了 V6.0 的“身份锁定”逻辑，防止兔子变狐狸
            
            style_prompt = ""
            if style == "3D 皮克斯动画":
                style_prompt = "high-quality 3D Disney Pixar style render, C4D, octane render, cute, glossy texture, studio lighting, vivid colors"
            elif style == "宫崎骏二次元":
                style_prompt = "beautiful Studio Ghibli anime style, vibrant colors, detailed background, hand-drawn feel, Hayao Miyazaki style"
            elif style == "梦幻水彩":
                style_prompt = "soft watercolor painting, artistic, pastel colors, dreamy, wet-on-wet technique, illustration"
            elif style == "乐高积木风":
                style_prompt = "lego bricks style, 3d render, plastic texture, toy world, macro photography"
            elif style == "写实油画":
                style_prompt = "classic oil painting, heavy brush strokes, artistic, detailed texture, van gogh style"

            base_instruction = ""
            if mode == "✨ 细节增强 (单图)":
                base_instruction = f"""
                You are an expert art director. Analyze the attached child's sketch carefully.
                Step 1: Identify the main subject (Animal species? Human?). Be VERY specific. If it looks like a rabbit, say 'White Rabbit'. If it's a car, say 'Yellow Car'.
                Step 2: Identify actions and objects.
                Step 3: Identify colors of the subject and objects strictly based on the sketch.
                Step 4: Write a detailed image generation prompt in English to re-imagine this EXACT scene in {style_prompt}.
                IMPORTANT: The prompt must explicitly state the animal species/character and action to prevent hallucination. Do not add objects that are not there.
                Output ONLY the English prompt text.
                """
            else: # 四格漫画
                base_instruction = "Analyze this sketch. Write a prompt for a '4-panel comic strip' featuring THIS SPECIFIC character. Describe a funny short sequence suitable for kids. Request 'thick black outlines, comic book style, speech bubbles with simple English text'. Ensure the character looks consistent in all panels. Output ONLY the English prompt text."

            # --- 2. 调用大脑 (Vision API) ---
            image_bytes = uploaded_file.getvalue()
            
            if "Google" in provider:
                status.write("🧠 Gemini 正在思考...")
                image_prompt = analyze_with_gemini(image_bytes, base_instruction, active_key)
            else:
                status.write("🧠 SiliconFlow 正在思考...")
                image_prompt = analyze_with_silicon(image_bytes, base_instruction, active_key)
            
            if not image_prompt:
                status.update(label="识别失败", state="error")
                st.stop()
                
            # print(image_prompt) # 调试用

            # --- 3. 调用画手 (Pollinations/Flux) ---
            status.write("🎨 正在绘制高清大图 (Flux)...")
            
            seed = random.randint(0, 10000)
            # URL Encode
            encoded_prompt = quote(image_prompt)
            # Pollinations API URL
            image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&model=flux&nologo=true&seed={seed}"
            
            # --- 4. 显示结果 ---
            status.update(label="魔法完成！", state="complete", expanded=False)
            
            st.image(image_url, caption=f"AI 重绘作品 ({style})", use_container_width=True)
            
            # 下载按钮
            try:
                img_data = requests.get(image_url).content
                st.download_button(
                    label="📥 保存高清大图",
                    data=img_data,
                    file_name="magic_canvas.png",
                    mime="image/png"
                )
            except:
                st.warning("图片下载准备失败，请右键另存为。")

            # 额外福利：如果是漫画模式且用了 Gemini，讲个故事
            if mode == "🖼️ 四格漫画 (故事)" and "Google" in provider:
                with st.expander("📖 听 Gemini 讲故事"):
                    story_prompt = f"Based on this image description: '{image_prompt}', write a very short, warm bedtime story for kids in Simplified Chinese. Use Emojis."
                    try:
                        genai.configure(api_key=active_key)
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        story = model.generate_content(story_prompt).text
                        st.write(story)
                    except:
                        pass
