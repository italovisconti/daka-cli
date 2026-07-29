from __future__ import annotations

import base64
import io
import os
from typing import Literal

from curl_cffi import requests
from PIL import Image

TerminalProtocol = Literal["auto", "kitty", "iterm", "ansi"]


def is_kitty_terminal() -> bool:
    term = os.environ.get("TERM", "").lower()
    return "KITTY_WINDOW_ID" in os.environ or "kitty" in term or os.environ.get("KITTY_PID") is not None


def is_iterm_terminal() -> bool:
    term_prog = os.environ.get("TERM_PROGRAM", "").lower()
    return "iterm" in term_prog or "wezterm" in term_prog


def download_image(url: str) -> Image.Image | None:
    try:
        res = requests.get(url, impersonate="chrome", timeout=8)
        if res.status_code == 200:
            return Image.open(io.BytesIO(res.content))
    except Exception:
        pass
    return None


def render_kitty_graphics(img: Image.Image, max_cols: int = 40) -> str:
    """Renderiza una imagen usando el protocolo gráfico nativo de Kitty."""
    w, h = img.size
    aspect = h / w
    target_width = max_cols * 12
    target_height = int(target_width * aspect)

    resized = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
    if resized.mode != "RGBA":
        resized = resized.convert("RGBA")

    buf = io.BytesIO()
    resized.save(buf, format="PNG")
    b64_data = base64.b64encode(buf.getvalue()).decode("ascii")

    chunk_size = 4096
    chunks = [b64_data[i : i + chunk_size] for i in range(0, len(b64_data), chunk_size)]

    out = []
    for i, chunk in enumerate(chunks):
        m = 1 if i < len(chunks) - 1 else 0
        if i == 0:
            out.append(f"\033_Ga=T,f=100,m={m};{chunk}\033\\")
        else:
            out.append(f"\033_Gm={m};{chunk}\033\\")
    return "".join(out)


def render_iterm_graphics(img: Image.Image, max_cols: int = 40) -> str:
    """Renderiza una imagen usando el protocolo gráfico de iTerm2 / WezTerm."""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64_data = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"\033]1337;File=inline=1;width={max_cols}c:{b64_data}\a\n"


def render_ansi_halfblocks(img: Image.Image, width: int = 40) -> str:
    """Renderiza la imagen en bloques ANSI 24-bit TrueColor (funciona en cualquier terminal)."""
    w, h = img.size
    aspect = h / w
    height = int(width * aspect * 0.5)
    if height < 1:
        height = 1
    resized = img.resize((width, height * 2), Image.Resampling.LANCZOS).convert("RGB")

    lines = []
    for y in range(0, height * 2, 2):
        line = ""
        for x in range(width):
            r_top, g_top, b_top = resized.getpixel((x, y))
            if y + 1 < height * 2:
                r_bot, g_bot, b_bot = resized.getpixel((x, y + 1))
            else:
                r_bot, g_bot, b_bot = (0, 0, 0)
            line += f"\033[48;2;{r_top};{g_top};{b_top}m\033[38;2;{r_bot};{g_bot};{b_bot}m▄"
        line += "\033[0m"
        lines.append(line)
    return "\n".join(lines)


def render_image(
    image_source: str | Image.Image,
    width: int = 40,
    protocol: TerminalProtocol = "auto",
) -> str:
    """Renderiza una imagen para la terminal según el protocolo soportado."""
    if isinstance(image_source, str):
        img = download_image(image_source)
        if img is None:
            return f"[Error: No se pudo descargar la imagen {image_source}]"
    else:
        img = image_source

    if protocol == "kitty" or (protocol == "auto" and is_kitty_terminal()):
        return render_kitty_graphics(img, max_cols=width)
    elif protocol == "iterm" or (protocol == "auto" and is_iterm_terminal()):
        return render_iterm_graphics(img, max_cols=width)
    else:
        return render_ansi_halfblocks(img, width=width)
