"""Colour palettes for presentations.

Each theme is four colours:
    bg     - slide background
    title  - slide titles
    text   - body text
    accent - highlights (subtitle, decorative elements)
"""
from pptx.dml.color import RGBColor

DEFAULT_THEME = "Corporate Blue"

THEMES = {
    # ---------- Original themes ----------
    "Corporate Blue": {
        "bg": RGBColor(245, 247, 250),
        "title": RGBColor(16, 44, 87),
        "text": RGBColor(53, 55, 64),
        "accent": RGBColor(53, 89, 224)
    },
    "Dark Modern": {
        "bg": RGBColor(24, 26, 32),
        "title": RGBColor(255, 255, 255),
        "text": RGBColor(200, 205, 215),
        "accent": RGBColor(0, 210, 180)
    },
    "Minimalist Light": {
        "bg": RGBColor(255, 255, 255),
        "title": RGBColor(20, 20, 20),
        "text": RGBColor(80, 80, 80),
        "accent": RGBColor(220, 50, 50)
    },
    "Eco Green": {
        "bg": RGBColor(242, 248, 244),
        "title": RGBColor(20, 60, 35),
        "text": RGBColor(50, 70, 60),
        "accent": RGBColor(46, 139, 87)
    },

    # ---------- Light themes ----------
    "Ocean Breeze": {
        "bg": RGBColor(240, 248, 252),
        "title": RGBColor(8, 60, 90),
        "text": RGBColor(45, 70, 85),
        "accent": RGBColor(0, 120, 160)
    },
    "Sunset Warm": {
        "bg": RGBColor(255, 246, 238),
        "title": RGBColor(120, 40, 20),
        "text": RGBColor(80, 55, 45),
        "accent": RGBColor(196, 70, 20)
    },
    "Lavender Dream": {
        "bg": RGBColor(247, 244, 252),
        "title": RGBColor(60, 40, 110),
        "text": RGBColor(75, 65, 95),
        "accent": RGBColor(120, 70, 195)
    },
    "Rose Quartz": {
        "bg": RGBColor(253, 244, 246),
        "title": RGBColor(110, 25, 55),
        "text": RGBColor(85, 60, 68),
        "accent": RGBColor(190, 40, 95)
    },
    "Desert Sand": {
        "bg": RGBColor(250, 245, 235),
        "title": RGBColor(92, 64, 30),
        "text": RGBColor(80, 68, 55),
        "accent": RGBColor(160, 98, 28)
    },
    "Mint Fresh": {
        "bg": RGBColor(240, 251, 247),
        "title": RGBColor(10, 80, 70),
        "text": RGBColor(45, 75, 70),
        "accent": RGBColor(0, 130, 105)
    },
    "Coffee House": {
        "bg": RGBColor(245, 238, 230),
        "title": RGBColor(62, 39, 25),
        "text": RGBColor(84, 66, 56),
        "accent": RGBColor(145, 80, 40)
    },
    "Arctic Frost": {
        "bg": RGBColor(238, 244, 250),
        "title": RGBColor(25, 45, 75),
        "text": RGBColor(60, 75, 95),
        "accent": RGBColor(40, 105, 180)
    },
    "Paper & Ink": {
        "bg": RGBColor(250, 248, 243),
        "title": RGBColor(30, 30, 35),
        "text": RGBColor(70, 70, 75),
        "accent": RGBColor(30, 90, 160)
    },
    "Sage Garden": {
        "bg": RGBColor(243, 246, 238),
        "title": RGBColor(55, 70, 45),
        "text": RGBColor(85, 100, 75),
        "accent": RGBColor(95, 125, 45)
    },
    "Teal & Coral": {
        "bg": RGBColor(244, 251, 251),
        "title": RGBColor(10, 70, 80),
        "text": RGBColor(55, 80, 85),
        "accent": RGBColor(215, 70, 60)
    },
    "Indigo Ink": {
        "bg": RGBColor(244, 245, 252),
        "title": RGBColor(30, 35, 110),
        "text": RGBColor(65, 70, 110),
        "accent": RGBColor(80, 70, 220)
    },
    "Burgundy Classic": {
        "bg": RGBColor(250, 244, 242),
        "title": RGBColor(95, 20, 35),
        "text": RGBColor(80, 60, 60),
        "accent": RGBColor(150, 30, 50)
    },
    "Retro Cream": {
        "bg": RGBColor(245, 235, 210),
        "title": RGBColor(60, 45, 30),
        "text": RGBColor(95, 80, 60),
        "accent": RGBColor(185, 60, 40)
    },
    "High Contrast": {
        "bg": RGBColor(255, 255, 255),
        "title": RGBColor(0, 0, 0),
        "text": RGBColor(30, 30, 30),
        "accent": RGBColor(0, 70, 200)
    },

    # ---------- Dark themes ----------
    "Midnight Purple": {
        "bg": RGBColor(22, 18, 40),
        "title": RGBColor(255, 255, 255),
        "text": RGBColor(205, 198, 230),
        "accent": RGBColor(170, 120, 255)
    },
    "Deep Ocean": {
        "bg": RGBColor(8, 25, 45),
        "title": RGBColor(235, 248, 255),
        "text": RGBColor(170, 200, 225),
        "accent": RGBColor(0, 190, 230)
    },
    "Forest Night": {
        "bg": RGBColor(16, 30, 24),
        "title": RGBColor(232, 248, 238),
        "text": RGBColor(175, 205, 188),
        "accent": RGBColor(120, 220, 130)
    },
    "Charcoal & Amber": {
        "bg": RGBColor(30, 30, 32),
        "title": RGBColor(255, 244, 225),
        "text": RGBColor(205, 200, 190),
        "accent": RGBColor(255, 170, 40)
    },
    "Crimson Noir": {
        "bg": RGBColor(20, 14, 16),
        "title": RGBColor(255, 240, 240),
        "text": RGBColor(210, 190, 194),
        "accent": RGBColor(255, 80, 90)
    },
    "Cyberpunk": {
        "bg": RGBColor(14, 10, 28),
        "title": RGBColor(255, 255, 255),
        "text": RGBColor(190, 200, 240),
        "accent": RGBColor(255, 45, 170)
    },
    "Graphite Blue": {
        "bg": RGBColor(28, 34, 44),
        "title": RGBColor(255, 255, 255),
        "text": RGBColor(180, 195, 215),
        "accent": RGBColor(90, 160, 255)
    },
    "Espresso Gold": {
        "bg": RGBColor(36, 26, 20),
        "title": RGBColor(250, 236, 200),
        "text": RGBColor(210, 195, 175),
        "accent": RGBColor(222, 170, 60)
    },
    "Terminal Green": {
        "bg": RGBColor(6, 14, 8),
        "title": RGBColor(190, 255, 200),
        "text": RGBColor(130, 210, 145),
        "accent": RGBColor(60, 255, 110)
    },
    "Royal Navy & Gold": {
        "bg": RGBColor(14, 26, 56),
        "title": RGBColor(255, 255, 255),
        "text": RGBColor(200, 210, 235),
        "accent": RGBColor(240, 190, 60)
    },
    "Plum Wine": {
        "bg": RGBColor(40, 16, 32),
        "title": RGBColor(255, 240, 248),
        "text": RGBColor(225, 195, 215),
        "accent": RGBColor(255, 120, 170)
    },
    "Pure Black": {
        "bg": RGBColor(0, 0, 0),
        "title": RGBColor(255, 255, 255),
        "text": RGBColor(190, 190, 190),
        "accent": RGBColor(255, 214, 0)
    },
    "Blueprint": {
        "bg": RGBColor(18, 52, 110),
        "title": RGBColor(255, 255, 255),
        "text": RGBColor(205, 225, 250),
        "accent": RGBColor(255, 220, 90)
    },
}
