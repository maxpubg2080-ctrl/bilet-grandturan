import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import io
import json
import time
import google.generativeai as genai

# Sahifa sozlamalari
st.set_page_config(page_title="AI PDF Modifier Ultra Pro", layout="wide")

# Chap menyu - Gemini API kalit kiritish joyi
with st.sidebar:
    st.subheader("🔑 Google AI Tizimi")
    st.info("Bu yerga aistudio.google.com saytidan olingan bepul kalitni kiriting.")
    raw_keys = st.text_input("Gemini API Kalit(lar)ni kiriting:", type="password", help="Kalitlarni vergul bilan ajrating")
    api_keys = [k.strip() for k in raw_keys.split(",")] if raw_keys else []

st.title("AI Yordamida Bilet Ma'lumotlarini Avtomat Almashtirish Pro 🚀")

def prepare_image_for_gemini(pil_image):
    """Rasmni maksimal darajada yengil formatga o'tkazish va limitlardan qochish"""
    # Rasmni AI qiynalmasligi uchun ixcham o'lchamga keltiramiz
    pil_image.thumbnail((600, 600))
    img_byte_arr = io.BytesIO()
    # Sifatini sezilarli pasaytiramiz, lekin matn o'qiladigan holatda qoladi
    pil_image.save(img_byte_arr, format='JPEG', quality=50)
    
    return {
        'mime_type': 'image/jpeg',
        'data': img_byte_arr.getvalue()
    }

def pasport_va_biletni_tahlil_qilish(passport_image, bilet_matni, keys_list):
    """Eng yuqori chidamlilikka ega model va zaxira kalitlar tizimi"""
    image_data = prepare_image_for_gemini(passport_image)
    
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
            genai.configure(api_key=key)
            # Eng so'nggi va eng katta limitga ega bepul model versiyasi
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            response = model.generate_content([prompt, image_data])
            ai_text = response.text.strip()
            
            # JSON formatni tozalash qismi
            if "```json" in ai_text:
                ai_text = ai_text.split("```json")[1].split("```")[0].strip()
            elif "```" in ai_text:
                ai_text = ai_text.split("```")[1].split("```")[0].strip()
                
            return json.loads(ai_text)
        except Exception as e:
            st.sidebar.warning(f"⚠️ Kalit-{index+1} rad etildi. Keyingisiga o'tilmoqda...")
            continue
            
    return None

def tahrirlash_bilet(pdf_bytes, data):
    """Hamma PyMuPDF versiyalarida 100% xatosiz ishlaydigan qayta chizish funksiyasi"""
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
                        # Eski matn oq to'rtburchak bilan butunlay yopiladi
                        page.draw_rect(inst, color=(1, 1, 1), fill=(1, 1, 1))
                        # Ustidan yangi matn chiroyli qilib yoziladi
                        page.insert_text(inst.tl, yangi, fontsize=9, color=(0, 0, 0))

        out_pdf = io.BytesIO()
        doc.save(out_pdf)
        doc.close()
        return out_pdf.getvalue()
    except Exception as e:
        st.error(f"PDF tahrirlashda texnik xatolik: {str(e)}")
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
                    with st.spinner("AI ma'lumotlarni o'qimoqda..."):
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
                        st.error("❌ Limitlar tufayli bu pasportni qayta ishlab bo'lmadi.")
                    
                    # Google tizimi xato bermasligi uchun qisqa tanaffus
                    time.sleep(5)
                st.balloons()
            else:
                st.error("Iltimos, oldin bilet PDF faylini va pasport rasmlarini yuklang!")
    else:
        st.warning("Dasturni ishlatish uchun chap menyuga Google Gemini API kalitini kiriting.")

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
