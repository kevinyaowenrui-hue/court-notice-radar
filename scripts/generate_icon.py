# -*- coding: utf-8 -*-
"""
Convert court_radar_icon to transparent multi-resolution .ico
"""
import os
from PIL import Image, ImageFilter
import numpy as np
from collections import deque

def create_transparent_icon():
    src_path = r"C:\Users\kevin\.gemini\antigravity\brain\56ccddca-1987-43a0-b15c-63a2b63d3a88\court_radar_icon_1791723846536.jpg"
    out_png = r"f:\antigravity exports\报纸采集\assets\radar_icon.png"
    out_ico = r"f:\antigravity exports\报纸采集\assets\radar_icon.ico"

    im = Image.open(src_path).convert("RGBA")
    w, h = im.size
    arr = np.array(im)

    # Compute brightness
    rgb = arr[:, :, :3].astype(np.float32)
    brightness = np.max(rgb, axis=2)

    # Flood fill from the 4 corners to find only the outside black background
    visited = np.zeros((h, w), dtype=bool)
    is_bg = np.zeros((h, w), dtype=bool)

    queue = deque()
    corners = [(0, 0), (0, w-1), (h-1, 0), (h-1, w-1)]
    for r, c in corners:
        queue.append((r, c))
        visited[r, c] = True

    # Background threshold: outside black has brightness < 15
    threshold = 14.0

    while queue:
        r, c = queue.popleft()
        if brightness[r, c] <= threshold:
            is_bg[r, c] = True
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < h and 0 <= nc < w and not visited[nr, nc]:
                    visited[nr, nc] = True
                    if brightness[nr, nc] <= threshold + 10.0:  # slight leeway
                        queue.append((nr, nc))

    # Create smooth alpha channel
    alpha = np.ones((h, w), dtype=np.uint8) * 255
    alpha[is_bg] = 0

    # Smooth the alpha mask edge with blur for anti-aliasing
    alpha_img = Image.fromarray(alpha, mode="L")
    alpha_img = alpha_img.filter(ImageFilter.GaussianBlur(radius=1.2))

    # Apply alpha back
    result_arr = np.array(im)
    result_arr[:, :, 3] = np.array(alpha_img)

    result_im = Image.fromarray(result_arr, mode="RGBA")
    result_im.save(out_png, format="PNG")
    print(f"Saved transparent master PNG to {out_png}")

    # Generate multi-size ICO: 256, 128, 64, 48, 32, 16
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    result_im.save(out_ico, format="ICO", sizes=sizes)
    print(f"Saved multi-resolution ICO to {out_ico}")

if __name__ == '__main__':
    create_transparent_icon()
