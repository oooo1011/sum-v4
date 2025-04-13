"""
使用更可靠的方法创建Windows兼容的图标
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageColor

def create_simple_icon(size, bg_color="#1834a3", text="∑", text_color="#ffffff"):
    """创建简单的图标"""
    # 创建一个正方形图像
    img = Image.new('RGBA', (size, size), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 绘制背景圆形
    draw.ellipse((0, 0, size, size), fill=bg_color)
    
    # 计算文字大小
    font_size = int(size * 0.6)
    
    # 尝试加载系统字体
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        try:
            # 尝试其他常见字体
            font = ImageFont.truetype("segoeui.ttf", font_size)
        except:
            # 如果都失败，使用默认字体
            font = ImageFont.load_default()
    
    # 绘制文本
    text_x = size // 2
    text_y = size // 2
    draw.text((text_x, text_y), text, fill=text_color, font=font, anchor="mm")
    
    return img

# 创建图标的各种尺寸
sizes = [16, 24, 32, 48, 64, 128, 256]
images = []

print("创建各种尺寸的图标...")
for size in sizes:
    img = create_simple_icon(size)
    images.append(img)
    # 保存单独的PNG文件以便检查
    img.save(f"icon_{size}x{size}.png")
    print(f"- 已创建 {size}x{size} 尺寸图标")

# 保存为.ico文件
ico_path = "windows_app_icon.ico"
images[0].save(ico_path, format="ICO", sizes=[(size, size) for size in sizes], append_images=images[1:])
print(f"图标已保存为: {os.path.abspath(ico_path)}")

# 创建一个更大的预览图
preview = create_simple_icon(512)
preview.save("icon_preview.png")
print(f"预览图已保存为: {os.path.abspath('icon_preview.png')}")

print("\n提示: 如果打包时图标仍然不生效，请尝试使用专业图标编辑工具如IcoFX或ResourceHacker")
