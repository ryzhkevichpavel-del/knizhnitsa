# -*- coding: utf-8 -*-
"""Иконка «Книжница» — аккуратная стопка книг на графитовом фоне."""
import os
from PIL import Image, ImageDraw

S = 512
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))

# фон — скруглённый квадрат с вертикальным градиентом (графит)
top, bottom = (60, 65, 74), (28, 31, 37)
grad = Image.new("RGB", (1, S))
for y in range(S):
    t = y / (S - 1)
    grad.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
grad = grad.resize((S, S))
mask = Image.new("L", (S, S), 0)
ImageDraw.Draw(mask).rounded_rectangle([0, 0, S - 1, S - 1], radius=112, fill=255)
img.paste(grad, (0, 0), mask)

d = ImageDraw.Draw(img)
cream = (244, 237, 224)
accent = (245, 215, 170)

# три книги стопкой (корешки лежат горизонтально), слегка разной ширины и со смещением
books = [
    # (x0, x1, y0, y1, цвет корешка, цвет «среза»)
    (120, 384, 312, 372, cream, (210, 200, 184)),
    (138, 366, 248, 308, accent, (214, 184, 142)),
    (128, 356, 184, 244, cream, (210, 200, 184)),
]
for (x0, x1, y0, y1, col, edge) in books:
    d.rounded_rectangle([x0, y0, x1, y1], radius=16, fill=col)
    # тонкая полоса-«страницы» у правого края корешка
    d.rounded_rectangle([x1 - 26, y0 + 6, x1 - 8, y1 - 6], radius=7, fill=edge)
    # маленькая «наклейка» на корешке
    d.rounded_rectangle([x0 + 18, y0 + 16, x0 + 60, y0 + 26], radius=5, fill=edge)

out = os.path.dirname(os.path.abspath(__file__))
img.save(os.path.join(out, "icon.png"))
img.save(os.path.join(out, "icon.ico"),
         sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("icon.png и icon.ico готовы")
