#!/usr/bin/env python3
"""Generate animated demo GIFs for pymasking web UI documentation."""

from PIL import Image, ImageDraw, ImageFont
import os, math

# ── Constants ─────────────────────────────────────────────────────────────
W, H      = 900, 700
TELOP_H   = 64
CONTENT_H = H - TELOP_H

BG        = (244, 246, 248)
HDR_BG    = ( 26,  26,  46)
WHITE     = (255, 255, 255)
DARK      = ( 51,  51,  51)
MED       = ( 85,  85,  85)
BLUE      = ( 67,  97, 238)
BLUE_LIT  = (238, 242, 255)
BORDER    = (200, 212, 220)
BORDER2   = (222, 226, 230)
SHADOW    = (215, 218, 222)
CATBG     = (248, 249, 250)
PHOLDER   = (175, 175, 175)
STS_OK    = ( 45, 106,  79)
RES_BG    = (248, 249, 250)
PURPLE    = (114,   9, 183)
ORANGE    = (244, 162,  97)
RED       = (230,  57,  70)
BTN_GRAY  = (233, 236, 239)

HDR_H   = 58
TABS_Y  = HDR_H + 20
TABS_H  = 36
TABBDR  = TABS_Y + TABS_H
CARD_Y  = TABBDR + 14
CARD_X  = 16
CARD_W  = W - 32
CP      = 22
INX     = CARD_X + CP
INY     = CARD_Y + CP
INW     = CARD_W - 2 * CP

JP  = "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf"
_fc = {}

def F(size):
    if size not in _fc:
        try:    _fc[size] = ImageFont.truetype(JP, size)
        except: _fc[size] = ImageFont.load_default()
    return _fc[size]

def TW(text, size=15):
    return F(size).getlength(text)

def rr(draw, xy, r=6, fill=None, ol=None, lw=1):
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle([x1,y1,x2,y2], radius=r, fill=fill, outline=ol, width=lw)

def dashed_rect(draw, xy, color=(150,150,150), lw=2, dash=8, gap=5):
    x1, y1, x2, y2 = xy
    for sx,sy,ex,ey in [(x1,y1,x2,y1),(x2,y1,x2,y2),(x2,y2,x1,y2),(x1,y2,x1,y1)]:
        length = math.hypot(ex-sx, ey-sy)
        if length == 0: continue
        dx, dy = (ex-sx)/length, (ey-sy)/length
        pos, drawing = 0.0, True
        while pos < length:
            seg = dash if drawing else gap
            end = min(pos+seg, length)
            if drawing:
                draw.line([(sx+pos*dx,sy+pos*dy),(sx+end*dx,sy+end*dy)], fill=color, width=lw)
            pos, drawing = end, not drawing

def add_cursor(img, mx, my, clicking=False):
    d = ImageDraw.Draw(img)
    pts = [(mx,my),(mx,my+17),(mx+4,my+13),(mx+7,my+19),(mx+9,my+18),(mx+7,my+12),(mx+12,my+12)]
    d.polygon([(p[0]+1,p[1]+1) for p in pts], fill=(120,120,120))
    d.polygon(pts, fill=WHITE, outline=(30,30,30))
    if clicking:
        for r in [12, 8]:
            d.ellipse([mx-r, my-r, mx+r, my+r], outline=BLUE, width=2)

def add_telop(img, text):
    overlay = Image.new('RGBA', (W, TELOP_H), (0,0,0,200))
    base = img.convert('RGBA')
    base.paste(overlay, (0, CONTENT_H), overlay)
    result = base.convert('RGB')
    d = ImageDraw.Draw(result)
    tw = TW(text, 21)
    d.text(((W-tw)/2, CONTENT_H+(TELOP_H-21)//2), text, font=F(21), fill=WHITE)
    return result

TAB_NAMES = ["テキスト", "ファイル", "クリップボード画像"]

def tab_rects():
    x = CARD_X
    rects = []
    for name in TAB_NAMES:
        w = int(TW(name, 15)) + 40
        rects.append((x, TABS_Y, x+w, TABBDR))
        x += w + 2
    return rects

def tab_center(idx):
    r = tab_rects()[idx]
    return (r[0]+r[2])//2, (r[1]+r[3])//2

def checkbox(d, x, y, checked, label, grey=False):
    fg = (180,180,180) if grey else (DARK if not checked else None)
    rr(d, [x,y,x+15,y+15], r=3, fill=(200,200,200) if grey else (BLUE if checked else WHITE),
       ol=(210,210,210) if grey else (BORDER if not checked else None), lw=1)
    if checked and not grey:
        d.line([(x+3,y+8),(x+6,y+12),(x+12,y+4)], fill=WHITE, width=2)
    d.text((x+19, y-1), label, font=F(14), fill=(180,180,180) if grey else DARK)

CATS = ["氏名","組織","住所","日付","電話番号","メール","SNS","特許番号","シリアル番号","型番","金額"]

def draw_cat_box(d, top_y, greyed=False):
    box_h = 88
    rr(d, [INX,top_y,INX+INW,top_y+box_h], r=6, fill=CATBG, ol=BORDER2, lw=1)
    d.text((INX+12, top_y+10), "マスキング対象", font=F(13), fill=(180,180,180) if greyed else MED)
    cols = 6
    col_w = INW // cols
    for i, cat in enumerate(CATS):
        col, row = i % cols, i // cols
        cx = INX + 12 + col * col_w
        cy = top_y + 30 + row * 24
        checkbox(d, cx, cy, True, cat, grey=greyed)
    return top_y + box_h

def draw_card(d, top_y, height):
    rr(d, [CARD_X+2,top_y+3,CARD_X+CARD_W+2,top_y+height+3], r=8, fill=SHADOW)
    rr(d, [CARD_X,top_y,CARD_X+CARD_W,top_y+height], r=8, fill=WHITE)

def make_base(active_tab=0):
    img = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0,0,W,HDR_H], fill=HDR_BG)
    d.text((24,(HDR_H-22)//2), "pymasking — 個人情報マスキングツール", font=F(22), fill=WHITE)
    d.rectangle([0,HDR_H,W,CONTENT_H], fill=BG)
    for i, (name, rect) in enumerate(zip(TAB_NAMES, tab_rects())):
        x1,y1,x2,y2 = rect
        if i == active_tab:
            d.rounded_rectangle([x1,y1,x2,y2], radius=6, fill=BLUE)
            d.text((x1+20,y1+(TABS_H-15)//2), name, font=F(15), fill=WHITE)
        else:
            d.text((x1+20,y1+(TABS_H-15)//2), name, font=F(15), fill=DARK)
    d.line([(CARD_X,TABBDR),(W-CARD_X,TABBDR)], fill=BORDER2, width=2)
    return img

# ── Method bar + Example box + Buttons + Progress ────────────────────────
METHOD_LABELS = [
    ('blackout', '伏字（●）'),
    ('unique',   '一意性保持'),
    ('pigpen',   'ピッグペン暗号'),
    ('decrypt',  '復号化'),
]

EXAMPLES = {
    'blackout': '田中太郎さんの電話番号 090-1234-5678  →  ●●●さんの電話番号 ●●●-●●●●-●●●●',
    'unique':   '田中太郎さんの電話番号 090-1234-5678  →  人物001さんの電話番号 電話001',
    'pigpen':   '田中太郎  →  【人物:⊞⊟⊠⊡⊢⊣⊤⊥:】',
    'decrypt':  '【人物:⊞⊟⊠⊡⊢⊣⊤⊥:】  →  田中太郎',
}

def draw_method_bar(d, y, selected='blackout'):
    d.text((INX, y), "マスキングの方法", font=F(13), fill=MED)
    y += 18
    centers = {}
    x = INX
    for mode, label in METHOD_LABELS:
        w = int(TW(label, 14)) + 36
        if mode == selected:
            bg = PURPLE if mode == 'decrypt' else HDR_BG
            fg, ol = WHITE, bg
        else:
            bg, fg, ol = BTN_GRAY, MED, None
        rr(d, [x,y,x+w,y+32], r=6, fill=bg, ol=ol, lw=2)
        d.text((x+18, y+8), label, font=F(14), fill=fg)
        centers[mode] = (x + w//2, y + 16)
        x += w + 8
    return y + 32 + 10, centers

def draw_example_box(d, y, mode='blackout'):
    box_h = 50
    rr(d, [INX,y,INX+INW,y+box_h], r=6, fill=(240,244,255), ol=(197,208,245), lw=1)
    d.text((INX+12, y+8),  "例)", font=F(12), fill=(136,136,136))
    d.text((INX+12, y+24), EXAMPLES[mode], font=F(13), fill=DARK)
    return y + box_h + 14

def draw_btn(d, x, y, label, state='normal', disabled=False, secondary=False):
    fnt = F(14)
    bw = int(fnt.getlength(label)) + 36
    if disabled:
        bg, fg = BTN_GRAY, (150,150,150)
    elif state == 'running':
        bg, fg = RED, WHITE
    elif state == 'download':
        bg, fg = ORANGE, WHITE
    elif secondary:
        bg, fg = PURPLE, WHITE
    else:
        bg, fg = BLUE, WHITE
    rr(d, [x,y,x+bw,y+32], r=6, fill=bg)
    tx = x + (bw - int(fnt.getlength(label))) // 2
    d.text((tx, y+8), label, font=fnt, fill=fg)
    return x + bw

def draw_progress(d, y, pct=0, text=''):
    rr(d, [INX,y,INX+INW,y+8], r=4, fill=(233,236,239))
    if pct > 0:
        done_color = ORANGE if pct >= 100 else BLUE
        rr(d, [INX,y,INX+int(INW*pct/100),y+8], r=4, fill=done_color)
    d.text((INX, y+12), text, font=F(12), fill=(102,102,102))
    return y + 28

def textarea_widget(d, x, y, w, h, text='', placeholder='', active=False):
    rr(d, [x,y,x+w,y+h], r=6, fill=WHITE, ol=BLUE if active else BORDER,
       lw=2 if active else 1)
    if text:
        lines, line = [], ''
        for ch in text:
            test = line + ch
            if F(14).getlength(test) > w-20:
                lines.append(line); line = ch
            else: line = test
        if line: lines.append(line)
        for i, ln in enumerate(lines[:5]):
            d.text((x+10, y+10+i*20), ln, font=F(14), fill=DARK)
    elif placeholder:
        d.text((x+10, y+10), placeholder, font=F(14), fill=PHOLDER)

def result_box_widget(d, x, y, w, h, text=''):
    rr(d, [x,y,x+w,y+h], r=6, fill=RES_BG, ol=BORDER2, lw=1)
    if text:
        lines, line = [], ''
        for ch in text:
            test = line + ch
            if F(14).getlength(test) > w-20:
                lines.append(line); line = ch
            else: line = test
        if line: lines.append(line)
        for i, ln in enumerate(lines[:4]):
            d.text((x+10, y+10+i*20), ln, font=F(14), fill=DARK)

# ── Render functions ──────────────────────────────────────────────────────
def render_text_tab(state):
    img = make_base(active_tab=0)
    d = ImageDraw.Draw(img)
    mode = state.get('mode', 'blackout')
    draw_card(d, CARD_Y, 500)

    y = INY
    d.text((INX, y), "テキストマスキング", font=F(18), fill=HDR_BG)
    y += 34

    y, method_centers = draw_method_bar(d, y, selected=mode)
    y = draw_example_box(d, y, mode=mode)

    d.text((INX, y), "入力テキスト（Ctrl+V でも貼り付け可能）", font=F(13), fill=MED)
    y += 18
    ta_h = 100
    textarea_widget(d, INX, y, INW, ta_h,
                    text=state.get('input_text', ''),
                    placeholder='センシティブ情報を含むテキストをここに入力...',
                    active=state.get('textarea_active', False))
    y += ta_h + 10

    greyed = (mode == 'decrypt')
    y = draw_cat_box(d, y, greyed=greyed) + 14

    x2 = draw_btn(d, INX, y, 'マスキング実行')
    draw_btn(d, x2+10, y, '復号化実行', secondary=True)
    y += 32 + 10

    result = state.get('result', '')
    if result:
        result_box_widget(d, INX, y, INW, 60, text=result)
        y += 60 + 8
        draw_btn(d, INX, y, '結果をコピー')

    return img

def render_file_tab(state):
    img = make_base(active_tab=1)
    d = ImageDraw.Draw(img)
    draw_card(d, CARD_Y, 520)

    y = INY
    d.text((INX, y), "ファイルマスキング", font=F(18), fill=HDR_BG)
    y += 34

    y, _ = draw_method_bar(d, y, selected='blackout')
    y = draw_example_box(d, y, mode='blackout')

    drag = state.get('drag_over', False)
    file_name = state.get('file_name')
    dz_h = 80
    rr(d, [INX,y,INX+INW,y+dz_h], r=8, fill=BLUE_LIT if drag else WHITE)
    dashed_rect(d, [INX,y,INX+INW,y+dz_h], color=BLUE if drag else (170,170,170), lw=2)
    if file_name:
        msg = f"選択済: {file_name}  (256.0 KB)"
        lw2 = F(15).getlength(msg)
        d.text((INX+(INW-lw2)//2, y+(dz_h-15)//2), msg, font=F(15), fill=DARK)
    else:
        msg1 = "クリックまたはドラッグ＆ドロップでファイルを選択"
        msg2 = "対応形式: docx / xlsx / pptx / pdf / jpg / png / txt / csv など（最大 50 MB）"
        d.text((INX+(INW-F(15).getlength(msg1))//2, y+14), msg1, font=F(15), fill=(136,136,136))
        d.text((INX+(INW-F(12).getlength(msg2))//2, y+36), msg2, font=F(12), fill=(170,170,170))
    y += dz_h + 14

    y = draw_cat_box(d, y) + 14

    opts_h = 54
    rr(d, [INX,y,INX+INW,y+opts_h], r=6, fill=CATBG, ol=BORDER2, lw=1)
    d.text((INX+12, y+8), "追加オプション", font=F(13), fill=MED)
    checkbox(d, INX+12, y+26, True, "Word: ヘッダー・フッターを削除")
    y += opts_h + 14

    file_ready = bool(file_name)
    btn_state = state.get('btn_state', 'normal')
    mask_lbl = state.get('mask_label', 'マスキング実行')
    x2 = draw_btn(d, INX, y, mask_lbl,
                  state=btn_state if file_ready else 'normal',
                  disabled=not file_ready)
    draw_btn(d, x2+10, y, '復号化実行', secondary=True, disabled=not file_ready)
    y += 32 + 12

    pct = state.get('pct', 0)
    ptxt = state.get('ptext', '')
    if pct > 0 or ptxt:
        draw_progress(d, y, pct=pct, text=ptxt)

    return img

def render_clipboard_tab(state):
    img = make_base(active_tab=2)
    d = ImageDraw.Draw(img)
    draw_card(d, CARD_Y, 360)

    y = INY
    d.text((INX, y), "クリップボード画像マスキング", font=F(18), fill=HDR_BG)
    y += 30
    d.text((INX, y), "スクリーンショット等をコピーした後、下のエリアへ Ctrl+V で貼り付けてください。", font=F(13), fill=MED)
    y += 20
    d.text((INX, y), "画像内の文字を OCR で検出して黒塗りマスキングします。", font=F(13), fill=MED)
    y += 26

    pz_h = 148
    focus = state.get('paste_focus', False)
    has_img = state.get('has_image', False)
    rr(d, [INX,y,INX+INW,y+pz_h], r=8, fill=BLUE_LIT if focus else WHITE)
    dashed_rect(d, [INX,y,INX+INW,y+pz_h], color=BLUE if focus else (170,170,170), lw=2)
    if has_img:
        tw, th = 240, 110
        tx, ty2 = INX+(INW-tw)//2, y+(pz_h-th)//2
        rr(d, [tx,ty2,tx+tw,ty2+th], r=4, fill=(230,235,240), ol=BORDER, lw=1)
        d.text((tx+10, ty2+8),  "田中 太郎 様",                 font=F(13), fill=DARK)
        d.text((tx+10, ty2+28), "TEL: 090-●●●●-●●●●",         font=F(12), fill=(100,100,100))
        d.text((tx+10, ty2+46), "Email: ●●●@example.com",      font=F(12), fill=(100,100,100))
        d.text((tx+10, ty2+64), "〒 100-●●●● 東京都千代田区",   font=F(12), fill=(100,100,100))
        d.text((INX+10, y+4),   "貼り付け済み",                 font=F(14), fill=DARK)
    elif focus:
        msg = "Ctrl+V で画像を貼り付けてください"
        d.text((INX+(INW-F(16).getlength(msg))//2, y+(pz_h-16)//2), msg, font=F(16), fill=BLUE)
    else:
        msg = "ここをクリックして Ctrl+V で画像を貼り付け"
        d.text((INX+(INW-F(16).getlength(msg))//2, y+(pz_h-16)//2), msg, font=F(16), fill=(136,136,136))
    y += pz_h + 14

    file_ready = has_img
    btn_state = state.get('btn_state', 'normal')
    mask_lbl = state.get('mask_label', 'マスキング実行')
    draw_btn(d, INX, y, mask_lbl, state=btn_state if file_ready else 'normal',
             disabled=not file_ready)
    y += 32 + 12

    pct = state.get('pct', 0)
    ptxt = state.get('ptext', '')
    if pct > 0 or ptxt:
        draw_progress(d, y, pct=pct, text=ptxt)

    return img

# ── Layout coordinate helpers ──────────────────────────────────────────────
def _method_bar_centers(y_start):
    y = y_start + 18
    x = INX
    centers = {}
    for mode, label in METHOD_LABELS:
        w = int(TW(label, 14)) + 36
        centers[mode] = (x + w//2, y + 16)
        x += w + 8
    return centers

def text_tab_coords():
    y = INY + 34
    mb_centers = _method_bar_centers(y)
    y += 18 + 32 + 10   # method label + bar + gap
    y += 50 + 14        # example box + gap
    y += 18             # textarea label
    y_ta = y
    ta_h = 100
    y += ta_h + 10 + 88 + 14   # textarea + gap + cat_box + gap
    y_btn = y
    mask_w = int(TW('マスキング実行', 14)) + 36
    y_result = y_btn + 32 + 10
    copy_w = int(TW('結果をコピー', 14)) + 36
    return {
        'mask':     (INX + mask_w//2,  y_btn + 16),
        'textarea': (INX + INW//2,     y_ta + ta_h//2),
        'copy':     (INX + copy_w//2,  y_result + 60 + 8 + 16),
        'method':   mb_centers,
    }

def file_tab_coords():
    y = INY + 34
    y += 18 + 32 + 10   # method
    y += 50 + 14        # example
    y_dz = y
    dz_h = 80
    y += dz_h + 14 + 88 + 14   # drop + gap + cat + gap
    y += 54 + 14                # options + gap
    y_btn = y
    mask_w = int(TW('マスキング実行', 14)) + 36
    return {
        'dropzone': (INX + INW//2, y_dz + dz_h//2),
        'mask':     (INX + mask_w//2, y_btn + 16),
    }

def clipboard_tab_coords():
    y = INY + 30 + 20 + 26
    y_pz = y
    pz_h = 148
    y += pz_h + 14
    y_btn = y
    mask_w = int(TW('マスキング実行', 14)) + 36
    return {
        'pastezone': (INX + INW//2, y_pz + pz_h//2),
        'mask':      (INX + mask_w//2, y_btn + 16),
    }

# ── Animation helpers ─────────────────────────────────────────────────────
def ease(t):
    return t * t * (3 - 2*t)

def move_mouse(frames, p0, p1, n=12, state_fn=None, telop='', clicking_last=False):
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
    images[0].save(path, format='GIF', save_all=True,
                   append_images=images[1:], duration=durations, loop=loop, optimize=True)
    print(f"Saved: {path}  ({len(images)} frames)")

# ── GIF 1: テキストタブ ───────────────────────────────────────────────────
def gen_text_gif(out_path):
    coords = text_tab_coords()
    START = (450, 400)
    INPUT_TEXT = "田中太郎さんの電話番号は 090-1234-5678 で、メールは tanaka@example.com です。"
    MASKED     = "●●●さんの電話番号は ●●●-●●●●-●●●● で、メールは ●●●@●●●●●●●.●●● です。"

    def st_init():
        return render_text_tab({'mode': 'blackout'})
    def st_typing(text=''):
        return render_text_tab({'mode': 'blackout', 'input_text': text, 'textarea_active': True})
    def st_pigpen():
        return render_text_tab({'mode': 'pigpen'})
    def st_back():
        return render_text_tab({'mode': 'blackout', 'input_text': INPUT_TEXT})
    def st_done():
        return render_text_tab({'mode': 'blackout', 'input_text': INPUT_TEXT, 'result': MASKED})

    frames = []
    frames += hold(st_init, "テキストタブを開きます", 1200, START)

    # テキストエリアへ移動してテキスト入力
    frames += move_mouse(frames, START, coords['textarea'],
                         state_fn=st_init, telop="個人情報を含むテキストを入力します")
    ta_pos = coords['textarea']
    for step in range(0, len(INPUT_TEXT)+1, max(1, len(INPUT_TEXT)//12)):
        frames.append((add_telop(render_text_tab({'mode':'blackout','input_text':INPUT_TEXT[:step],'textarea_active':True}),
                                  "センシティブ情報を含むテキストを入力"), 100))
    frames += hold(lambda: st_typing(INPUT_TEXT), "テキスト入力完了", 800, ta_pos)

    # マスキング実行ボタンへ
    frames += move_mouse(frames, ta_pos, coords['mask'],
                         state_fn=lambda: st_typing(INPUT_TEXT),
                         telop="「マスキング実行」をクリックします")
    frames += hold(st_back, "「マスキング実行」をクリックします", 400, coords['mask'])
    frames += hold(lambda: render_text_tab({'mode':'blackout','input_text':INPUT_TEXT}),
                   "処理中...", 300, coords['mask'], clicking=True)
    frames += hold(st_done, "個人情報が「●●●」に置換されました！", 2400, coords['mask'])

    # 結果をコピー
    frames += move_mouse(frames, coords['mask'], coords['copy'],
                         state_fn=st_done, telop="「結果をコピー」で結果を取得できます")
    frames += hold(st_done, "「結果をコピー」で結果を取得できます", 1600, coords['copy'])

    save_gif(frames, out_path)

# ── GIF 2: ファイルタブ ───────────────────────────────────────────────────
def gen_file_gif(out_path):
    tc = tab_center(1)
    fc = file_tab_coords()
    START = (450, 300)

    PROGRESS_STEPS = [(10,'ファイルを読み込み中…'),(30,'テキストを解析中…'),
                      (55,'個人情報を検出中…'),(75,'マスキングを適用中…'),
                      (90,'ファイルを生成中…'),(100,'完了')]

    def st_text():
        return render_text_tab({'mode': 'blackout'})
    def st_file_empty():
        return render_file_tab({})
    def st_drag():
        return render_file_tab({'drag_over': True})
    def st_selected():
        return render_file_tab({'file_name': 'report.docx'})

    frames = []
    frames += hold(st_text, "ファイルタブでファイルをマスキングできます", 1000, START)

    frames += move_mouse(frames, START, tc, state_fn=st_text, telop="「ファイル」タブをクリックします")
    frames += hold(st_text, "「ファイル」タブをクリックします", 300, tc)
    frames += hold(st_file_empty, "ファイルタブが開きました", 1000, tc)

    frames += move_mouse(frames, tc, fc['dropzone'],
                         state_fn=st_file_empty, telop="ファイルをドロップエリアへ")
    frames += hold(st_drag, "report.docx をドラッグ＆ドロップします", 600, fc['dropzone'])
    frames += hold(st_selected, "report.docx を選択しました", 1200, fc['dropzone'])

    frames += move_mouse(frames, fc['dropzone'], fc['mask'],
                         state_fn=st_selected, telop="「マスキング実行」をクリックします")
    frames += hold(st_selected, "「マスキング実行」をクリックします", 400, fc['mask'])

    # 実行中フレーム（赤点滅シミュレート：2フレーム交互）
    for _ in range(4):
        for alpha in [1.0, 0.4]:
            s = {'file_name':'report.docx','btn_state':'running','mask_label':'実行中',
                 'pct':0,'ptext':'処理中...'}
            img = render_file_tab(s)
            if alpha < 1.0:
                overlay = Image.new('RGB', (W,H), WHITE)
                img = Image.blend(img, overlay, 0.3)
            img = add_telop(img, "処理中...")
            add_cursor(img, fc['mask'][0], fc['mask'][1])
            frames.append((img, 120))

    # プログレス
    for pct, txt in PROGRESS_STEPS:
        s = {'file_name':'report.docx','btn_state':'running','mask_label':'実行中',
             'pct':pct,'ptext':txt}
        img = render_file_tab(s)
        img = add_telop(img, "処理中...")
        add_cursor(img, fc['mask'][0], fc['mask'][1])
        frames.append((img, 300))

    # ダウンロード状態
    def st_dl():
        return render_file_tab({'file_name':'report.docx','btn_state':'download',
                                'mask_label':'ダウンロード','pct':100,'ptext':'完了'})
    frames += hold(st_dl, "マスク済みファイルをダウンロードできます！", 2400, fc['mask'])

    save_gif(frames, out_path)

# ── GIF 3: クリップボードタブ ─────────────────────────────────────────────
def gen_clipboard_gif(out_path):
    tc = tab_center(2)
    cc = clipboard_tab_coords()
    START = (450, 300)

    PROGRESS_STEPS = [(10,'画像を読み込み中…'),(35,'OCR でテキストを認識中…'),
                      (65,'個人情報を検出中…'),(85,'黒塗りマスキングを適用中…'),(100,'完了')]

    def st_text():
        return render_text_tab({'mode': 'blackout'})
    def st_clip_empty():
        return render_clipboard_tab({})
    def st_clip_focus():
        return render_clipboard_tab({'paste_focus': True})
    def st_img_pasted():
        return render_clipboard_tab({'has_image': True})

    frames = []
    frames += hold(st_text, "クリップボード画像タブでスクリーンショットをマスキング", 1000, START)

    frames += move_mouse(frames, START, tc, state_fn=st_text,
                         telop="「クリップボード画像」タブをクリックします")
    frames += hold(st_text, "「クリップボード画像」タブをクリックします", 300, tc)
    frames += hold(st_clip_empty, "クリップボード画像タブが開きました", 1000, tc)

    frames += move_mouse(frames, tc, cc['pastezone'], state_fn=st_clip_empty,
                         telop="貼り付けエリアをクリックします")
    frames += hold(st_clip_empty, "貼り付けエリアをクリックします", 300, cc['pastezone'], clicking=True)
    frames += hold(st_clip_focus, "Ctrl+V でスクリーンショットを貼り付けます", 1400, cc['pastezone'])
    frames += hold(st_img_pasted, "スクリーンショットが貼り付けられました！", 1600, cc['pastezone'])

    frames += move_mouse(frames, cc['pastezone'], cc['mask'], state_fn=st_img_pasted,
                         telop="「マスキング実行」をクリックします")
    frames += hold(st_img_pasted, "「マスキング実行」をクリックします", 400, cc['mask'])

    for _ in range(3):
        for alpha in [1.0, 0.4]:
            s = {'has_image':True,'btn_state':'running','mask_label':'実行中','pct':0,'ptext':'処理中...'}
            img = render_clipboard_tab(s)
            if alpha < 1.0:
                img = Image.blend(img, Image.new('RGB',(W,H),WHITE), 0.3)
            img = add_telop(img, "OCR で個人情報を検出中...")
            add_cursor(img, cc['mask'][0], cc['mask'][1])
            frames.append((img, 120))

    for pct, txt in PROGRESS_STEPS:
        s = {'has_image':True,'btn_state':'running','mask_label':'実行中','pct':pct,'ptext':txt}
        img = render_clipboard_tab(s)
        img = add_telop(img, "OCR で個人情報を検出中...")
        add_cursor(img, cc['mask'][0], cc['mask'][1])
        frames.append((img, 300))

    def st_dl():
        return render_clipboard_tab({'has_image':True,'btn_state':'download',
                                     'mask_label':'ダウンロード','pct':100,'ptext':'完了'})
    frames += hold(st_dl, "マスク済み画像をダウンロードできます！", 2400, cc['mask'])

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



