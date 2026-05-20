import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import io
import json
import time
import requests
import base64

# Sahifa sozlamalari
st.set_page_config(page_title="AI PDF Modifier Pro", layout="wide")

# Chap menyu - OpenRouter API kalit kiritish joyi
with st.sidebar:
    st.subheader("🔑 OpenRouter AI Tizimi")
    st.info("Bu yerga openrouter.ai saytidan olingan bepul kalitni kiriting. Bu modelda limitlar juda katta!")
    raw_keys = st.text_input("OpenRouter API Kalit(lar)ni kiriting:", type="password", help="Kalit1, Kalit2 formatida yozing")
    api_keys = [k.strip() for k in raw_keys.split(",")] if raw_keys else []

st.title("AI Yordamida Bilet Ma'lumotlarini Avtomat Almashtirish Pro (Llama-3 Version) 🚀")

def encode_image_to_base64(pil_image):
    """Rasm faylini AI tushunadigan base64 formatiga o'tkazish"""
    buffered = io.BytesIO()
    pil_image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def pasport_va_biletni_tahlil_qilish(passport_image, bilet_matni, keys_list):
    """OpenRouter orqali Llama-3-Vision modeliga ulanish funksiyasi"""
    base64_image = encode_image_to_base64(passport_image)
    
    prompt = f"""
    Siz aqlli hujjatchisiz. Bilet matni ichidan yo'lovchining ESKI ismi, ESKI pasport raqami va ESKI tug'ilgan sanasini aniqlang.
    Pasport rasmidan YANGI yo'lovchining ismi, pasport raqami va tug'ilgan sanasini o'qing.
    
    Bilet matni:
    "{bilet_matni}"
    
    Natijani faqat mana shu JSON formatida qaytaring, boshqa hech qanday matn, izoh yoki kirish so'zi qo'shmang. To'g'ridan-to'g'ri JSON formatida ochiluvchi qavsdan boshlang:
    {{
        "eski_ism": "ESKI ISM",
        "yangi_ism": "YANGI ISM",
        "eski_pasport": "ESKI PASPORT",
        "yangi_pasport": "YANGI PASPORT",
        "eski_sana": "ESKI SANA",
        "yangi_sana": "YANGI SANA"
    }}
    """
    
    for index, key in enumerate(keys_list):
        try:
            # OpenRouter API manzili va sozlamalari (Llama-3 Vision modeli ishlatiladi)
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json"
                },
                data=json.dumps({
                    "model": "meta-llama/llama-3.2-11b-vision-instruct:free", # Mutlaqo bepul kuchli AI modeli
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}"
                                    }
                                }
                            ]
                        }
                    ]
                }),
                timeout=45
            )
            
            res_json = response.json()
            ai_text = res_json['choices'][0]['message']['content'].strip()
            
            # JSON formatni tozalash
            if "```json" in ai_text:
                ai_text = ai_text.split("```json")[1].split("```")[0].strip()
            elif "```" in ai_text:
                ai_text = ai_text.split("```")[1].split("```")[0].strip()
                
            return json.loads(ai_text)
        except Exception as e:
            st.sidebar.warning(f"Kalit-{index+1}da xatolik yuz berdi, keyingisiga o'tilmoqda...")
            continue
            
    st.error("❌ Kiritilgan OpenRouter kalitlar ishlamadi yoki server javob bermadi!")
    return None

def tahrirlash_bilet(pdf_bytes, data):
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page in doc:
            # 1. Ism
            if data.get("eski_ism") and data.get("yangi_ism"):
                for inst in page.search_for(data["eski_ism"]):
                    page.add_redact_annot(inst)
                    page.apply_redactions()
                    page.insert_text(inst.tl, data["yangi_ism"], fontsize=10, color=(0, 0, 0))

            # 2. Pasport
            if data.get("eski_pasport") and data.get("yangi_pasport"):
                for inst in page.search_for(data["eski_pasport"]):
                    page.add_redact_annot(inst)
                    page.apply_redactions()
                    page.insert_text(inst.tl, data["yangi_pasport"], fontsize=10, color=(0, 0, 0))

            # 3. Sana
            if data.get("eski_sana") and data.get("yangi_sana"):
                for inst in page.search_for(data["eski_sana"]):
                    page.add_redact_annot(inst)
                    page.apply_redactions()
                    page.insert_text(inst.tl, data["yangi_sana"], fontsize=10, color=(0, 0, 0))

        out_pdf = io.BytesIO()
        doc.save(out_pdf)
        doc.close()
        return out_pdf.getvalue()
    except Exception as e:
        st.error(f"PDF tahrirlashda xatolik yuz berdi: {str(e)}")
        return None

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Hujjatlarni Yuklang")
    uploaded_pdf = st.file_uploader("Asl PDF biletni yuklang", type=['pdf'])
    st.write("---")
    uploaded_passports = st.file_uploader(
        "Yangi yo'lovchilar pasport rasmlarini yuklang (Bir nechta yuklash mumkin ➕)", 
        type=["png", "jpg", "jpeg"], 
        accept_multiple_files=True
    )

with col2:
    st.subheader("2. AI Avtomatizatsiya Jarayoni")
    if api_keys:
        if st.button("AI orqali Avtomatik Almashtirish 🚀"):
            if uploaded_pdf and uploaded_passports:
                pdf_bytes = uploaded_pdf.read()
                
                doc_temp = fitz.open(stream=pdf_bytes, filetype="pdf")
                bilet_matni = doc_temp[0].get_text()
                doc_temp.close()
                
                st.write(f"📊 Jami yuklangan pasportlar: {len(uploaded_passports)} ta")
                st.session_state.tayyor_biletlar = {}
                
                for index, passport_file in enumerate(uploaded_passports):
                    st.markdown(f"### 👤 Yo'lovchi {index+1}: {passport_file.name}")
                    with st.spinner("Llama-3 AI tahlil qilmoqda..."):
                        passport_image = Image.open(passport_file)
                        ai_natija = pasport_va_biletni_tahlil_qilish(passport_image, bilet_matni, api_keys)
                        
                    if ai_natija:
                        st.success(f"✅ AI topdi: {ai_natija.get('yangi_ism', '')}")
                        final_pdf = tahrirlash_bilet(pdf_bytes, ai_natija)
                        
                        if final_pdf:
                            st.session_state.tayyor_biletlar[f"bilet_{index}"] = {
                                "name": f"bilet_{passport_file.name}.pdf",
                                "data": final_pdf
                            }
                    # Server ketma-ket yuklanishdan charchamasligi uchun 2 soniya kutish
                    time.sleep(2)
                st.balloons()
            else:
                st.error("Iltimos, oldin bilet PDF faylini va pasport rasmlarini yuklang!")
    else:
        st.warning("Dasturni ishlatish uchun chap menyuga OpenRouter API kalit kiriting.")

# Sahifa yangilanganda yuklash tugmalari o'chib ketmasligi uchun xotiradan chiqarish
if 'tayyor_biletlar' in st.session_state and st.session_state.tayyor_biletlar:
    st.write("---")
    st.subheader("📥 Tayyorlangan biletlar ro'yxati:")
    for key, bilet in st.session_state.tayyor_biletlar.items():
        st.download_button(
            label=f"💾 {bilet['name']} faylini yuklab olish",
            data=bilet['data'],
            file_name=bilet['name'],
            key=f"download_{key}"
        )

st.write("---")
st.markdown("<h4 style='text-align: center; color: gray;'>👨‍💻 Dasturchi: Muxammadamin</h4>", unsafe_allow_html=True)
