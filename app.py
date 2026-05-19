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
    st.subheader("🔑 AI Kalitlar Tizimi")
    st.info("Limitdan qochish uchun bir nechta kalit kiritsangiz bo'ladi (vergul bilan ajrating)")
    raw_keys = st.text_input("Gemini API Kalit(lar)ni kiriting:", type="password", help="Kalit1, Kalit2 formatida yozing")
    
    # Kalitlarni ro'yxatga olish
    api_keys = [k.strip() for k in raw_keys.split(",")] if raw_keys else []

st.title("AI Yordamida Bilet Ma'lumotlarini Avtomat Almashtirish Pro 🚀")

def pasport_va_biletni_tahlil_qilish(passport_image, bilet_matni, keys_list):
    """Zaxira kalitlar bilan ishlovchi aqlli AI funksiyasi."""
    prompt = f"""
    Siz aqlli hujjatchisiz. Bilet matni ichidan yo'lovchining ESKI ismi, ESKI pasport raqami va ESKI tug'ilgan sanasini aniqlang.
    Pasport rasmidan YANGI yo'lovchining ismi, pasport raqami va tug'ilgan sanasini o'qing.
    
    Bilet matni:
    \"\"\"{bilet_matni}\"\"\"
    
    Natijani faqat mana shu JSON formatida qaytaring, boshqa matn qo'shmang:
    {{
      "eski_ism": "BILETDGI ESKI ISM",
      "eski_pasport": "BILETDAGI ESKI PASPORT",
      "eski_sana": "BILETDAGI ESKI SANA",
      "yangi_ism": "PASPORTDAGI YANGI ISM",
      "yangi_pasport": "PASPORTDAGI YANGI PASPORT",
      "yangi_sana": "PASPORTDAGI YANGI SANA"
    }}
    """
    
    if not keys_list:
        st.error("API kalit kiritilmagan!")
        return None

    # Har bir kalitni ketma-ket sinab ko'radi
    for current_key in keys_list:
        try:
            genai.configure(api_key=current_key)
            model = genai.GenerativeModel("gemini-2.5-flash")
            
            passport_image.thumbnail((800, 800))
            response = model.generate_content([prompt, passport_image])
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                st.warning("Bitta kalitda limit tugadi, zaxiradagiga o'tilmoqda... 🔄")
                continue
            else:
                st.error(f"Xatolik yuz berdi: {str(e)}")
                return None
    
    st.error("❌ Barcha kiritilgan API kalitlarda limit tugadi!")
    return None

def tahrirlash_bilet(pdf_bytes, data):
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page in doc:
            # 1. Ismni o'zgartirish
            if data.get("eski_ism") and data.get("yangi_ism"):
                for inst in page.search_for(data["eski_ism"]):
                    page.add_redact_annot(inst) # Qizil chiziq bilan yopish
                    page.apply_redactions()      # Eski matnni olib tashlash
                    page.insert_text(inst.tl, data["yangi_ism"], fontsize=11, color=(0, 0, 0)) # Yangisini yozish

            # 2. Pasportni o'zgartirish
            if data.get("eski_pasport") and data.get("yangi_pasport"):
                for inst in page.search_for(data["eski_pasport"]):
                    page.add_redact_annot(inst)
                    page.apply_redactions()
                    page.insert_text(inst.tl, data["yangi_pasport"], fontsize=11, color=(0, 0, 0))

            # 3. Sanani o'zgartirish
            if data.get("eski_sana") and data.get("yangi_sana"):
                for inst in page.search_for(data["eski_sana"]):
                    page.add_redact_annot(inst)
                    page.apply_redactions()
                    page.insert_text(inst.tl, data["yangi_sana"], fontsize=11, color=(0, 0, 0))

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
    uploaded_pdf = st.file_uploader("Asl PDF biletni yuklang", type=["pdf"])
    
    st.write("---")
    # CRITICAL FIX: accept_multiple_files=True qo'shildi! Endi + bosganda yo'qolmaydi.
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
                
                st.write(f"📋 Jami yuklangan pasportlar: {len(uploaded_passports)} ta")
                
                for index, passport_file in enumerate(uploaded_passports):
                    st.markdown(f"### 👤 Yo'lovchi {index+1}: {passport_file.name}")
                    
                    with st.spinner("AI tahlil qilmoqda..."):
                        passport_image = Image.open(passport_file)
                        ai_natija = pasport_va_biletni_tahlil_qilish(passport_image, bilet_matni, api_keys)
                        
                        if ai_natija:
                            st.success(f"✅ AI topdi: {ai_natija.get('yangi_ism', '')}")
                            final_pdf = tahrirlash_bilet(pdf_bytes, ai_natija)
                            
                            if final_pdf:
                                st.download_button(
                                    label=f"📥 {passport_file.name} uchun PDF-ni yuklash",
                                    data=final_pdf,
                                    file_name=f"bilet_{passport_file.name}.pdf",
                                    key=f"dl_btn_{index}"
                                )
                        
                        # Limit himoyasi
                        if index < len(uploaded_passports) - 1 and len(api_keys) == 1:
                            st.info("Kutish rejimi: 15 soniya... ⏱️")
                            time.sleep(15)
                            
                st.balloons()
                st.success("🎉 Barcha biletlar muvaffaqiyatli tayyorlandi!")
            else:
                st.warning("Iltimos, biletni va pasport(lar)ni yuklang.")
    else:
        st.warning("Dasturni ishlatish uchun chap menyudan API kalit kiriting.")

st.write("---")
st.caption("Dasturchi: Muxammadamin 😎")
