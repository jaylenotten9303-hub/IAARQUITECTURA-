import base64
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_text_from_image(file_bytes: bytes, filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext == "pdf":
        raise ValueError("PDF no soportado. Sube una imagen JPG o PNG.")
    mime = f"image/{'jpeg' if ext == 'jpg' else ext}"
    b64 = base64.b64encode(file_bytes).decode("utf-8")

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Extract all text, numbers, equations, and data from this image exactly as written. Return only the extracted content, no commentary.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}"},
                    },
                ],
            }
        ],
        max_tokens=1000,
    )
    return response.choices[0].message.content.strip()
