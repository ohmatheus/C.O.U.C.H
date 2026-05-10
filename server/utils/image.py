from io import BytesIO

from PIL import Image


def resize_screenshot(data: bytes, max_size: int = 800) -> bytes:
    img = Image.open(BytesIO(data))
    img.thumbnail((max_size, max_size), Image.LANCZOS)
    out = BytesIO()
    img.save(out, format="JPEG", quality=75)
    return out.getvalue()
