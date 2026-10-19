
import os
from PIL import Image, ImageDraw, ImageFont

base_image_path = "/home/lami/odoo-dev/odoo18_erp_training_repo/fleet_management/static/description/icon.png.backup"
output_path = "/home/lami/odoo-dev/odoo18_erp_training_repo/fleet_management/static/description/icon.png"

try:
    base = Image.open(base_image_path).convert("RGBA")
    width, height = base.size
    
    # Different text and color for each frame
    features = [
        {"text": "Fleet Management", "color": (255, 255, 255, 255)}, # White
        {"text": "100% Automated", "color": (16, 185, 129, 255)}, # Green #10b981
        {"text": "Fuel Quotas", "color": (236, 72, 153, 255)}, # Pink #ec4899
        {"text": "Trip Approvals", "color": (59, 130, 246, 255)}, # Blue #3b82f6
        {"text": "Driver Scorecards", "color": (245, 158, 11, 255)}  # Orange #f59e0b
    ]
    
    # Try to load a nice bold font, fallback to default
    try:
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    except:
        font_path = None
        
    frames = []
    
    for item in features:
        text = item["text"]
        color = item["color"]
        frame = base.copy()
        draw = ImageDraw.Draw(frame)
        
        # Draw a semi-transparent dark blue overlay at the bottom for text readability
        overlay_height = int(height * 0.28)
        overlay = Image.new('RGBA', (width, overlay_height), (15, 23, 42, 240)) # very dark blue almost solid
        frame.paste(overlay, (0, height - overlay_height), overlay)
        
        # Dynamic font sizing to ensure text fits
        font_size = int(height * 0.12)
        if font_path:
            font = ImageFont.truetype(font_path, font_size)
        else:
            font = ImageFont.load_default()
            
        # Reduce font size until it fits in width - 20px padding
        while font_path:
            try:
                bbox = draw.textbbox((0,0), text, font=font)
                text_w = bbox[2] - bbox[0]
            except AttributeError:
                text_w, _ = draw.textsize(text, font=font)
                
            if text_w < width - 20:
                break
            font_size -= 2
            font = ImageFont.truetype(font_path, font_size)
        
        try:
            bbox = draw.textbbox((0,0), text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
        except AttributeError:
            text_w, text_h = draw.textsize(text, font=font)
            
        x = (width - text_w) // 2
        y = height - overlay_height + (overlay_height - text_h) // 2 - 5 # shift slightly up for visual balance
        
        # Draw text with the specific color
        draw.text((x, y), text, font=font, fill=color)
        frames.append(frame)
    
    # Save as APNG (Animated PNG)
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=1800, # 1.8 seconds per frame
        loop=0,
        optimize=False
    )
    print("SUCCESS: Animated icon created")
except Exception as e:
    print(f"FAILED: {e}")
