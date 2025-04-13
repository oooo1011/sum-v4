"""
创建一个Windows兼容的应用图标
使用多尺寸图标确保在不同场景下都能正确显示
"""
from PIL import Image, ImageDraw, ImageFont
import os

def create_icon(size):
    """创建指定尺寸的图标"""
    # 创建一个正方形图像，背景为深蓝色
    img = Image.new('RGBA', (size, size), color=(24, 52, 131, 255))
    draw = ImageDraw.Draw(img)
    
    # 计算圆形和文字的尺寸比例
    circle_margin = int(size * 0.15)
    circle_size = size - (circle_margin * 2)
    font_size = int(size * 0.5)
    
    # 绘制一个圆形
    draw.ellipse((circle_margin, circle_margin, 
                  circle_margin + circle_size, circle_margin + circle_size), 
                 fill=(255, 255, 255, 220))
    
    # 在圆形中绘制"∑"符号
    try:
        # 尝试加载系统字体
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        # 如果无法加载，使用默认字体
        font = ImageFont.load_default()
    
    # 绘制文本
    text_x = size // 2
    text_y = size // 2
    draw.text((text_x, text_y), "∑", fill=(24, 52, 131, 255), font=font, anchor="mm")
    
    return img

# 创建多种尺寸的图标
sizes = [16, 32, 48, 64, 128, 256]
icons = [create_icon(size) for size in sizes]

# 保存为ICO文件 (包含多个尺寸)
icons[0].save("app_icon.ico", sizes=[(size, size) for size in sizes], 
              format="ICO", append_images=icons[1:])

# 同时保存一个PNG版本用于参考
icons[-1].save("app_icon.png")

print(f"多尺寸图标已创建: {os.path.abspath('app_icon.ico')}")
