"""
Erstellt ein einfaches Icon für die Anwendung
Benötigt: pip install pillow
"""

from PIL import Image, ImageDraw, ImageFont
import sys

def create_icon():
    """Erstellt ein einfaches Icon"""

    # Icon-Größen
    sizes = [16, 32, 48, 64, 128, 256]

    # Für Windows ICO
    images = []

    for size in sizes:
        # Bild erstellen
        img = Image.new('RGB', (size, size), color='#1e1e1e')
        draw = ImageDraw.Draw(img)

        # Kreis zeichnen (TOR-ähnlich)
        margin = size // 10
        draw.ellipse(
            [margin, margin, size-margin, size-margin],
            fill='#7d4698',  # Lila (TOR-Farbe)
            outline='#ffffff',
            width=max(1, size // 32)
        )

        # Innerer Kreis
        inner_margin = size // 4
        draw.ellipse(
            [inner_margin, inner_margin, size-inner_margin, size-inner_margin],
            fill='#1e1e1e',
            outline='#ffffff',
            width=max(1, size // 32)
        )

        # Text "RSS"
        if size >= 32:
            try:
                font_size = size // 4
                # Versuche eine Schriftart zu laden
                try:
                    font = ImageFont.truetype("arial.ttf", font_size)
                except:
                    font = ImageFont.load_default()

                text = "RSS"
                # Text-Bounding-Box ermitteln
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]

                # Text zentrieren
                x = (size - text_width) // 2
                y = (size - text_height) // 2

                draw.text((x, y), text, fill='#ffffff', font=font)
            except:
                pass

        images.append(img)

    # Windows ICO speichern
    images[0].save(
        'icon.ico',
        format='ICO',
        sizes=[(img.width, img.height) for img in images],
        append_images=images[1:]
    )
    print("✅ Icon erstellt: icon.ico")

    # PNG für andere Plattformen
    images[-1].save('icon.png', format='PNG')
    print("✅ Icon erstellt: icon.png")

    # macOS ICNS (benötigt zusätzliche Tools)
    print("ℹ️  Für macOS .icns verwenden Sie: png2icns icon.icns icon.png")

if __name__ == '__main__':
    try:
        create_icon()
    except ImportError:
        print("❌ Pillow nicht installiert!")
        print("Installieren Sie es mit: pip install pillow")
        sys.exit(1)
