import streamlit as st
from PIL import Image, ImageOps
import numpy as np
import io
import zipfile
from pdf2image import convert_from_bytes
import cv2
from streamlit_image_coordinates import streamlit_image_coordinates

st.title("Автоматизация оформления тахографических документов — вставка по клику")

photo_file = st.file_uploader("📷 Фото водителя", type=["jpg", "jpeg", "png"])
statement_file = st.file_uploader("📄 Заявление (PDF или изображение)", type=["jpg", "jpeg", "png", "pdf"])
stamp_file = st.file_uploader("🧾 Печать", type=["jpg", "jpeg", "png"])
doc_files = st.file_uploader("📎 Документы", accept_multiple_files=True, type=["jpg", "jpeg", "png"])

def crop_face_high_quality(img_pil):
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    img_cv = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 5)
    if len(faces) == 0:
        return None
    (x, y, w, h) = faces[0]
    top = max(y - int(0.25 * h), 0)
    bottom = min(y + int(1.6 * h), img_pil.height)
    left = max(x - int(0.3 * w), 0)
    right = min(x + int(1.3 * w), img_pil.width)
    region = img_pil.crop((left, top, right, bottom))
    canvas = Image.new("RGB", (394, 506), "white")
    face = ImageOps.fit(region, (394, 506), method=Image.Resampling.LANCZOS)
    canvas.paste(face)
    return canvas

def process_doc_image(doc_img, stamp_img):
    gray = cv2.cvtColor(np.array(doc_img), cv2.COLOR_RGB2GRAY)
    _, bw = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
    result = Image.fromarray(bw).convert("RGB")
    doc_w, doc_h = result.size
    stamp_resized = stamp_img.resize((150, 150))
    result.paste(stamp_resized, (doc_w - 170, doc_h - 170), stamp_resized)
    return result

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
                processed_photo = crop_face_high_quality(photo)

                if processed_photo is None:
                    st.error("❌ Лицо не найдено.")
                else:
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
