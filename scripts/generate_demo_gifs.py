#!/usr/bin/env python3
"""Generate animated demo GIFs for pymasking web UI documentation."""

from PIL import Image, ImageDraw, ImageFont
import os, math

# ── Constants ─────────────────────────────────────────────────────────────
W, H      = 900, 700
TELOP_H   = 64
CONTENT_H = H - TELOP_H   # 636

# Colours
BG        = (244, 246, 248)
HDR_BG    = ( 26,  26,  46)
WHITE     = (255, 255, 255)
DARK      = ( 51,  51,  51)
MED       = ( 85,  85,  85)
BLUE      = ( 67,  97, 238)
BLUE_HOV  = ( 52,  81, 209)
BLUE_LIT  = (238, 242, 255)
BORDER    = (200, 212, 220)
BORDER2   = (222, 226, 230)
SHADOW    = (215, 218, 222)
CATBG     = (248, 249, 250)
PHOLDER   = (175, 175, 175)
STS_OK    = ( 45, 106,  79)
STS_ERR   = (230,  57,  70)
RES_BG    = (248, 249, 250)

# Layout
HDR_H   = 58
TABS_Y  = HDR_H + 20      # 78
TABS_H  = 36
TABBDR  = TABS_Y + TABS_H  # 114
CARD_Y  = TABBDR + 14      # 128
CARD_X  = 16
CARD_W  = W - 32           # 868
CP      = 22               # card padding
INX     = CARD_X + CP      # 38 – inner left
INY     = CARD_Y + CP      # 150 – inner top
INW     = CARD_W - 2 * CP  # 824 – inner width

# Fonts
JP  = "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf"
LT  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
_fc = {}

def F(size):
    if size not in _fc:
        try:
            _fc[size] = ImageFont.truetype(JP, size)
        except Exception:
            _fc[size] = ImageFont.load_default()
    return _fc[size]

def TW(text, size=15):
    return F(size).getlength(text)

def rr(draw, xy, r=6, fill=None, ol=None, lw=1):
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle([x1, y1, x2, y2], radius=r, fill=fill, outline=ol, width=lw)

# ── Dashed rect ───────────────────────────────────────────────────────────
def dashed_rect(draw, xy, color=(150,150,150), lw=2, dash=8, gap=5):
    x1, y1, x2, y2 = xy
    sides = [(x1,y1,x2,y1), (x2,y1,x2,y2), (x2,y2,x1,y2), (x1,y2,x1,y1)]
    for sx,sy,ex,ey in sides:
        length = math.hypot(ex-sx, ey-sy)
        if length == 0:
            continue
        dx, dy = (ex-sx)/length, (ey-sy)/length
        pos = 0.0
        drawing = True
        while pos < length:
            seg = dash if drawing else gap
            end = min(pos+seg, length)
            if drawing:
                draw.line([(sx+pos*dx, sy+pos*dy), (sx+end*dx, sy+end*dy)], fill=color, width=lw)
            pos = end
            drawing = not drawing

# ── Mouse cursor ──────────────────────────────────────────────────────────
def add_cursor(img, mx, my, clicking=False):
    d = ImageDraw.Draw(img)
    pts = [(mx,my),(mx,my+17),(mx+4,my+13),(mx+7,my+19),(mx+9,my+18),(mx+7,my+12),(mx+12,my+12)]
    shadow = [(p[0]+1,p[1]+1) for p in pts]
    d.polygon(shadow, fill=(120,120,120))
    d.polygon(pts, fill=WHITE, outline=(30,30,30))
    if clicking:
        for r, alpha in [(12,80),(8,140)]:
            d.ellipse([mx-r, my-r, mx+r, my+r], outline=BLUE, width=2)

# ── Telop overlay ─────────────────────────────────────────────────────────
def add_telop(img, text):
    overlay = Image.new('RGBA', (W, TELOP_H), (0,0,0,200))
    base = img.convert('RGBA')
    base.paste(overlay, (0, CONTENT_H), overlay)
    result = base.convert('RGB')
    d = ImageDraw.Draw(result)
    fnt = F(21)
    tw = TW(text, 21)
    d.text(((W - tw)/2, CONTENT_H + (TELOP_H - 21)//2), text, font=fnt, fill=WHITE)
    return result

# ── Tab geometry helpers ──────────────────────────────────────────────────
TAB_NAMES = ["テキスト", "ファイル", "クリップボード画像"]
_TAB_TXTS = [15, 15, 15]

def tab_rects():
    x = CARD_X
    rects = []
    for name in TAB_NAMES:
        w = int(TW(name, 15)) + 40
        rects.append((x, TABS_Y, x + w, TABBDR))
        x += w + 2
    return rects

def tab_center(idx):
    r = tab_rects()[idx]
    return (r[0]+r[2])//2, (r[1]+r[3])//2

# ── Checkbox helper ───────────────────────────────────────────────────────
def checkbox(d, x, y, checked, label):
    rr(d, [x,y,x+15,y+15], r=3, fill=BLUE if checked else WHITE, ol=BORDER if not checked else None, lw=1)
    if checked:
        d.line([(x+3,y+8),(x+6,y+12),(x+12,y+4)], fill=WHITE, width=2)
    d.text((x+19, y-1), label, font=F(14), fill=DARK)

# ── Category grid ─────────────────────────────────────────────────────────
CATS = ["氏名","組織","住所","日付","電話番号","メール","SNS","特許番号","シリアル番号","型番","金額"]

def draw_cat_box(d, top_y):
    box_h = 88
    rr(d, [INX, top_y, INX+INW, top_y+box_h], r=6, fill=CATBG, ol=BORDER2, lw=1)
    d.text((INX+12, top_y+10), "マスキング対象", font=F(13), fill=MED)
    # Grid: 6 per row, 2 rows
    cols = 6
    col_w = INW // cols
    for i, cat in enumerate(CATS):
        col = i % cols
        row = i // cols
        cx = INX + 12 + col * col_w
        cy = top_y + 30 + row * 24
        checkbox(d, cx, cy, True, cat)
    return top_y + box_h

# ── Button helper ─────────────────────────────────────────────────────────
def btn(d, x, y, label, primary=True, hover=False, disabled=False):
    if disabled:
        bg, fg = (233, 236, 239), (150,150,150)
    elif primary:
        bg, fg = (BLUE_HOV if hover else BLUE), WHITE
    else:
        bg, fg = ((210,215,220) if hover else (233,236,239)), DARK
    w = int(TW(label, 15)) + 40
    rr(d, [x, y, x+w, y+32], r=6, fill=bg)
    d.text((x+20, y+8), label, font=F(15), fill=fg)
    return x + w

# ── Textarea helper ───────────────────────────────────────────────────────
def textarea(d, x, y, w, h, text="", placeholder="", active=False):
    ol = BLUE if active else BORDER
    rr(d, [x, y, x+w, y+h], r=6, fill=WHITE, ol=ol, lw=2 if active else 1)
    if text:
        # Word-wrap simplified: draw lines
        lines = []
        line = ""
        fnt = F(14)
        for ch in text:
            test = line + ch
            if fnt.getlength(test) > w - 20:
                lines.append(line)
                line = ch
            else:
                line = test
        if line:
            lines.append(line)
        for i, ln in enumerate(lines[:6]):
            d.text((x+10, y+10+i*20), ln, font=fnt, fill=DARK)
    elif placeholder:
        d.text((x+10, y+10), placeholder, font=F(14), fill=PHOLDER)
    if active:
        # Text cursor blink
        if text:
            fnt = F(14)
            last_line = lines[-1] if lines else ""
            cx = x + 10 + int(fnt.getlength(last_line))
            row = len(lines) - 1
            d.line([(cx, y+10+row*20), (cx, y+10+row*20+16)], fill=DARK, width=1)

# ── Result box helper ─────────────────────────────────────────────────────
def result_box(d, x, y, w, h, text=""):
    rr(d, [x, y, x+w, y+h], r=6, fill=RES_BG, ol=BORDER2, lw=1)
    if text:
        fnt = F(14)
        lines = []
        line = ""
        for ch in text:
            test = line + ch
            if fnt.getlength(test) > w - 20:
                lines.append(line)
                line = ch
            else:
                line = test
        if line:
            lines.append(line)
        for i, ln in enumerate(lines[:6]):
            d.text((x+10, y+10+i*20), ln, font=fnt, fill=DARK)

# ── Status line helper ────────────────────────────────────────────────────
def status_line(d, x, y, text, ok=True):
    color = STS_OK if ok else STS_ERR
    d.text((x, y), text, font=F(14), fill=color)

# ── Card with shadow ──────────────────────────────────────────────────────
def draw_card(d, top_y, height):
    rr(d, [CARD_X+2, top_y+3, CARD_X+CARD_W+2, top_y+height+3], r=8, fill=SHADOW)
    rr(d, [CARD_X, top_y, CARD_X+CARD_W, top_y+height], r=8, fill=WHITE)

# ── Base UI (header + tabs) ───────────────────────────────────────────────
def make_base(active_tab=0):
    img = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(img)

    # Header
    d.rectangle([0, 0, W, HDR_H], fill=HDR_BG)
    d.text((24, (HDR_H-22)//2), "pymasking — 個人情報マスキングツール", font=F(22), fill=WHITE)
    d.text((4, (HDR_H-22)//2+2), "🔒", font=F(18), fill=WHITE)

    # Background below header
    d.rectangle([0, HDR_H, W, CONTENT_H], fill=BG)

    # Tabs
    for i, (name, rect) in enumerate(zip(TAB_NAMES, tab_rects())):
        x1, y1, x2, y2 = rect
        if i == active_tab:
            d.rounded_rectangle([x1,y1,x2,y2], radius=6, fill=BLUE)
            d.text((x1+20, y1+(TABS_H-15)//2), name, font=F(15), fill=WHITE)
        else:
            d.text((x1+20, y1+(TABS_H-15)//2), name, font=F(15), fill=DARK)

    # Tab bottom border
    d.line([(CARD_X, TABBDR), (W-CARD_X, TABBDR)], fill=BORDER2, width=2)

    return img

# ── Text tab frame ────────────────────────────────────────────────────────
def render_text_tab(state):
    img = make_base(active_tab=0)
    d = ImageDraw.Draw(img)

    card_h = state.get('card_h', 510)
    draw_card(d, CARD_Y, card_h)

    y = INY
    # h2
    d.text((INX, y), "テキストマスキング", font=F(18), fill=HDR_BG)
    y += 34

    # Mode selector + buttons row
    d.text((INX, y), "マスキングの方法", font=F(13), fill=MED)
    y += 18
    rr(d, [INX, y, INX+220, y+32], r=6, fill=WHITE, ol=BORDER, lw=1)
    mode_label = {"blackout":"「●」で塗りつぶす", "unique":"「氏名1」などに置換", "pigpen":"暗号化(元に戻せる)"}
    d.text((INX+10, y+8), mode_label.get(state.get('mode','blackout'),'「●」で塗りつぶす'), font=F(14), fill=DARK)
    d.text((INX+205, y+10), "▼", font=F(12), fill=MED)

    bx = INX + 230
    mask_hover = state.get('mask_btn_hover', False)
    mask_btn_x2 = btn(d, bx, y, "マスキング実行", primary=True, hover=mask_hover)

    unmask_hover = state.get('unmask_btn_hover', False)
    bx2 = mask_btn_x2 + 8
    btn(d, bx2, y, "暗号化解除", primary=False, hover=unmask_hover)

    copy_x = bx2 + int(TW("暗号化解除",15)) + 48
    copy_hover = state.get('copy_btn_hover', False)
    btn(d, copy_x, y, "結果をコピー", primary=False, hover=copy_hover)
    y += 46

    # Category box
    y = draw_cat_box(d, y) + 10

    # Textarea
    d.text((INX, y), "入力テキスト", font=F(13), fill=MED)
    y += 20
    ta_h = 130
    textarea(d, INX, y, INW, ta_h,
             text=state.get('input_text',''),
             placeholder="センシティブ情報を含むテキストをここに入力...",
             active=state.get('textarea_active', False))
    y += ta_h + 6

    # Status
    sts = state.get('status', '')
    if sts:
        status_line(d, INX, y, sts, ok=state.get('status_ok', True))
    y += 20

    # Result box
    res_h = 80
    result_box(d, INX, y, INW, res_h, text=state.get('result', ''))

    return img

# Approximate button positions for text tab (for cursor targeting)
def text_tab_coords():
    y_btn = INY + 34 + 18
    mask_bx = INX + 230
    mask_w = int(TW("マスキング実行", 15)) + 40
    mask_cx = mask_bx + mask_w // 2
    mask_cy = y_btn + 16

    y_ta = INY + 34 + 18 + 46 + 88 + 10 + 20
    ta_cx = INX + INW // 2
    ta_cy = y_ta + 30

    copy_bx = INX + 230 + mask_w + 8 + int(TW("暗号化解除",15)) + 48
    copy_w = int(TW("結果をコピー",15)) + 40
    copy_cx = copy_bx + copy_w // 2
    copy_cy = y_btn + 16

    return {'mask': (mask_cx, mask_cy), 'textarea': (ta_cx, ta_cy), 'copy': (copy_cx, copy_cy)}

# ── File tab frame ────────────────────────────────────────────────────────
def render_file_tab(state):
    img = make_base(active_tab=1)
    d = ImageDraw.Draw(img)

    card_h = 510
    draw_card(d, CARD_Y, card_h)

    y = INY
    d.text((INX, y), "ファイルマスキング", font=F(18), fill=HDR_BG)
    y += 26
    d.text((INX, y), "対応形式: docx / xlsx / pptx / pdf / jpg / png / txt / csv など", font=F(13), fill=MED)
    y += 26

    # Mode selector
    d.text((INX, y), "マスキングの方法", font=F(13), fill=MED)
    y += 18
    rr(d, [INX, y, INX+220, y+32], r=6, fill=WHITE, ol=BORDER, lw=1)
    d.text((INX+10, y+8), "「●」で塗りつぶす", font=F(14), fill=DARK)
    d.text((INX+205, y+10), "▼", font=F(12), fill=MED)
    y += 46

    # Category box
    y = draw_cat_box(d, y) + 10

    # Drop zone
    file_name = state.get('file_name', None)
    drag_over = state.get('drag_over', False)
    dz_h = 78
    dz_bg = BLUE_LIT if drag_over else WHITE
    dz_border = BLUE if drag_over else (170,170,170)
    rr(d, [INX, y, INX+INW, y+dz_h], r=8, fill=dz_bg)
    dashed_rect(d, [INX, y, INX+INW, y+dz_h], color=dz_border, lw=2)

    if file_name:
        label = f"選択済: {file_name}  (256.0 KB)"
        fnt_dz = F(15)
        lw2 = fnt_dz.getlength(label)
        d.text((INX + (INW - lw2)//2, y + (dz_h-15)//2), label, font=fnt_dz, fill=DARK)
    else:
        msg1 = "クリックまたはドラッグ＆ドロップでファイルを選択"
        msg2 = "（最大 50 MB）"
        fnt1 = F(15)
        lw1 = fnt1.getlength(msg1)
        d.text((INX + (INW - lw1)//2, y + 16), msg1, font=fnt1, fill=(136,136,136))
        fnt2 = F(13)
        lw2 = fnt2.getlength(msg2)
        d.text((INX + (INW - lw2)//2, y + 38), msg2, font=fnt2, fill=(136,136,136))

    y += dz_h + 8

    # Status
    sts = state.get('status', '')
    if sts:
        status_line(d, INX, y, sts, ok=state.get('status_ok', True))
    y += 20

    # Buttons
    file_ready = bool(file_name)
    mask_hover = state.get('mask_btn_hover', False)
    btn(d, INX, y, "マスキング実行 → ダウンロード", primary=True,
        hover=mask_hover, disabled=not file_ready)
    bx2 = INX + int(TW("マスキング実行 → ダウンロード",15)) + 48
    btn(d, bx2, y, "暗号化解除 → ダウンロード", primary=False,
        hover=False, disabled=not file_ready)

    return img

def file_tab_coords():
    y_dz = INY + 26 + 26 + 18 + 46 + 88 + 10
    dz_cx = INX + INW // 2
    dz_cy = y_dz + 39

    y_btn = y_dz + 78 + 8 + 20
    mask_w = int(TW("マスキング実行 → ダウンロード", 15)) + 40
    mask_cx = INX + mask_w // 2
    mask_cy = y_btn + 16

    return {'dropzone': (dz_cx, dz_cy), 'mask': (mask_cx, mask_cy)}

# ── Clipboard tab frame ───────────────────────────────────────────────────
def render_clipboard_tab(state):
    img = make_base(active_tab=2)
    d = ImageDraw.Draw(img)

    card_h = 340
    draw_card(d, CARD_Y, card_h)

    y = INY
    d.text((INX, y), "クリップボード画像マスキング", font=F(18), fill=HDR_BG)
    y += 26
    d.text((INX, y), "スクリーンショット等をコピーした後、下のエリアへ Ctrl+V で貼り付けてください。", font=F(13), fill=MED)
    y += 28

    # Paste zone
    pz_h = 130
    pz_focus = state.get('paste_focus', False)
    has_img = state.get('has_image', False)
    pz_border = BLUE if pz_focus else (170,170,170)
    pz_bg = BLUE_LIT if pz_focus else WHITE
    rr(d, [INX, y, INX+INW, y+pz_h], r=8, fill=pz_bg)
    dashed_rect(d, [INX, y, INX+INW, y+pz_h], color=pz_border, lw=2)

    if has_img:
        # Draw fake screenshot thumbnail
        thumb_w, thumb_h = 220, 100
        tx = INX + (INW - thumb_w) // 2
        ty = y + (pz_h - thumb_h) // 2
        rr(d, [tx, ty, tx+thumb_w, ty+thumb_h], r=4, fill=(230,235,240), ol=BORDER, lw=1)
        d.text((tx+10, ty+10), "田中 太郎 様", font=F(13), fill=DARK)
        d.text((tx+10, ty+30), "TEL: 090-●●●●-●●●●", font=F(12), fill=(100,100,100))
        d.text((tx+10, ty+48), "Email: ●●●@example.com", font=F(12), fill=(100,100,100))
        d.text((tx+10, ty+66), "〒 100-●●●● 東京都千代田区", font=F(12), fill=(100,100,100))
        d.text((INX+10, y+4), "貼り付け済み —", font=F(14), fill=DARK)
    elif pz_focus:
        msg = "Ctrl+V で画像を貼り付けてください"
        fnt = F(16)
        lw_ = fnt.getlength(msg)
        d.text((INX + (INW - lw_)//2, y + (pz_h-16)//2), msg, font=fnt, fill=BLUE)
    else:
        msg1 = "ここをクリックして Ctrl+V で画像を貼り付け"
        fnt1 = F(16)
        lw_ = fnt1.getlength(msg1)
        d.text((INX + (INW - lw_)//2, y + (pz_h-16)//2 - 10), msg1, font=fnt1, fill=(136,136,136))

    y += pz_h + 8

    # Status
    sts = state.get('status', '')
    if sts:
        status_line(d, INX, y, sts, ok=state.get('status_ok', True))
    y += 22

    # Button
    enabled = has_img
    mask_hover = state.get('mask_btn_hover', False)
    btn(d, INX, y, "マスキング実行 → ダウンロード", primary=True,
        hover=mask_hover, disabled=not enabled)

    return img

def clipboard_tab_coords():
    y_pz = INY + 26 + 28
    pz_cx = INX + INW // 2
    pz_cy = y_pz + 65

    y_btn = y_pz + 130 + 8 + 22
    mask_w = int(TW("マスキング実行 → ダウンロード", 15)) + 40
    mask_cx = INX + mask_w // 2
    mask_cy = y_btn + 16

    return {'pastezone': (pz_cx, pz_cy), 'mask': (mask_cx, mask_cy)}

# ── Animation helpers ─────────────────────────────────────────────────────
def ease(t):
    return t * t * (3 - 2 * t)

def move_mouse(frames, p0, p1, n=12, state_fn=None, telop="", clicking_last=False):
    """Generate n frames moving mouse from p0 to p1."""
    result = []
    for i in range(n):
        t = ease(i / max(n-1, 1))
        mx = int(p0[0] + (p1[0]-p0[0])*t)
        my = int(p0[1] + (p1[1]-p0[1])*t)
        clicking = clicking_last and (i == n-1)
        img = state_fn()
        img = add_telop(img, telop)
        add_cursor(img, mx, my, clicking)
        result.append((img, 80))
    return result

def hold(state_fn, telop, ms, cursor_pos, clicking=False):
    """Hold a frame for ms milliseconds (GIF frame count)."""
    n = max(1, ms // 80)
    result = []
    for i in range(n):
        img = state_fn()
        img = add_telop(img, telop)
        add_cursor(img, cursor_pos[0], cursor_pos[1], clicking and i < 2)
        result.append((img, 80))
    return result

def save_gif(frames, path, loop=0):
    images = [f[0] for f in frames]
    durations = [f[1] for f in frames]
    images[0].save(
        path, format='GIF', save_all=True,
        append_images=images[1:],
        duration=durations, loop=loop, optimize=True,
    )
    print(f"Saved: {path}  ({len(images)} frames)")

# ── GIF 1: テキストタブ ───────────────────────────────────────────────────
def gen_text_gif(out_path):
    coords = text_tab_coords()
    START = (450, 400)

    INPUT_TEXT = "田中太郎さんの電話番号は 090-1234-5678 で、メールは tanaka@example.com です。"
    MASKED     = "●●●さんの電話番号は ●●●-●●●●-●●●● で、メールは ●●●@●●●●●●●.●●● です。"

    def st_init():
        return render_text_tab({'input_text': '', 'textarea_active': False})

    def st_typing(text=''):
        return render_text_tab({'input_text': text, 'textarea_active': True})

    def st_hover():
        return render_text_tab({'input_text': INPUT_TEXT, 'mask_btn_hover': True})

    def st_processing():
        return render_text_tab({'input_text': INPUT_TEXT, 'status': '処理中...', 'status_ok': True})

    def st_done():
        return render_text_tab({'input_text': INPUT_TEXT, 'result': MASKED,
                                 'status': '✓ 完了', 'status_ok': True})

    def st_copy_hover():
        return render_text_tab({'input_text': INPUT_TEXT, 'result': MASKED,
                                 'status': '✓ 完了', 'status_ok': True,
                                 'copy_btn_hover': True})

    frames = []

    # 1. 初期表示
    frames += hold(st_init, "テキストタブを開きます", 1600, START)

    # 2. テキストエリアへ移動
    frames += move_mouse(frames, START, coords['textarea'],
                         state_fn=st_init, telop="個人情報を含むテキストを入力します")

    # 3. テキスト入力アニメーション（段階的に表示）
    ta_pos = coords['textarea']
    for step in range(0, len(INPUT_TEXT)+1, max(1, len(INPUT_TEXT)//10)):
        partial = INPUT_TEXT[:step]
        frames.append((add_telop(render_text_tab({'input_text': partial, 'textarea_active': True}),
                                  "個人情報を含むテキストを入力します"), 120))
    frames += hold(lambda: st_typing(INPUT_TEXT), "田中太郎さんの連絡先情報を入力しました", 1400, ta_pos)

    # 4. マスキング実行ボタンへ
    frames += move_mouse(frames, ta_pos, coords['mask'],
                         state_fn=lambda: st_typing(INPUT_TEXT),
                         telop="「マスキング実行」をクリックします")

    frames += hold(st_hover, "「マスキング実行」をクリックします", 600, coords['mask'])

    # 5. クリック
    frames += hold(lambda: render_text_tab({'input_text': INPUT_TEXT, 'mask_btn_hover': True}),
                   "処理中...", 300, coords['mask'], clicking=True)
    frames += hold(st_processing, "処理中...", 800, coords['mask'])

    # 6. 結果表示
    frames += hold(st_done, "個人情報が「●●●」に置換されました！", 2400, coords['mask'])

    # 7. コピーボタンへ
    frames += move_mouse(frames, coords['mask'], coords['copy'],
                         state_fn=st_done, telop="「結果をコピー」で結果を取得できます")
    frames += hold(st_copy_hover, "「結果をコピー」で結果を取得できます", 1800, coords['copy'])

    save_gif(frames, out_path)

# ── GIF 2: ファイルタブ ───────────────────────────────────────────────────
def gen_file_gif(out_path):
    tc = tab_center(1)
    fc = file_tab_coords()
    START = (450, 300)

    def st_text_init():
        return render_text_tab({'input_text': ''})

    def st_file_init():
        return render_file_tab({})

    def st_drag_over():
        return render_file_tab({'drag_over': True})

    def st_file_selected():
        return render_file_tab({'file_name': 'report.docx'})

    def st_hover():
        return render_file_tab({'file_name': 'report.docx', 'mask_btn_hover': True})

    def st_processing():
        return render_file_tab({'file_name': 'report.docx',
                                 'status': '処理中...', 'status_ok': True})

    def st_done():
        return render_file_tab({'file_name': 'report.docx',
                                 'status': '✓ ダウンロード開始', 'status_ok': True})

    frames = []

    frames += hold(st_text_init, "ファイルタブでファイルをマスキングできます", 1200, START)

    frames += move_mouse(frames, START, tc,
                         state_fn=st_text_init, telop="「ファイル」タブをクリックします")
    frames += hold(st_text_init, "「ファイル」タブをクリックします", 400, tc)
    frames += hold(st_file_init, "ファイルタブが開きました", 1200, tc)

    frames += move_mouse(frames, tc, fc['dropzone'],
                         state_fn=st_file_init, telop="ファイルをドラッグ＆ドロップできます")
    frames += hold(st_drag_over, "ファイルをドラッグ＆ドロップ、またはクリックで選択", 800, fc['dropzone'])

    frames += hold(st_file_selected, "report.docx を選択しました", 1600, fc['dropzone'])

    frames += move_mouse(frames, fc['dropzone'], fc['mask'],
                         state_fn=st_file_selected, telop="「マスキング実行→ダウンロード」をクリックします")
    frames += hold(st_hover, "「マスキング実行→ダウンロード」をクリックします", 600, fc['mask'])

    frames += hold(lambda: render_file_tab({'file_name':'report.docx','mask_btn_hover':True}),
                   "処理中...", 400, fc['mask'], clicking=True)
    frames += hold(st_processing, "処理中...", 800, fc['mask'])

    frames += hold(st_done, "マスク済みファイルのダウンロードが始まりました！", 2400, fc['mask'])

    save_gif(frames, out_path)

# ── GIF 3: クリップボードタブ ─────────────────────────────────────────────
def gen_clipboard_gif(out_path):
    tc = tab_center(2)
    cc = clipboard_tab_coords()
    START = (450, 300)

    def st_text_init():
        return render_text_tab({'input_text': ''})

    def st_clip_init():
        return render_clipboard_tab({})

    def st_clip_focus():
        return render_clipboard_tab({'paste_focus': True})

    def st_img_pasted():
        return render_clipboard_tab({'has_image': True, 'paste_focus': False,
                                      'status': '画像を取得しました', 'status_ok': True})

    def st_hover():
        return render_clipboard_tab({'has_image': True, 'mask_btn_hover': True,
                                      'status': '画像を取得しました', 'status_ok': True})

    def st_processing():
        return render_clipboard_tab({'has_image': True,
                                      'status': '処理中...', 'status_ok': True})

    def st_done():
        return render_clipboard_tab({'has_image': True,
                                      'status': '✓ ダウンロード開始', 'status_ok': True})

    frames = []

    frames += hold(st_text_init, "クリップボード画像タブでスクリーンショットをマスキング", 1200, START)

    frames += move_mouse(frames, START, tc,
                         state_fn=st_text_init, telop="「クリップボード画像」タブをクリックします")
    frames += hold(st_text_init, "「クリップボード画像」タブをクリックします", 400, tc)
    frames += hold(st_clip_init, "クリップボード画像タブが開きました", 1200, tc)

    frames += move_mouse(frames, tc, cc['pastezone'],
                         state_fn=st_clip_init, telop="貼り付けエリアをクリックしてフォーカスします")
    frames += hold(st_clip_init, "貼り付けエリアをクリックしてフォーカスします", 400, cc['pastezone'], clicking=True)
    frames += hold(st_clip_focus, "Ctrl+V でスクリーンショットを貼り付けます", 1600, cc['pastezone'])

    frames += hold(st_img_pasted, "スクリーンショットが貼り付けられました！", 1800, cc['pastezone'])

    frames += move_mouse(frames, cc['pastezone'], cc['mask'],
                         state_fn=st_img_pasted, telop="「マスキング実行→ダウンロード」をクリックします")
    frames += hold(st_hover, "「マスキング実行→ダウンロード」をクリックします", 600, cc['mask'])

    frames += hold(lambda: render_clipboard_tab({'has_image':True,'mask_btn_hover':True,
                                                  'status':'画像を取得しました','status_ok':True}),
                   "処理中...", 400, cc['mask'], clicking=True)
    frames += hold(st_processing, "処理中...", 800, cc['mask'])

    frames += hold(st_done, "マスク済み画像のダウンロードが始まりました！", 2400, cc['mask'])

    save_gif(frames, out_path)

# ── Main ──────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    out_dir = os.path.join(os.path.dirname(__file__), '..', 'doc')
    os.makedirs(out_dir, exist_ok=True)

    print("Generating GIFs...")
    gen_text_gif(os.path.join(out_dir, 'demo_text.gif'))
    gen_file_gif(os.path.join(out_dir, 'demo_file.gif'))
    gen_clipboard_gif(os.path.join(out_dir, 'demo_clipboard.gif'))
    print("Done!")
