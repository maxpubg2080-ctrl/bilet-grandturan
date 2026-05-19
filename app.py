import streamlit as st
import google.generativeai as genai
import fitz  # PyMuPDF
from PIL import Image
import io
import json
import time
import re

# Sahifa sozlamalari
st.set_page_config(page_title="AI PDF Modifier", layout="wide")

# Chap menyu (Sidebar) - API Kalit uchun
with st.sidebar:
    st.subheader("Sozlamalar")
    api_key = st.text_input("Google Gemini API Kalitini kiriting:", type="password")
    if api_key:
        genai.configure(api_key=api_key)

st.title("AI Yordamida Bilet Ma'lumotlarini Avtomat Almashtirish 😉")

# AI funksiyasi
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
        model = genai.GenerativeModel("gemini-2.5-flash")
        passport_image.thumbnail((800, 800))
        
        response = model.generate_content([prompt, passport_image])
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        return None
    except Exception as e:
        st.error(f"AI tahlilida xatolik: {str(e)}")
        return None

def tahrirlash_bilet(pdf_bytes, data):
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page in doc:
            if "eski_ism" in data and "yangi_ism" in data:
                text_instances = page.search_for(data["eski_ism"])
                for inst in text_instances:
                    page.add_redact_annot(inst, new_text=data["yangi_ism"])
            
            if "eski_pasport" in data and "yangi_pasport" in data:
                text_instances = page.search_for(data["eski_pasport"])
                for inst in text_instances:
                    page.add_redact_annot(inst, new_text=data["yangi_pasport"])
            
            if "eski_sana" in data and "yangi_sana" in data:
                text_instances = page.search_for(data["eski_sana"])
                for inst in text_instances:
                    page.add_redact_annot(inst, new_text=data["yangi_sana"])
                    
            page.apply_redactions()
        
        out_pdf = io.BytesIO()
        doc.save(out_pdf)
        doc.close()
        return out_pdf.getvalue()
    except Exception as e:
        st.error(f"PDF tahrirlashda xatolik: {str(e)}")
        return None

# UI qismi
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Hujjatlarni Yuklang")
    uploaded_pdf = st.file_uploader("Asl PDF biletni yuklang", type=["pdf"])
    
    st.write("---")
    st.markdown("**Yangi yo'lovchilar pasportlarini alohida yuklang (Maksimum 10 ta):**")
    
    # 10 ta alohida pasport yuklash maydoni
    uploaded_passports = []
    for i in range(1, 11):
        pass_file = st.file_uploader(f"👤 {i}-Yo'lovchi pasport rasmi", type=["png", "jpg", "jpeg"], key=f"pass_field_{i}")
        if pass_file:
            uploaded_passports.append(pass_file)

with col2:
    st.subheader("2. AI Avtomatizatsiya Jarayoni")
    st.info("AI bilet ichidagi eski ma'lumotlarni ham, pasportdagi yangi ma'lumotlarni ham o'zi solishtirib tahrirlaydi.")

    if api_key:
        if st.button("AI orqali Avtomatik Almashtirish 🚀"):
            if uploaded_pdf and uploaded_passports:
                pdf_bytes = uploaded_pdf.read()
                doc_temp = fitz.open(stream=pdf_bytes, filetype="pdf")
                bilet_matni = doc_temp[0].get_text()
                doc_temp.close()
                
                st.write(f"📋 Jami yuklangan pasportlar soni: {len(uploaded_passports)} ta")
                
                for index, passport_file in enumerate(uploaded_passports):
                    st.markdown(f"### 👤 {index+1}-Yo'lovchi: {passport_file.name}")
                    with st.spinner("AI bilet matnini va pasport rasmini tahlil qilmoqda..."):
                        passport_image = Image.open(passport_file)
                        
                        ai_natija = pasport_va_biletni_tahlil_qilish(passport_image, bilet_matni)
                        
                        if ai_natija:
                            st.success(f"AI aniqlagan ma'lumotlar: {ai_natija.get('yangi_ism', '')}")
                            final_pdf = tahrirlash_bilet(pdf_bytes, ai_natija)
                            
                            if final_pdf:
                                st.download_button(
                                    label=f"📥 {passport_file.name} uchun tayyor biletni yuklab olish 🚀",
                                    data=final_pdf,
                                    file_name=f"bilet_{passport_file.name}.pdf",
                                    mime="application/pdf",
                                    key=f"btn_dl_{index}"
                                )
                        
                        # Limitga tushmaslik uchun har safar 30 soniya kutamiz
                        if index < len(uploaded_passports) - 1:
                            st.info("Keyingi pasportga o'tish uchun 30 soniya kutilmoqda... ⏱️")
                            time.sleep(30)
                            
                st.balloons()
                st.success("🎉 Barcha yuklangan biletlar muvaffaqiyatli tayyorlandi!")
            else:
                st.warning("Iltimos, PDF bilet va kamida bitta pasport rasmini yuklang.")
    else:
        st.warning("Dasturdan foydalanish uchun chap menyudan yangi Google Gemini API kalitini kiriting.")

# Mualliflik
st.write("---")
st.caption("Dasturchi: Muxammadamin 😎")
