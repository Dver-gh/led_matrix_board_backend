from io import BytesIO

import requests
from PIL import Image, ImageOps


def process_album_art_to_cd(image_url: str, output_size: int = 38) -> bytes | None:
    """
    Downloads ablum's cover art from URL, cuts it into a rectangle,
    then applies it onto a CD player mask and returns it as bytes.
    """
    if not image_url:
        return None

    try:
        response = requests.get(image_url, timeout=5)
        if response.status_code != 200:
            return None

        img = Image.open(BytesIO(response.content)).convert("RGBA")

        img = ImageOps.fit(img, (output_size, output_size), centering=(0.5, 0.5))

        mask = Image.new("L", (output_size, output_size), 0)
        from PIL import ImageDraw
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, output_size, output_size), fill=255)

        cd_img = Image.new("RGBA", (output_size, output_size), (0, 0, 0, 0))
        cd_img.paste(img, (0, 0), mask=mask)

        hole_size = max(4, output_size // 10)
        hole_pos = (output_size - hole_size) // 2
        draw_cd = ImageDraw.Draw(cd_img)
        draw_cd.ellipse(
            (hole_pos, hole_pos, hole_pos + hole_size, hole_pos + hole_size),
            fill=(0, 0, 0, 255)
        )

        output_buffer = BytesIO()
        cd_img.save(output_buffer, format="PNG")
        return output_buffer.getvalue()

    except (OSError, requests.exceptions.RequestException) as e:
        print(f"Error during processing spotify album cover: {e}")
        return None
