"""Caption style chosen in the Studio: font, colours, outline, position on screen, animation."""

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# key -> (font family for libass on the server, weight is in the family name where needed)
FONTS: dict[str, str] = {
    "montserrat_black": "Montserrat Black",
    "montserrat": "Montserrat ExtraBold",
    "bebas": "Bebas Neue",
    "roboto": "Roboto",
    "open_sans": "Open Sans",
    "lato_black": "Lato Black",
    "dejavu": "DejaVu Sans",
}

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


class CaptionStyle(BaseModel):
    font: Literal[tuple(FONTS)] = "montserrat_black"  # type: ignore[valid-type]
    size: int = Field(default=92, ge=36, le=180)
    color: str = "#FFFFFF"
    highlight_color: str = "#FFD84D"
    outline_color: str = "#000000"
    outline: int = Field(default=7, ge=0, le=14)
    shadow: int = Field(default=3, ge=0, le=10)
    uppercase: bool = True
    words_per_cue: int = Field(default=3, ge=1, le=7)
    position: int = Field(default=50, ge=8, le=92, description="vertical centre of the caption, % from top")
    animation: Literal["none", "fade", "pop", "slide_up", "karaoke"] = "pop"

    @field_validator("color", "highlight_color", "outline_color")
    @classmethod
    def _hex(cls, v: str) -> str:
        if not HEX.match(v):
            raise ValueError("colour must look like #RRGGBB")
        return v.upper()


def ass_colour(hex_rgb: str, alpha: int = 0) -> str:
    """#RRGGBB -> ASS &HAABBGGRR."""
    r, g, b = hex_rgb[1:3], hex_rgb[3:5], hex_rgb[5:7]
    return f"&H{alpha:02X}{b}{g}{r}".upper()
