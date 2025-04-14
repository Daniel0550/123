
import streamlit as st
from PIL import Image, ImageOps, ImageDraw, ImageEnhance
import numpy as np
import io
import zipfile
from pdf2image import convert_from_bytes
from streamlit_image_coordinates import streamlit_image_coordinates

st.title("Автоматизация оформления тахографических документов — вставка по клику (без OpenCV)")

photo_file = st.file_uploader("📷 Фото водителя", type=["jpg", "jpeg", "png"])
statement_file = st.file_uploader("📄 Заявление (PDF или изображение)", type=["jpg", "jpeg", "png", "pdf"])
stamp_file = st.file_uploader("🧾 Печать", type=["jpg", "jpeg", "png"])
doc_files = st.file_uploader("📎 Документы", accept_multiple_files=True, type=["jpg", "jpeg", "png"])

def resize_and_center_face(img_pil):
    width, height = img_pil.size
    crop_box = (int(width * 0.2), int(height * 0.15), int(width * 0.8), int(height * 0.9))
    cropped = img_pil.crop(crop_box)
    final = Image.new("RGB", (394, 506), "white")
    resized = ImageOps.fit(cropped, (394, 506), method=Image.Resampling.LANCZOS)
    final.paste(resized)
    return final

def process_doc_image(doc_img, stamp_img):
    doc_bw = doc_img.convert("L").point(lambda x: 0 if x < 180 else 255, '1').convert("RGB")
    doc_w, doc_h = doc_bw.size
    stamp_resized = stamp_img.resize((150, 150))
    doc_bw.paste(stamp_resized, (doc_w - 170, doc_h - 170), stamp_resized)
    return doc_bw

if statement_file:
    if statement_file.name.endswith(".pdf"):
        pages = convert_from_bytes(statement_file.read())
        statement_img = pages[0].convert("RGB")
    else:
        statement_img = Image.open(statement_file).convert("RGB")

    st.subheader("🖱 Кликните по изображению, чтобы вставить фото")
    coords = streamlit_image_coordinates(statement_img)

    if coords is not None:
        x, y = int(coords["x"]), int(coords["y"])
        st.success(f"Вы выбрали координаты: X={x}, Y={y}")

        if st.button("▶️ Обработать документы"):
            result_files = {}
            if photo_file and stamp_file and doc_files:
                photo = Image.open(photo_file).convert("RGB")
                stamp = Image.open(stamp_file).convert("RGBA")
                processed_photo = resize_and_center_face(photo)

                statement_copy = statement_img.copy()
                resized = ImageOps.fit(processed_photo, (394, 506), method=Image.Resampling.LANCZOS)
                statement_copy.paste(resized, (x, y))
                result_files["statement_with_photo.jpg"] = statement_copy
                result_files["resized_passport_photo.jpg"] = processed_photo

                for i, f in enumerate(doc_files):
                    img = Image.open(f).convert("RGB")
                    processed = process_doc_image(img, stamp)
                    result_files[f"document_{i+1}.jpg"] = processed

                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w") as zipf:
                    for name, image in result_files.items():
                        buf = io.BytesIO()
                        image.save(buf, format="JPEG")
                        zipf.writestr(name, buf.getvalue())

                zip_buffer.seek(0)
                st.download_button(
                    label="📦 Скачать весь пакет",
                    data=zip_buffer,
                    file_name="tachograph_package.zip",
                    mime="application/zip"
                )
            else:
                st.warning("Загрузите все обязательные файлы.")
