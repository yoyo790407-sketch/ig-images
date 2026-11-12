"""Sunny 剪片師 — 仿 growthfyn 風格的口播／生活影片剪輯流程

用法：
  python3 reel.py transcribe 影片.mov 工作資料夾      # 產生 proxy.mp4、transcript.json
  python3 reel.py storyboard 工作資料夾               # 產生 storyboard.jpg（三種字幕風格給她選）
  python3 reel.py render 工作資料夾/plan.json         # 依剪輯計畫輸出 reel.mp4、cover.jpg、compare.mp4

plan.json 由 Claude 依逐字稿撰寫，欄位見 SKILL.md。
需要：ffmpeg、playwright(chromium)、faster-whisper、rembg、手寫字型（npm pack lxgw-wenkai-tc-webfont 解到 /tmp/f）
"""
import asyncio, json, os, subprocess, sys, glob, shutil

FONT_DIR = "/tmp/f/package/"
W, H = 1080, 1920


def sh(args):
    subprocess.run(args, check=True)


def dur(path):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path]).decode())


def ensure_font():
    if not os.path.exists(FONT_DIR + "lxgwwenkaitc-bold.css"):
        os.makedirs("/tmp/f", exist_ok=True)
        sh(["bash", "-c", "cd /tmp/f && npm pack -q lxgw-wenkai-tc-webfont >/dev/null && tar xzf lxgw-wenkai-tc-webfont-*.tgz"])


# ---------- 1. 轉檔＋聽寫 ----------
def transcribe(src, wd):
    os.makedirs(wd, exist_ok=True)
    proxy = f"{wd}/proxy.mp4"
    sh(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=30",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-c:a", "aac", "-b:a", "192k", "-map", "0:v:0", "-map", "0:a:0", proxy])
    sh(["ffmpeg", "-v", "error", "-y", "-i", proxy, "-ac", "1", "-ar", "16000", "-f", "f32le", f"{wd}/a.raw"])
    import numpy as np
    from faster_whisper import WhisperModel
    a = np.fromfile(f"{wd}/a.raw", dtype=np.float32)
    m = WhisperModel("small", device="cpu", compute_type="int8")
    segs, _ = m.transcribe(a, language="zh", initial_prompt="以下是繁體中文的句子。", vad_filter=True, word_timestamps=True)
    out = [{"s": round(s.start, 2), "e": round(s.end, 2), "t": s.text.strip()} for s in segs]
    json.dump({"duration": dur(proxy), "segments": out}, open(f"{wd}/transcript.json", "w"), ensure_ascii=False, indent=1)
    for s in out:
        print(s["s"], s["e"], s["t"])


# ---------- 樣式 ----------
STYLES = {
    # A：白色粗字＋黑色光暈＋黃色手寫補充（growthfyn 主風格）
    "A": ".cap{color:#fff;font-weight:900;font-size:80px;text-shadow:0 0 14px rgba(0,0,0,.8),0 4px 8px rgba(0,0,0,.6)}"
         ".hw{color:#F6C344;text-shadow:0 0 12px rgba(0,0,0,.75)}",
    # B：黃底黑字標籤
    "B": ".cap span.l{background:#F6C344;color:#1E1E1E;font-weight:900;font-size:72px;padding:6px 26px;border-radius:14px;box-decoration-break:clone;-webkit-box-decoration-break:clone}"
         ".hw{color:#fff;text-shadow:0 0 12px rgba(0,0,0,.8)}",
    # C：白字粗黑描邊（綜藝感）
    "C": ".cap{color:#fff;font-weight:900;font-size:84px;-webkit-text-stroke:10px #1E1E1E;paint-order:stroke fill}"
         ".hw{color:#FF8A3D;-webkit-text-stroke:8px #fff;paint-order:stroke fill}",
}
BASE_CSS = """<link rel=stylesheet href="lxgwwenkaitc-bold.css"><style>*{margin:0;padding:0;box-sizing:border-box}
body{width:1080px;height:1920px;background:transparent;position:relative;font-family:'Noto Sans CJK TC'}
.cap{position:absolute;left:40px;right:40px;top:1330px;text-align:center;line-height:1.3}
.hw{font-family:'LXGW WenKai TC';font-weight:700;font-size:64px;margin-top:12px;display:block}
.glass{position:absolute;border-radius:40px;background:rgba(255,250,244,.86);color:#3B2F2A;box-shadow:0 20px 50px rgba(0,0,0,.25)}
.card{left:90px;top:200px;width:640px;padding:44px 50px}
.card h3{font-size:34px;color:#8C7B6B;font-weight:700;margin-bottom:20px}
.row{font-size:50px;font-weight:700;margin:16px 0;display:flex;align-items:center;gap:22px}
.ck{width:54px;height:54px;border-radius:14px;display:inline-flex;align-items:center;justify-content:center;font-size:38px;color:#fff;background:#8FB39A;flex:none}
.ck.no{background:transparent;border:4px solid #C9B8AA}
.vs{left:60px;right:60px;top:180px;padding:40px 56px;display:flex;align-items:center;justify-content:space-between}
.big{font-family:'Noto Serif CJK TC';font-weight:900;font-size:150px;line-height:1}
.unit{font-size:56px;font-weight:900;margin-left:8px}
.pill{font-size:40px;font-weight:700;color:#8C7B6B;border:3px solid #C9B8AA;border-radius:30px;padding:4px 22px;margin:8px 0;text-align:center}
.strike{position:absolute;left:-10px;right:-10px;top:52%;height:12px;background:#D9452B;border-radius:6px}
.prog{left:200px;right:200px;top:120px;padding:22px 34px;display:flex;align-items:center;gap:20px;font-size:32px;font-weight:700}
.bar{flex:1;height:14px;border-radius:7px;background:#E6DCD2;overflow:hidden}.bar i{display:block;height:100%;background:#D9A441}
svg{position:absolute}</style>"""


def spark(pos, s=1, c="#F6C344"):
    return f'<svg width="{int(110*s)}" height="{int(150*s)}" viewBox="0 0 60 80" style="{pos}"><path d="M30 4C33 26 38 32 56 36 38 40 33 48 30 76 27 48 22 40 4 36 22 32 27 26 30 4Z" fill="{c}"/></svg>'


def burst(pos, c="#fff"):
    return f'<svg width="200" height="200" viewBox="0 0 100 100" style="{pos}"><path d="M30 70 18 30M50 64 58 18M66 74 92 46" stroke="{c}" stroke-width="6" stroke-linecap="round"/></svg>'


def cap_html(t, hw, style):
    inner = f'<span class=l>{t}</span>' if style == "B" else t
    return f'<div class=cap>{inner}{f"<span class=hw>{hw}</span>" if hw else ""}</div>'


def overlay_html(item, style):
    k = item["type"]
    if k == "cap":
        x = cap_html(item["t"], item.get("hw", ""), style)
        if item.get("fx"):
            x += burst("right:90px;top:1180px") + spark("left:110px;top:1250px", .7)
        return x
    if k == "title":
        return (f'<div class=cap style="top:330px;font-size:104px">{item["title"]}</div>'
                f'<div class="cap" style="top:470px"><span class=hw style="font-size:78px">{item.get("sub","")}</span></div>'
                + spark("left:110px;top:250px") + spark("right:120px;top:470px", .7) + burst("right:100px;top:170px"))
    if k == "check":
        n = sum(1 for _, c in item["rows"] if c)
        rows = "".join(f'<div class=row><span class="ck{"" if c else " no"}">{"✓" if c else ""}</span>{t}</div>' for t, c in item["rows"])
        return f'<div class="glass card"><h3>{item["head"]} {n}/{len(item["rows"])}</h3>{rows}</div>'
    if k == "vs":  # 數字對比卡：舊數字劃掉、新數字變黃
        stage = item.get("stage", "old")
        num, unit = (item["new"] if stage == "new" else item["old"])
        color = "#D9A441" if stage == "new" else "#3B2F2A"
        strike = '<div class=strike></div>' if stage == "strike" else ""
        pills = "".join(f'<div class=pill>{p}</div>' for p in item.get("items", []))
        return (f'<div class="glass vs"><div style="position:relative;display:flex;align-items:baseline;color:{color}">'
                f'<span class=big>{num}</span><span class=unit>{unit}</span>{strike}</div><div>{pills}</div></div>')
    if k == "progress":
        p = item.get("pct", 60)
        return f'<div class="glass prog"><span>{item["label"]}</span><div class=bar><i style="width:{p}%"></i></div><span>{p}%</span></div>'
    if k == "sticker":  # 任意圖片（App 圖示、截圖）放在指定位置
        return f'<img src="{os.path.abspath(item["path"])}" style="position:absolute;{item.get("pos","left:90px;top:220px;width:300px")};border-radius:30px;box-shadow:0 12px 30px rgba(0,0,0,.3)">'
    raise ValueError(k)


async def render_pngs(items, style, outdir):
    from playwright.async_api import async_playwright
    ensure_font()
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--allow-file-access-from-files"])
        pg = await b.new_page(viewport={"width": W, "height": H})
        for i, it in enumerate(items):
            html = "<html><head><meta charset=utf-8>" + BASE_CSS + f"<style>{STYLES[style]}</style></head><body>" + overlay_html(it, style) + "</body></html>"
            open(FONT_DIR + "ov.html", "w").write(html)
            await pg.goto("file://" + FONT_DIR + "ov.html")
            await pg.evaluate("document.fonts.ready")
            await pg.wait_for_timeout(200)
            it["png"] = f"{outdir}/ov{i:03d}.png"
            await pg.screenshot(path=it["png"], omit_background=True)
        await b.close()


# ---------- 2. storyboard：三種字幕風格 ----------
def storyboard(wd):
    tr = json.load(open(f"{wd}/transcript.json"))
    seg = max(tr["segments"], key=lambda s: len(s["t"])) if tr["segments"] else {"s": 1, "t": "字幕範例"}
    frame = f"{wd}/sb_frame.jpg"
    sh(["ffmpeg", "-v", "error", "-y", "-ss", str(seg["s"] + 0.3), "-i", f"{wd}/proxy.mp4", "-frames:v", "1", frame])
    from PIL import Image, ImageDraw, ImageFont
    tiles = []
    for st in "ABC":
        items = [{"type": "cap", "t": seg["t"][:14], "hw": "手寫補充字"}]
        os.makedirs(f"{wd}/sb", exist_ok=True)
        asyncio.run(render_pngs(items, st, f"{wd}/sb"))
        bg = Image.open(frame).convert("RGBA")
        bg.alpha_composite(Image.open(items[0]["png"]))
        tiles.append(bg.convert("RGB").resize((360, 640)))
    f = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", 30)
    sb = Image.new("RGB", (360 * 3 + 40, 700), "white")
    d = ImageDraw.Draw(sb)
    for i, (t, name) in enumerate(zip(tiles, ["A 白字黃手寫", "B 黃底標籤", "C 粗描邊綜藝"])):
        sb.paste(t, (i * 380, 60))
        d.text((i * 380 + 10, 12), name, fill="black", font=f)
    sb.save(f"{wd}/storyboard.jpg", quality=88)
    print(f"{wd}/storyboard.jpg")


# ---------- 3. 頭部光芒（rembg 去背，光芒放在人後面） ----------
def glow_clip(wd, s, e):
    from rembg import remove, new_session
    from PIL import Image, ImageDraw, ImageFilter
    import math
    fd = f"{wd}/glow"
    shutil.rmtree(fd, ignore_errors=True); os.makedirs(fd)
    sh(["ffmpeg", "-v", "error", "-y", "-ss", str(s), "-t", str(e - s), "-i", f"{wd}/proxy.mp4", "-vf", "fps=30", f"{fd}/f%04d.png"])
    sess = new_session("u2net_human_seg")
    frames = sorted(glob.glob(f"{fd}/f*.png"))
    for n, fp in enumerate(frames):
        im = Image.open(fp).convert("RGBA")
        small = im.resize((W // 3, H // 3))
        mask = remove(small, session=sess, only_mask=True).resize((W, H))
        bb = mask.point(lambda v: 255 if v > 128 else 0).getbbox() or (W // 3, H // 4, 2 * W // 3, H // 2)
        cx, cy = (bb[0] + bb[2]) // 2, bb[1] + int((bb[3] - bb[1]) * 0.18)
        g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(g)
        rot = n * 0.02
        for k in range(14):
            a = rot + k * 2 * math.pi / 14
            bw = bb[2] - bb[0]
            r1, r2 = int(bw * 0.42), int(bw * 0.42) + 190 + (50 if k % 2 else 0)
            d.line([(cx + r1 * math.cos(a), cy + r1 * math.sin(a)), (cx + r2 * math.cos(a), cy + r2 * math.sin(a))], fill=(255, 140, 70, 230), width=22)
        halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(halo).ellipse([cx - 260, cy - 260, cx + 260, cy + 260], fill=(255, 150, 90, 150))
        g = Image.alpha_composite(halo.filter(ImageFilter.GaussianBlur(60)), g.filter(ImageFilter.GaussianBlur(2)))
        out = Image.alpha_composite(im, g)
        person = im.copy(); person.putalpha(mask)
        out = Image.alpha_composite(out, person)
        out.convert("RGB").save(fp)
    sh(["ffmpeg", "-v", "error", "-y", "-framerate", "30", "-i", f"{fd}/f%04d.png", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", f"{wd}/glow.mp4"])
    return f"{wd}/glow.mp4"


# ---------- 4. render ----------
def render(plan_path):
    plan = json.load(open(plan_path))
    wd = os.path.dirname(os.path.abspath(plan_path))
    style = plan.get("style", "A")
    proxy = f"{wd}/proxy.mp4"
    total = dur(proxy)
    items = []
    for c in plan.get("captions", []):
        items.append({"type": "cap", **c})
    items += plan.get("cards", [])
    od = f"{wd}/ov"; shutil.rmtree(od, ignore_errors=True); os.makedirs(od)
    asyncio.run(render_pngs(items, style, od))

    # (a) 在原始時間軸疊字幕和卡片
    args = ["ffmpeg", "-v", "error", "-y", "-i", proxy]
    fc, prev, idx = [], "0:v", 1
    g = plan.get("glow")
    if g:
        args += ["-itsoffset", str(g["s"]), "-i", glow_clip(wd, g["s"], g["e"])]
        fc.append(f"[0:v][1:v]overlay=0:0:eof_action=pass[g0]"); prev = "g0"; idx = 2
    for it in items:
        s, e = it["s"], it["e"]; d = e - s
        args += ["-loop", "1", "-t", f"{d:.2f}", "-i", it["png"]]
        pop = it["type"] == "cap"
        fc.append(f"[{idx}:v]format=rgba,fade=in:st=0:d={0.1 if pop else 0.2}:alpha=1,fade=out:st={max(d-0.12,0.01):.2f}:d=0.1:alpha=1,setpts=PTS+{s}/TB[o{idx}]")
        y = f"'if(lt(t-{s},0.15),(1-(t-{s})/0.15)*40,0)'" if pop else "0"
        fc.append(f"[{prev}][o{idx}]overlay=x=0:y={y}:eof_action=pass[v{idx}]"); prev = f"v{idx}"; idx += 1
    fc.append(f"[{prev}]format=yuv420p[v]")
    full = f"{wd}/full.mp4"
    sh(args + ["-filter_complex", ";".join(fc), "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-c:a", "aac", "-b:a", "160k", full])

    # (b) 剪空白：保留片段，奇數段放大 1.1 倍做跳接感
    keep = plan.get("keep") or [[0, total]]
    fc, cat = [], ""
    for i, (s, e) in enumerate(keep):
        z = plan.get("jump_zoom", True) and i % 2 == 1
        zf = f",scale={int(W*1.1)}:{int(H*1.1)},crop={W}:{H}" if z else ""
        fc.append(f"[0:v]trim={s}:{e},setpts=PTS-STARTPTS{zf}[v{i}];[0:a]atrim={s}:{e},asetpts=PTS-STARTPTS,afade=t=in:d=0.04,afade=t=out:st={e-s-0.05:.2f}:d=0.05[a{i}]")
        cat += f"[v{i}][a{i}]"
    fc.append(f"{cat}concat=n={len(keep)}:v=1:a=1[v][a]")
    out = f"{wd}/reel.mp4"
    sh(["ffmpeg", "-v", "error", "-y", "-i", full, "-filter_complex", ";".join(fc), "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", out])

    # (c) 封面：去背人像貼紙（白色描邊）＋大標
    cv = plan.get("cover")
    if cv:
        make_cover(wd, cv)
    # (d) 前後對比：左原始、右成品，兩支手機框
    if plan.get("compare"):
        make_compare(wd, plan["compare"].get("s", 0), plan["compare"].get("len", 6))
    print(out)


def make_cover(wd, cv):
    from rembg import remove, new_session
    from PIL import Image, ImageFilter
    fr = f"{wd}/cover_frame.png"
    sh(["ffmpeg", "-v", "error", "-y", "-ss", str(cv.get("t", 1)), "-i", f"{wd}/proxy.mp4", "-frames:v", "1", fr])
    im = Image.open(fr).convert("RGBA")
    mask = remove(im.resize((W // 2, H // 2)), session=new_session("u2net_human_seg"), only_mask=True).resize((W, H))
    person = im.copy(); person.putalpha(mask)
    edge = mask.filter(ImageFilter.MaxFilter(25))
    white = Image.new("RGBA", (W, H), (255, 255, 255, 255)); white.putalpha(edge)
    bg = im.filter(ImageFilter.GaussianBlur(18)).point(lambda v: int(v * 0.55))
    bg = bg.convert("RGBA")
    bg.alpha_composite(white); bg.alpha_composite(person)
    bg.save(f"{wd}/cover_base.png")
    html_items = [{"type": "title", "title": cv["title"], "sub": cv.get("sub", ""), "s": 0, "e": 1}]
    asyncio.run(render_pngs(html_items, "A", wd))
    bg.alpha_composite(Image.open(html_items[0]["png"]))
    bg.convert("RGB").save(f"{wd}/cover.jpg", quality=92)


def make_compare(wd, s, ln):
    sh(["ffmpeg", "-v", "error", "-y", "-ss", str(s), "-t", str(ln), "-i", f"{wd}/proxy.mp4", "-ss", str(s), "-t", str(ln), "-i", f"{wd}/reel.mp4",
        "-filter_complex",
        "color=c=0xF3EBDD:s=1080x1920:d=%s[bg];[0:v]scale=480:853,pad=500:873:10:10:white[l];[1:v]scale=480:853,pad=500:873:10:10:white[r];"
        "[bg][l]overlay=30:560[b1];[b1][r]overlay=550:560,drawtext=fontfile=/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc:text='剪輯前後對比':fontsize=90:fontcolor=0x3B2F2A:x=(w-text_w)/2:y=250,"
        "drawtext=fontfile=/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc:text='原始影片':fontsize=54:fontcolor=0x3B2F2A:x=170:y=460,"
        "drawtext=fontfile=/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc:text='剪好的樣子':fontsize=54:fontcolor=0xD9A441:x=660:y=460,format=yuv420p[v]" % ln,
        "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-c:a", "aac", "-shortest", f"{wd}/compare.mp4"])


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "transcribe": transcribe(sys.argv[2], sys.argv[3])
    elif cmd == "storyboard": storyboard(sys.argv[2])
    elif cmd == "render": render(sys.argv[2])
