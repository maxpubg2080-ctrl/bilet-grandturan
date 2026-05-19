import streamlit as st
import google.generativeai as genai
import fitz  # PyMuPDF
import io
import re
import json
from PIL import Image

# Sahifa sozlamalari
st.set_page_config(page_title="AI PDF Modifier", layout="wide")
st.title("AI Yordamida Bilet Ma'lumotlarini Avtomat Almashtirish 🤖")

# API Kalitni avtomatik sozlash (Yoki yon menyudan kiritish)
with st.sidebar:
    st.subheader("Sozlamalar")
    api_key = st.text_input("Google Gemini API Kalitini kiriting:", type="password")
    if api_key:
        genai.configure(api_key=api_key)

def pasport_va_biletni_tahlil_qilish(passport_image, bilet_matni):
    """AI bilet ichidagi eski ma'lumotlarni va pasportdagi yangi ma'lumotlarni o'zi topadi."""
    
    prompt = f"""
    Siz aqlli hujjatchisiz. Sizga bilet ichidagi matn va yangi yo'lovchining pasport rasmi berilgan.
    
    Vazifangiz:
    1. Bilet matni ichidan yo'lovchining ESKI ismi (F.I.O), ESKI pasport raqami va ESKI tug'ilgan sanasini aniqlang.
    2. Pasport rasmidan YANGI yo'lovchining ismi, pasport raqami va tug'ilgan sanasini o'qing.
    
    Bilet matni:
    \"\"\"{bilet_matni}\"\"\"
    
    Natijani faqat va faqat mana shu JSON formatida qaytaring, boshqa hech narsa yozmang:
    {{
      "eski_ism": "BILETDGI ESKI ISM",
      "eski_pasport": "BILETDAGI ESKI PASPORT",
      "eski_sana": "BILETDAGI ESKI SANA",
      "yangi_ism": "PASPORTDAGI YANGI ISM",
      "yangi_pasport": "PASPORTDAGI YANGI PASPORT",
      "yangi_sana": "PASPORTDAGI YANGI SANA (Format: DD.MM.YYYY)"
    }}
    """
    
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        # Limitga urilmaslik uchun rasmni siqamiz (kichraytiramiz)
        passport_image.thumbnail((800, 800))
        
        response = model.generate_content([prompt, passport_image])
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        return None
    except Exception as e:
        st.error(f"AI tahlilida xatolik: {e}")
        return None

def tahrirlash_bilet(pdf_data, data):
    """AI topgan eski matnlarni bilet ichidan qidirib topadi va chiziqlarni buzmasdan o'chirib, yangisini yozadi."""
    doc = fitz.open(stream=pdf_data, filetype="pdf")
    page = doc[0]
    
    # AI topgan eski matnlarni bilet ichidan qidirish
    blok_ism = page.search_for(data["eski_ism"].strip())
    blok_pasport = page.search_for(data["eski_pasport"].strip())
    blok_sana = page.search_for(data["eski_sana"].strip())
    
    # 1. Ismni almashtirish
    if blok_ism:
        rect = blok_ism[0]
        safe_rect = fitz.Rect(rect.x0, rect.y0 + 1, rect.x1, rect.y1 - 1)
        page.draw_rect(safe_rect, color=(1, 1, 1), fill=(1, 1, 1))
        page.insert_text((rect.x0, rect.y1 - 2), data["yangi_ism"].upper(), fontname="helvetica", fontsize=8.5, color=(0, 0, 0))
        
    # 2. Pasportni almashtirish
    if blok_pasport:
        rect = blok_pasport[0]
        safe_rect = fitz.Rect(rect.x0, rect.y0 + 1, rect.x1, rect.y1 - 1)
        page.draw_rect(safe_rect, color=(1, 1, 1), fill=(1, 1, 1))
        page.insert_text((rect.x0, rect.y1 - 2), data["yangi_pasport"].upper(), fontname="helvetica", fontsize=8.5, color=(0, 0, 0))
        
    # 3. Sanani almashtirish
    if blok_sana:
        rect = blok_sana[0]
        safe_rect = fitz.Rect(rect.x0, rect.y0 + 1, rect.x1, rect.y1 - 1)
        page.draw_rect(safe_rect, color=(1, 1, 1), fill=(1, 1, 1))
        page.insert_text((rect.x0, rect.y1 - 2), data["yangi_sana"], fontname="helvetica", fontsize=8.5, color=(0, 0, 0))

    output = io.BytesIO()
    doc.save(output)
    doc.close()
    output.seek(0)
    return output

# UI qismi
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Hujjatlarni Yuklang")
    uploaded_pdf = st.file_uploader("Asl PDF biletni yuklang", type=["pdf"])
    uploaded_pass = st.file_uploader("Yangi yo'lovchi pasport rasmini yuklang", type=["png", "jpg", "jpeg"])

with col2:
    st.subheader("2. AI Avtomatizatsiya Jarayoni")
    st.info("Siz hech qanday ma'lumotni qo'lda yozmaysiz. AI bilet ichidagi eski ma'lumotlarni ham, pasportdagi yangi ma'lumotlarni ham o'zi solishtirib tahrirlaydi.")
    
    if api_key:
        if st.button("AI orqali Avtomatik Almashtirish 🚀"):
            if uploaded_pdf and uploaded_pass:
                with st.spinner("AI bilet matnini va pasport rasmini tahlil qilmoqda..."):
                    
                    # PDF ichidagi matnlarni AI o'qishi uchun ajratib olamiz
                    pdf_bytes = uploaded_pdf.read()
                    doc_temp = fitz.open(stream=pdf_bytes, filetype="pdf")
                    bilet_matni = doc_temp[0].get_text()
                    doc_temp.close()
                    
                    passport_image = Image.open(uploaded_pass)
                    
                    # AI funksiyasini chaqiramiz
                    ai_natija = pasport_va_biletni_tahlil_qilish(passport_image, bilet_matni)
                    
                if ai_natija:
                    st.write("🔍 **AI aniqlagan ma'lumotlar:**")
                    st.success(f"O'chirilayotgan eski ma'lumot: {ai_natija['eski_ism']} ({ai_natija['eski_pasport']})")
                    st.info(f"Yozilayotgan yangi ma'lumot: {ai_natija['yangi_ism']} ({ai_natija['yangi_pasport']})")
                    
                    # Biletni tahrirlash
                    final_pdf = tahrirlash_bilet(pdf_bytes, ai_natija)
                    
                    if final_pdf:
                        st.balloons()
                        st.success("Bilet ideal tarzda tayyorlandi!")
                        st.download_button(
                            label="Yangilangan PDF biletni yuklab olish ✨",
                            data=final_pdf,
                            file_name="ai_yangilangan_bilet.pdf",
                            mime="application/pdf"
                        )
                else:
                    st.error("AI hujjatlarni tahlil qila olmadi. API kalitni yoki rasmni tekshiring.")
            else:
                st.warning("Iltimos, PDF bilet va pasport rasmini yuklang.")
    else:
        st.warning("Dasturni ishlatish uchun chap menyudan yangi Google Gemini API kalitini kiriting.")
        st.write(muxammadamin)
st.caption("Dasturchi: muxammadamin 😎")
