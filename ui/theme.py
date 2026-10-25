"""
Theme and Design Tokens for Classroom AI Face Recognition System.
Provides a modern dark slate palette, typography standards, and widget styling.
"""

# Color Palette
BG_DARK = "#090d16"           # Window Background
BG_SURFACE = "#0f172a"        # Card / Sidebar Surface
BG_CARD = "#1e293b"           # Elevated Card Surface
BG_CARD_HOVER = "#273549"     # Card Hover State
BORDER_COLOR = "#334155"      # Subtle Border

ACCENT_BLUE = "#38bdf8"       # Electric Sky Blue
ACCENT_BLUE_DARK = "#0284c7"  # Deeper Sky Blue
ACCENT_EMERALD = "#10b981"    # Success / Present
ACCENT_AMBER = "#f59e0b"      # Warning / Processing
ACCENT_ROSE = "#ef4444"       # Danger / Unknown / Absent

TEXT_MAIN = "#f8fafc"         # Crisp White
TEXT_MUTED = "#94a3b8"        # Secondary Muted
TEXT_DIM = "#64748b"          # Tertiary Dim

# Fonts
FONT_TITLE = ("Segoe UI", 16, "bold")
FONT_SUBTITLE = ("Segoe UI", 12, "bold")
FONT_BODY = ("Segoe UI", 10)
FONT_BODY_BOLD = ("Segoe UI", 10, "bold")
FONT_SMALL = ("Segoe UI", 9)
FONT_MONO = ("Consolas", 10)

def style_button(btn, variant="primary"):
    """Applies modern flat aesthetics and hover states to Tkinter buttons."""
    if variant == "primary":
        bg, fg, active_bg = ACCENT_BLUE, "#090d16", ACCENT_BLUE_DARK
    elif variant == "success":
        bg, fg, active_bg = ACCENT_EMERALD, "#ffffff", "#059669"
    elif variant == "danger":
        bg, fg, active_bg = ACCENT_ROSE, "#ffffff", "#dc2626"
    elif variant == "secondary":
        bg, fg, active_bg = BG_CARD, TEXT_MAIN, BG_CARD_HOVER
    else:
        bg, fg, active_bg = BG_CARD, TEXT_MUTED, BG_CARD_HOVER

    btn.configure(
        bg=bg,
        fg=fg,
        activebackground=active_bg,
        activeforeground=fg,
        relief="flat",
        bd=0,
        cursor="hand2",
        font=FONT_BODY_BOLD,
        padx=12,
        pady=6
    )
