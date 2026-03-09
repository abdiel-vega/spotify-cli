import requests
from PIL import Image
from io import BytesIO
from functools import lru_cache


@lru_cache(maxsize=4)
def get_ascii_art(image_url: str, columns: int = 64) -> str:
    """
    downloads a Spotify album art image and converts it to a half-block
    ANSI string using the ▀ character

    each terminal character carries 2 rows of pixel color, the top pixel
    becomes the foreground color and the bottom pixel becomes the background.
    this doubles the effective vertical resolution compared to normal ASCII art,
    making the image look significantly more detailed at the same column count.
    """
    # download image into memory
    response = requests.get(image_url)
    img = Image.open(BytesIO(response.content)).convert("RGB")

    # calculate height preserving the image's square aspect ratio.
    # terminal characters are roughly twice as tall as they are wide,
    # so we set height = columns // 2 to get a square-looking output.
    # each character row will represent 2 pixel rows (top + bottom),
    # so total pixel rows needed = (columns // 2) * 2 = columns.
    pixel_width  = columns
    pixel_height = columns  # square source image → equal pixel rows

    img = img.resize((pixel_width, pixel_height), Image.LANCZOS)
    pixels = img.load()

    lines = []

    # step through the image two pixel rows at a time
    # row y   → top half of the character → foreground color of ▀
    # row y+1 → bottom half of the character → background color of ▀
    for y in range(0, pixel_height - 1, 2):
        line_parts = []

        for x in range(pixel_width):
            r1, g1, b1 = pixels[x, y]       # top pixel → foreground
            r2, g2, b2 = pixels[x, y + 1]   # bottom pixel → background

            # ANSI 24-bit color escape codes:
            # \033[38;2;R;G;Bm  sets foreground (text) color
            # \033[48;2;R;G;Bm  sets background color
            # ▀ is the upper-half-block character, its top half takes
            # the foreground color and its bottom half takes the background.
            line_parts.append(
                f"\033[38;2;{r1};{g1};{b1}m"   # set foreground to top pixel
                f"\033[48;2;{r2};{g2};{b2}m"   # set background to bottom pixel
                f"▀"                           # upper half block character
            )

        # \033[0m resets all color attributes at the end of each line
        # so colors don't bleed into adjacent terminal content
        lines.append("".join(line_parts) + "\033[0m")

    return "\n".join(lines)