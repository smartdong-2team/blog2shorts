from pathlib import Path

FONT_DIR = Path(__file__).resolve().parents[2] / "assets" / "fonts"

FONT_SIZE = 60

# 제목(hook_text)에서 *로 감싼 강조 부분: 노란 배경에 어두운 글자
HOOK_HIGHLIGHT = {
    "color": "#111111",
    "background_color": "#FFE45C",
    "padding": 12,
}

SUBTITLE_STYLES = {
    "default": {
        "font_file": FONT_DIR / "Pretendard-Black.otf",
        "font_size": FONT_SIZE,
        "color": "#FFFFFF",
        "outline_color": "#000000",
        "outline_width": 10,
        "background_color": "#000000",
        "background_opacity": 1,
        "background_padding": 15,
    },
    "highlight": {
        "font_file": FONT_DIR / "ChosunCentennial.ttf",
        "font_size": 80,
        "color": "#FFE45C",
        "outline_color": "#000000",
        "outline_width": 10,
        "background_color": "#000000",
        "background_opacity": 1,
        "background_padding": 15,
    },
    "impact": {
        "font_file": FONT_DIR / "ChosunCentennial.ttf",
        "font_size": 80,
        "color": "#FF4545",
        "outline_color": "#000000",
        "outline_width": 10,
        "background_color": "#000000",
        "background_opacity": 1,
        "background_padding": 15,
    },
}