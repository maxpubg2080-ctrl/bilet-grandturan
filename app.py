import streamlit as st
import google.generativeai as genai
import fitz  # PyMuPDF
from PIL import Image
import io
import json
import time
import re

# O'zbekcha Streamlit interfeysi uchun maxsus moslashtirgich
st.set_page_config(page_title="AI PDF Modifier", layout="wide")

# O'zbekcha nomlar bilan ishlash
with st.sidebar:
    st.subheader("Sozlamalar")
    api_key = st.text_input("Google Gemini API Kalitini kiriting:", type="password")
    if api_key:
        genai.configure(api_key=api_key)

st.title("AI Yordamida Bilet Ma'lumotlarini Avtomat Almashtirish 😉")

def pasport_va_biletni_tahlil_qilish(passport_image, bilet_matni):
    prompt = f"""
    Siz aqlli hujjatchisiz. Bilet matni ichidan yo'lovchining ESKI ismi, ESKI pasport raqami va ESKI tug'ilgan sanasini aniqlang.
    Pasport rasmidan YANGI yo'lovchining ismi, pasport raqami va tug'ilgan sanasini o'qing.
    
    Bilet matni:
    \"\"\"{bilet_matni}\"\"\"
    
    Natijani faqat mana shu JSON formatida qaytaring:
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

# Sahifa tuzilishi
chap_ustun, ong_ustun = st.columns(2)

with chap_ustun:
    st.subheader("1. Hujjatlarni Yuklang")
    yuklangan_bilet = st.file_uploader("Asl PDF biletni yuklang", type=["pdf"], key="bilet_pdf_main")
    
    st.write("---")
    st.markdown("**Yangi yo'lovchilar pasportlarini alohida joylang (Maksimum 5 ta):**")
    
    # 5 ta alohida, bir-biriga xalaqit bermaydigan o'zbekcha yuklash tugmalari
    pasportlar_royxati = []
    
    p1 = st.file_uploader("👤 1-Yo'lovchi pasport rasmi", type=["png", "jpg", "jpeg"], key="p_tugma_1")
    if p1: pasportlar_royxati.append(p1)
        
    p2 = st.file_uploader("👤 2-Yo'lovchi pasport rasmi", type=["png", "jpg", "jpeg"], key="p_tugma_2")
    if p2: pasportlar_royxati.append(p2)
        
    p3 = st.file_uploader("👤 3-Yo'lovchi pasport rasmi", type=["png", "jpg", "jpeg"], key="p_tugma_3")
    if p3: pasportlar_royxati.append(p3)
        
    p4 = st.file_uploader("👤 4-Yo'lovchi pasport rasmi", type=["png", "jpg", "jpeg"], key="p_tugma_4")
    if p4: pasportlar_royxati.append(p4)
        
    p5 = st.file_uploader("👤 5-Yo'lovchi pasport rasmi", type=["png", "jpg", "jpeg"], key="p_tugma_5")
    if p5: pasportlar_royxati.append(p5)

with ong_ustun:
    st.subheader("2. AI Avtomatizatsiya Jarayoni")
    st.info("Har bir yuklangan pasport uchun alohida tayyor biletlar pastda yuklab olish uchun paydo bo'ladi.")

    if api_key:
        if st.button("AI orqali Avtomatik Almashtirish 🚀", key="start_ai_process"):
            if yuklangan_bilet and pasportlar_royxati:
                pdf_bytes = yuklangan_bilet.read()
                doc_temp = fitz.open(stream=pdf_bytes, filetype="pdf")
                bilet_matni = doc_temp[0].get_text()
                doc_temp.close()
                
                st.write(f"📋 Jami yuklangan pasportlar: {len(pasportlar_royxati)} ta")
                
                for indeks, pasport_fayl in enumerate(pasportlar_royxati):
                    st.markdown(f"### 👤 {indeks+1}-Yo'lovchi: {pasport_fayl.name}")
                    with st.spinner("AI tahlil qilmoqda..."):
                        pasport_tasvir = Image.open(pasport_fayl)
                        ai_natija = pasport_va_biletni_tahlil_qilish(pasport_tasvir, bilet_matni)
                        
                        if ai_natija:
                            st.success(f"Aniqlangan ism: {ai_natija.get('yangi_ism', '')}")
                            tayyor_bilet = tahrirlash_bilet(pdf_bytes, ai_natija)
                            
                            if tayyor_bilet:
                                st.download_button(
                                    label=f"📥 {pasport_fayl.name} uchun biletni yuklash",
                                    data=tayyor_bilet,
                                    file_name=f"tayyor_bilet_{indeks+1}.pdf",
                                    mime="application/pdf",
                                    key=f"yuklash_knopka_{indeks}"
                                )
                        
                        if indeks < len(pasportlar_royxati) - 1:
                            st.info("Limitdan qochish uchun 30 soniya kutilmoqda... ⏱️")
                            time.sleep(30)
                            
                st.balloons()
                st.success("🎉 Barcha biletlar tayyor!")
            else:
                st.warning("Iltimos, PDF bilet va kamida bitta pasport rasmini yuklang.")
    else:
        st.warning("Dasturdan foydalanish uchun chap menyudan yangi Google Gemini API kalitini kiriting.")

st.write("---")
st.caption("Dasturchi: Muxammadamin 😎")
