import io
import os
import random
import string

from django.conf import settings
from PIL import Image, ImageDraw, ImageFont

CAPTCHA_LENGTH = 6
CAPTCHA_WIDTH = 150
CAPTCHA_HEIGHT = 40
FONT_SIZE = 28
FONT_FILE = os.path.join(settings.BASE_DIR, "static", "DejaVuSans-Bold.ttf")

def generate_captcha_text(length=CAPTCHA_LENGTH):
    """Generate a random CAPTCHA text."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def generate_captcha_image(text):
    """Generate a CAPTCHA image with text and noise."""
    image = Image.new('RGB', (CAPTCHA_WIDTH, CAPTCHA_HEIGHT), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)

    try:
        # Try to load a TrueType font (adjust path as needed for your system)
        font = ImageFont.truetype(FONT_FILE, FONT_SIZE)
    except:
        font = ImageFont.load_default()

    # Get text dimensions
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Center the text
    x = (CAPTCHA_WIDTH - text_width) // 2
    y = (CAPTCHA_HEIGHT - text_height) // 2

    # Add some random variation to character positions for security
    char_positions = []
    current_x = x
    for i, char in enumerate(text):
        char_bbox = draw.textbbox((0, 0), char, font=font)
        char_width = char_bbox[2] - char_bbox[0]

        # Add slight random offset to each character
        char_y = y + random.randint(-3, 3)
        char_positions.append((current_x, char_y, char))
        current_x += char_width + random.randint(-2, 2)  # Slight spacing variation

    # Draw each character with slight random positioning
    for char_x, char_y, char in char_positions:
        # Random color variation for each character (dark colors for readability)
        color = (random.randint(0, 100), random.randint(0, 100), random.randint(0, 100))
        draw.text((char_x, char_y), char, fill=color, font=font)

    # Add noise lines
    for _ in range(3):
        x1, y1 = random.randint(0, CAPTCHA_WIDTH), random.randint(0, CAPTCHA_HEIGHT)
        x2, y2 = random.randint(0, CAPTCHA_WIDTH), random.randint(0, CAPTCHA_HEIGHT)
        color = (random.randint(150, 255), random.randint(150, 255), random.randint(150, 255))
        draw.line((x1, y1, x2, y2), fill=color, width=1)

    # Add noise points (reduced number for better readability)
    for _ in range(30):
        x = random.randint(0, CAPTCHA_WIDTH)
        y = random.randint(0, CAPTCHA_HEIGHT)
        color = (random.randint(150, 255), random.randint(150, 255), random.randint(150, 255))
        draw.point((x, y), fill=color)

    # Convert to bytes
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr.getvalue()
