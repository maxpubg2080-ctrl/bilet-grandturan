import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import io
import json
import time
import requests
import base64

# Sahifa sozlamalari
st.set_page_config(page_title="AI PDF Modifier Groq Pro", layout="wide")

# Chap menyu - Groq API kalit kiritish joyi
with st.sidebar:
    st.subheader("🔑 Groq AI Tizimi")
    st.info("Bu yerga console.groq.com saytidan olingan bepul kalitni kiriting. Bu tizim o'ta tezkor va barqaror!")
    raw_keys = st.text_input("Groq API Kalit(lar)ni kiriting:", type="password", help="gsk_... formatida yozing")
    api_keys = [k.strip() for k in raw_keys.split(",")] if raw_keys else []

st.title("AI Yordamida Bilet Ma'lumotlarini Avtomat Almashtirish Pro (Groq Speed) 🚀")

def encode_image_to_base64(pil_image):
    """Rasm faylini AI tushunadigan base64 formatiga o'tkazish"""
    buffered = io.BytesIO()
    # Groq o'lchami o'ta katta rasmlarda qiynalmasligi uchun hajmini biroz kichiklashtiramiz
    pil_image.thumbnail((1024, 1024))
    pil_image.save(buffered, format="JPEG", quality=85)
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def pasport_va_biletni_tahlil_qilish(passport_image, bilet_matni, keys_list):
    """Groq API orqali Llama-3.1-Vision modeliga ulanish"""
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
    
    for key in keys_list:
        try:
            response = requests.post(
                url="https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json"
                },
                data=json.dumps({
                    "model": "llama-3.2-11b-vision-preview",  # Groq platformasidagi eng kuchli vizual model
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
                    ],
                    "response_format": {"type": "json_object"}  # Groq-dan aniq JSON formatda javob olish xususiyati
                }),
                timeout=25
            )
            
            res_json = response.json()
            ai_text = res_json['choices'][0]['message']['content'].strip()
            return json.loads(ai_text)
        except Exception:
            continue
            
    return None

def tahrirlash_bilet(pdf_bytes, data):
    """PDF-ni xatosiz va chiroyli tahrirlash (oq kvadrat bilan yopish usuli)"""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page in doc:
            tahrir_royxati = [
                (data.get("eski_ism"), data.get("yangi_ism")),
                (data.get("eski_pasport"), data.get("yangi_pasport")),
                (data.get("eski_sana"), data.get("yangi_sana"))
            ]
            
            for eski, yangi in tahrir_royxati:
                if eski and yangi:
                    text_instances = page.search_for(eski)
                    for inst in text_instances:
                        # Eski matnni oq to'rtburchak bilan o'chirish
                        page.draw_rect(inst, color=(1, 1, 1), fill=(1, 1, 1))
                        # Yangi matnni joylashtirish
                        page.insert_text(inst.tl, yangi, fontsize=9, color=(0, 0, 0))

        out_pdf = io.BytesIO()
        doc.save(out_pdf)
        doc.close()
        return out_pdf.getvalue()
    except Exception as e:
        st.error(f"PDF tahrirlashda xatolik: {str(e)}")
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
                    with st.spinner("Groq AI yashindagi tezlikda tahlil qilmoqda..."):
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
                    else:
                        st.error("❌ Groq AI ma'lumotni o'qiy olmadi yoki kalitda xatolik bor.")
                    time.sleep(0.5)
                st.balloons()
            else:
                st.error("Iltimos, oldin bilet PDF faylini va pasport rasmlarini yuklang!")
    else:
        st.warning("Dasturni ishlatish uchun chap menyuga Groq API kalitini kiriting.")

# Yuklash tugmalari chiqishi uchun
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
