import base64
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MAX_IMAGES = 20

def _mime(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext == "pdf":
        raise ValueError("PDF no soportado. Sube imágenes JPG o PNG.")
    return f"image/{'jpeg' if ext == 'jpg' else ext}"

def _image_block(file_bytes: bytes, filename: str) -> dict:
    return {
        "type": "image_url",
        "image_url": {
            "url": f"data:{_mime(filename)};base64,{base64.b64encode(file_bytes).decode()}",
            "detail": "high",
        },
    }

def extract_text_from_images(files: list[tuple[bytes, str]]) -> str:
    """Extract text from 1–20 images in a single GPT-4o Vision call."""
    if not files:
        raise ValueError("No se recibieron imágenes.")
    if len(files) > MAX_IMAGES:
        raise ValueError(f"Máximo {MAX_IMAGES} imágenes por solicitud.")

    n = len(files)
    content = [
        {
            "type": "text",
            "text": (
                f"Tengo {n} imagen(es) de un problema de ingeniería estructural. "
                "Extrae TODO el texto, números, ecuaciones, tablas y datos de todas las imágenes, "
                "en orden. Incluye títulos, unidades, valores dados y lo que se pide calcular. "
                "Devuelve solo el contenido extraído, sin comentarios."
            ),
        }
    ] + [_image_block(fb, fn) for fb, fn in files]

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": content}],
        max_tokens=4000,
    )
    return response.choices[0].message.content.strip()
