import streamlit as st
import google.generativeai as genai
import fitz  # PyMuPDF
from PIL import Image
import io
import json
import time
import re

# Sahifa sozlamalari
st.set_page_config(page_title="AI PDF Modifier Pro", layout="wide")

# Chap menyu - Bir nechta API kalit kiritish joyi
with st.sidebar:
    st.sidebar.subheader("🔑 AI Kalitlar Tizimi")
    st.sidebar.info("Limitdan qochish uchun bir nechta kalit kiritsangiz bo'ladi (vergul bilan ajrating)")
    raw_keys = st.sidebar.text_input("Gemini API Kalit(lar)ni kiriting:", type="password", help="Kalit1, Kalit2 formatida yozing")

    # Kalitlarni ro'yxatga olish
    api_keys = [k.strip() for k in raw_keys.split(",")] if raw_keys else []

st.title("AI Yordamida Bilet Ma'lumotlarini Avtomat Almashtirish Pro 🚀")

def pasport_va_biletni_tahlil_qilish(passport_image, bilet_matni, keys_list):
    """Zaxira kalitlar bilan ishlovchi aqlli AI funksiyasi."""
    prompt = f"""
    Siz aqlli hujjatchisiz. Bilet matni ichidan yo'lovchining ESKI ismi, ESKI pasport raqami va ESKI tug'ilgan sanasini aniqlang.
    Pasport rasmidan YANGI yo'lovchining ismi, pasport raqami va tug'ilgan sanasini o'qing.
    
    Bilet matni:
    \"{bilet_matni}\"
    
    Natijani faqat mana shu JSON formatida qaytaring, boshqa matn qo'shmang:
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
            genai.configure(api_key=key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content([prompt, passport_image])
            
            # JSON formatni tozalab olish
            cleaned_text = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(cleaned_text)
        except Exception as e:
            st.sidebar.warning(f"Kalit-{index+1}da cheklov yoki xatolik: o'tilmoqda...")
            continue
            
    st.error("❌ Barcha kiritilgan API kalitlarda limit tugadi!")
    return None

def tahrirlash_bilet(pdf_bytes, data):
    """PDF-ni xatosiz va yangi formatda tahrirlash funksiyasi."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page in doc:
            # 1. Ismni o'zgartirish
            if data.get("eski_ism") and data.get("yangi_ism"):
                for inst in page.search_for(data["eski_ism"]):
                    page.add_redact_annot(inst)
                    page.apply_redactions()
                    page.insert_text(inst.tl, data["yangi_ism"], fontsize=10, color=(0, 0, 0))

            # 2. Pasportni o'zgartirish
            if data.get("eski_pasport") and data.get("yangi_pasport"):
                for inst in page.search_for(data["eski_pasport"]):
                    page.add_redact_annot(inst)
                    page.apply_redactions()
                    page.insert_text(inst.tl, data["yangi_pasport"], fontsize=10, color=(0, 0, 0))

            # 3. Sanani o'zgartirish
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
        st.error(f"PDF tahrirlashda xatolik: {str(e)}")
        return None

# Interfeys qismi
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
                
                # Bilet matnini vaqtincha o'qib olish
                doc_temp = fitz.open(stream=pdf_bytes, filetype="pdf")
                bilet_matni = doc_temp[0].get_text()
                doc_temp.close()
                
                st.write(f"📊 Jami yuklangan pasportlar: {len(uploaded_passports)} ta")
                
                # Xotirani tozalab yangidan yaratish
                st.session_state.tayyor_biletlar = {}
                
                for index, passport_file in enumerate(uploaded_passports):
                    st.markdown(f"### 👤 Yo'lovchi {index+1}: {passport_file.name}")
                    
                    with st.spinner("AI tahlil qilmoqda..."):
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
                st.balloons()
            else:
                st.error("Iltimos, oldin bilet PDF faylini va pasport rasmlarini yuklang!")
    else:
        st.warning("Dasturni ishlatish uchun chap menyuga API kalit kiriting.")

# Sahifa yangilanganda yuklash tugmalari yo'qolib ketmasligi uchun sikldan tashqarida chiqariladi
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
st.caption("Dasturchi: Muxammadamin 😎")
