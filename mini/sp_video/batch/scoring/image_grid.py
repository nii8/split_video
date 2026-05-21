"""
第一阶段：拼 9 宫格。

设计原则：
1. 固定就是 9 张图
2. 固定就是 3x3
3. 不做可变布局

后续如果运行环境有更好的拼图方式，直接替换 make_grid_image() 就行。
"""

import os
import shutil


def pad_images_for_grid(image_paths):
    """不足 9 张时重复最后一张补齐"""
    if not image_paths:
        return []

    padded = list(image_paths)
    while len(padded) < 9:
        padded.append(padded[-1])
    return padded[:9]


def make_grid_image(image_paths, output_path):
    """固定拼成 3x3 的 9 宫格图"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True) if os.path.dirname(output_path) else None
    padded = pad_images_for_grid(image_paths)
    if not padded:
        return None

    try:
        from PIL import Image
    except ImportError:
        # 如果 Pillow 没装，不让流程直接死掉，先复制第一张图占位。
        shutil.copyfile(padded[0], output_path)
        return output_path

    images = [Image.open(path).convert("RGB") for path in padded]
    thumb_size = (320, 180)
    for img in images:
        img.thumbnail(thumb_size)

    grid = Image.new("RGB", (thumb_size[0] * 3, thumb_size[1] * 3), color=(0, 0, 0))
    for idx, img in enumerate(images):
        x = (idx % 3) * thumb_size[0]
        y = (idx // 3) * thumb_size[1]
        if img.size != thumb_size:
            canvas = Image.new("RGB", thumb_size, color=(0, 0, 0))
            offset = ((thumb_size[0] - img.size[0]) // 2, (thumb_size[1] - img.size[1]) // 2)
            canvas.paste(img, offset)
            img = canvas
        grid.paste(img, (x, y))

    grid.save(output_path, quality=90)
    return output_path
