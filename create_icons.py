from PIL import Image, ImageDraw, ImageFont

def create_icon(size, filename):
    # Create image with gradient background
    img = Image.new('RGB', (size, size), color='#2196F3')
    draw = ImageDraw.Draw(img)

    # Draw a shield shape (simplified)
    # Background circle
    margin = size // 8
    draw.ellipse([margin, margin, size-margin, size-margin], fill='#1976D2')

    # Draw a lock symbol using basic shapes
    lock_width = size // 2
    lock_height = size // 2
    x_offset = (size - lock_width) // 2
    y_offset = (size - lock_height) // 2 + size // 10

    # Lock body
    body_height = lock_height * 0.5
    draw.rounded_rectangle(
        [x_offset, y_offset + lock_height - body_height,
         x_offset + lock_width, y_offset + lock_height],
        radius=size//20,
        fill='white'
    )

    # Lock shackle
    shackle_width = lock_width * 0.6
    shackle_x = x_offset + (lock_width - shackle_width) / 2
    draw.arc(
        [shackle_x, y_offset, shackle_x + shackle_width, y_offset + lock_height*0.6],
        start=0, end=180, fill='white', width=size//12
    )

    img.save(filename)
    print(f"✅ Created {filename}")

# Create icons in different sizes
create_icon(16, 'exam-monitor/icon16.png')
create_icon(48, 'exam-monitor/icon48.png')
create_icon(128, 'exam-monitor/icon128.png')

print("\n🎨 All icons created successfully!")
