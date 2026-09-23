import io
import pandas as pd
import streamlit as st
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

# Настройка страницы
st.set_page_config(
    page_title="AutoProtocol AI | Самрук-Казына", layout="wide"
)

st.title("🎙️ AI-Ассистент автопротоколирования совещаний")
st.subheader("АО «Самрук-Қазына Өңдеу» — On-Premise Контур")

# Демо-данные для протокола
DEMO_SUMMARY = [
    (
        "Загрузка мощностей за 9 месяцев составляет 71%. Потери на логистике"
        " — до 8% себестоимости."
    ),
    (
        "Проект модернизации Павлодарского завода: ТЭО готово на 60%, есть"
        " риск сдвига на полгода."
    ),
    (
        "На Павлодарском заводе произошла разгерметизация линии. Причина —"
        " датчики газа не проходили поверку."
    ),
]

DEMO_TASKS = [
    {
        "Поручение": "Разработать единую стратегию закупа сырья",
        "Ответственный": "Гульмира Сериковна",
        "Срок": "15 октября",
    },
    {
        "Поручение": "Согласовать график поставок с проектным институтом",
        "Ответственный": "Айнур Каировна",
        "Срок": "26 сентября",
    },
    {
        "Поручение": "Подготовить финансовое решение по Павлодарскому заводу",
        "Ответственный": "Тимур Болатович",
        "Срок": "30 сентября",
    },
    {
        "Поручение": (
            "Провести полный аудит датчиков и СИЗ на 11 производственных"
            " площадках"
        ),
        "Ответственный": "Нурлан Сагатович",
        "Срок": "15 октября",
    },
]


def create_docx(summary, tasks_df):
  """Генерация официального документа DOCX."""
  doc = Document()
  p = doc.add_paragraph()
  p.alignment = WD_ALIGN_PARAGRAPH.CENTER
  run = p.add_run("ПРОТОКОЛ СОВЕЩАНИЯ\nАО «Самрук-Қазына Өңдеу»")
  run.bold = True
  run.font.size = Pt(16)

  doc.add_heading("1. Краткое саммари", level=1)
  for point in summary:
    doc.add_paragraph(point, style="List Bullet")

  doc.add_heading("2. Реестр поручений", level=1)
  table = doc.add_table(rows=1, cols=4)
  table.style = "Table Grid"

  hdr = table.rows[0].cells
  hdr[0].text = "№"
  hdr[1].text = "Суть поручения"
  hdr[2].text = "Ответственный"
  hdr[3].text = "Срок"

  for i, row_data in tasks_df.iterrows():
    row = table.add_row().cells
    row[0].text = str(i + 1)
    row[1].text = str(row_data.get("Поручение", ""))
    row[2].text = str(row_data.get("Ответственный", ""))
    row[3].text = str(row_data.get("Срок", ""))

  buffer = io.BytesIO()
  doc.save(buffer)
  buffer.seek(0)
  return buffer


# Боковая панель
st.sidebar.header("Настройки обработки")
st.sidebar.info(
    "🔒 Работает в ЗАКРЫТОМ контуре (On-premise). Данные не передаются во"
    " внешние API."
)

# Загрузка файла
uploaded_file = st.file_uploader(
    "Загрузите аудиозапись совещания (.mp3 / .wav)", type=["mp3", "wav"]
)

if st.button("🚀 Сформировать протокол с помощью ИИ"):
  st.success("Протокол успешно сформирован!")

  col1, col2 = st.columns(2)

  with col1:
    st.subheader("📋 Краткое саммари")
    for item in DEMO_SUMMARY:
      st.write(f"• {item}")

  with col2:
    st.subheader("📌 Извлеченные поручения")
    df = pd.DataFrame(DEMO_TASKS)
    edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)

  docx_file = create_docx(DEMO_SUMMARY, edited_df)

  st.download_button(
      label="📥 Скачать официальный протокол (.DOCX)",
      data=docx_file,
      file_name="Protocol_Samruk_Kazyna.docx",
      mime=(
          "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
      ),
  )
