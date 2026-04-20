import pdfplumber
from docx import Document
import pytesseract
from PIL import Image
from odf import text, teletype
from odf.opendocument import load

def extract_pdf(path):
    text = ""

    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""

    except Exception as e:
        print(f"⚠️ pdfplumber failed: {e}")
        text = ""

    # 🔥 Fallback to OCR if empty
    if not text.strip():
        try:
            from pdf2image import convert_from_path
            import pytesseract

            images = convert_from_path(path)
            for img in images:
                text += pytesseract.image_to_string(img)

        except Exception as e:
            print(f"❌ OCR also failed: {e}")

    return text


def extract_docx(path):
    doc = Document(path)
    return "\n".join([para.text for para in doc.paragraphs])


def extract_image(path):
    return pytesseract.image_to_string(Image.open(path))


def extract_txt(path):
    with open(path, "r") as f:
        return f.read()

def extract_odt(path):
    doc = load(path)
    all_text = []
    for elem in doc.getElementsByType(text.P):
        all_text.append(teletype.extractText(elem))
    return "\n".join(all_text)


def extract_text(path):
    """
    Main function used in pipeline
    Detects file type and routes to correct extractor
    """

    if path.endswith(".pdf"):
        return extract_pdf(path)

    elif path.endswith(".docx"):
        return extract_docx(path)

    elif path.endswith(".png") or path.endswith(".jpg") or path.endswith(".jpeg"):
        return extract_image(path)

    elif path.endswith(".txt"):
        return extract_txt(path)
        
    elif path.endswith(".odt"):
        return extract_odt(path)
    else:
        return ""