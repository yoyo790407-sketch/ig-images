"""Sunny 剪片師 toolkit. 用法見 SKILL.md。
pipeline: proxy -> transcribe -> plan(JSON) -> render overlays -> composite -> cut silence
"""
import asyncio, json, os, subprocess, sys, math, glob
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
FONT_DIR="/tmp/f/package/"   # lxgw wenkai (npm pack lxgw-wenkai-tc-webfont)
W,H=1080,1920; FPS=30

# ---------- 1. proxy ----------
def proxy(src,out="p.mp4"):
    subprocess.run(["ffmpeg","-v","error","-y","-i",src,"-vf",f"scale={W}:{H},fps={FPS}","-c:v","libx264","-preset","veryfast","-crf","18","-c:a","aac","-b:a","192k","-map","0:v:0","-map","0:a:0",out],check=True); return out

# ---------- 2. transcribe ----------
def transcribe(video,out="tr.json"):
    from faster_whisper import WhisperModel
    subprocess.run(["ffmpeg","-v","error","-y","-i",video,"-ac","1","-ar","16000","-f","f32le","_a.raw"],check=True)
    a=np.fromfile("_a.raw",dtype=np.float32)
    m=WhisperModel("small",device="cpu",compute_type="int8")
    segs,_=m.transcribe(a,language="zh",initial_prompt="以下是繁體中文的句子。",word_timestamps=True,vad_filter=True)
    res=[{"start":round(s.start,2),"end":round(s.end,2),"text":s.text.strip(),"words":[[w.word,round(w.start,2),round(w.end,2)] for w in s.words]} for s in segs]
    json.dump(res,open(out,"w"),ensure_ascii=False,indent=1); return res

# ---------- 3. overlay components (HTML, animated by t in seconds) ----------
CSS="""<link rel=stylesheet href="lxgwwenkaitc-bold.css"><style>
*{margin:0;padding:0;box-sizing:border-box}body{width:1080px;height:1920px;background:transparent;position:relative;font-family:'Noto Sans CJK TC';overflow:hidden}
.hw{font-family:'LXGW WenKai TC';font-weight:700}
.cap{position:absolute;left:40px;right:40px;top:1330px;text-align:center;color:#fff;font-weight:900;font-size:80px;line-height:1.25;text-shadow:0 0 14px rgba(0,0,0,.8),0 4px 8px rgba(0,0,0,.6)}
.gold{color:#F6C344;font-size:62px;margin-top:12px;text-shadow:0 0 12px rgba(0,0,0,.7)}
.card{position:absolute;background:rgba(255,250,244,.88);border-radius:40px;color:#3B2F2A;box-shadow:0 20px 50px rgba(0,0,0,.28);backdrop-filter:blur(10px)}
.pill{position:absolute;left:50%;transform:translateX(-50%);top:120px;white-space:nowrap;background:rgba(255,250,244,.92);border-radius:60px;padding:22px 44px;display:flex;align-items:center;gap:22px;font-size:34px;font-weight:700;color:#3B2F2A;box-shadow:0 12px 30px rgba(0,0,0,.25)}
.bar{width:220px;height:14px;background:#E6DED3;border-radius:7px;overflow:hidden}.bar i{display:block;height:100%;background:#F6A623;border-radius:7px}
.row{font-size:48px;font-weight:700;margin:14px 0;display:flex;align-items:center;gap:22px;transition:opacity .2s}
.ck{width:54px;height:54px;border-radius:14px;flex:none;display:inline-flex;align-items:center;justify-content:center;font-size:36px;color:#fff;background:#8FB39A;transform:scale(1)}
.ck.no{background:transparent;border:4px solid #C9B8AA}
.phone{position:absolute;width:420px;height:860px;border-radius:60px;background:#111;border:12px solid #222;overflow:hidden;box-shadow:0 30px 60px rgba(0,0,0,.4)}
.phone img{width:100%;height:100%;object-fit:cover}
.tag{position:absolute;top:-30px;left:50%;transform:translateX(-50%);background:#F6C344;color:#3B2F2A;font-size:30px;font-weight:700;padding:8px 26px;border-radius:30px;white-space:nowrap}
.icon{width:150px;height:150px;border-radius:36px;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:60px;color:#fff;position:relative}
.icon .x{position:absolute;inset:-14px;border:10px solid #E8453C;border-radius:46px}
.icon .x:before,.icon .x:after{content:'';position:absolute;left:50%;top:50%;width:160%;height:12px;background:#E8453C;transform:translate(-50%,-50%) rotate(45deg)}.icon .x:after{transform:translate(-50%,-50%) rotate(-45deg)}
.chat{position:absolute;left:120px;right:120px;top:260px;background:#fff;border-radius:36px;padding:36px 40px;font-size:40px;color:#222;box-shadow:0 20px 50px rgba(0,0,0,.28)}
.chat .lbl{display:flex;align-items:center;gap:14px;font-size:28px;color:#888;margin-bottom:22px}.dot{width:18px;height:18px;border-radius:50%;background:#D97757}
.chat .send{position:absolute;right:30px;bottom:30px;width:64px;height:64px;border-radius:18px;background:#D97757;color:#fff;display:flex;align-items:center;justify-content:center;font-size:34px}
.file{display:inline-flex;align-items:center;gap:16px;background:#F3EEE6;border-radius:20px;padding:14px 22px;font-size:30px;margin-top:20px;font-family:monospace}
.num{position:absolute;left:90px;top:230px;background:rgba(255,250,244,.9);border-radius:36px;padding:40px 60px;box-shadow:0 20px 50px rgba(0,0,0,.25);display:flex;align-items:center;gap:40px}
.num b{font-size:150px;line-height:1;color:#3B2F2A;position:relative}.num b.strike:after{content:'';position:absolute;left:-10px;right:-10px;top:52%;height:14px;background:#E8453C;border-radius:7px}
.num b.gold{color:#F6A623;font-size:150px}.num small{font-size:44px;font-weight:700;color:#3B2F2A;margin-left:8px}
.subtags{display:flex;flex-direction:column;gap:12px}.subtags span{background:#F3EEE6;border-radius:20px;padding:8px 22px;font-size:30px;font-weight:700;color:#8C7B6B;position:relative}
.subtags span.s:after{content:'';position:absolute;left:14px;right:14px;top:50%;height:4px;background:#E8453C}
.cmt{position:absolute;left:60px;right:60px;top:1060px;background:#fff;border-radius:40px 40px 0 0;padding:30px 40px;color:#222;box-shadow:0 -10px 40px rgba(0,0,0,.3);min-height:400px}
.cmt h4{text-align:center;font-size:30px;color:#666;border-bottom:1px solid #eee;padding-bottom:16px;margin-bottom:24px}
.cmt .c{display:flex;gap:20px;font-size:32px;margin:14px 0}.av{width:64px;height:64px;border-radius:50%;background:#E8C9B0;flex:none}
.sb{position:absolute;left:60px;right:60px;top:220px;background:#fff;border-radius:36px;padding:30px;box-shadow:0 20px 50px rgba(0,0,0,.28)}
.sb .g{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px}.sb img{width:100%;aspect-ratio:9/16;object-fit:cover;border-radius:18px}
.sb h4{font-size:28px;color:#888;margin-bottom:18px}
svg{position:absolute}
</style>"""
SPARK=lambda x,y,s=1,c="#F6C344":f'<svg width="{int(110*s)}" height="{int(150*s)}" viewBox="0 0 60 80" style="left:{x}px;top:{y}px"><path d="M30 4C33 26 38 32 56 36 38 40 33 48 30 76 27 48 22 40 4 36 22 32 27 26 30 4Z" fill="{c}"/></svg>'
BURST=lambda x,y,s=1:f'<svg width="{int(200*s)}" height="{int(200*s)}" viewBox="0 0 100 100" style="left:{x}px;top:{y}px"><path d="M30 70 18 30M50 64 58 18M66 74 92 46" stroke="#fff" stroke-width="6" stroke-linecap="round"/></svg>'

def ease(t,a,b): return 0 if t<=a else 1 if t>=b else (lambda x:x*x*(3-2*x))((t-a)/(b-a))

def comp_html(kind,p,t,dur):
    """return html for component `kind` with params p at local time t"""
    pop=ease(t,0,0.25); out=1-ease(t,dur-0.25,dur)
    s=f"transform:scale({0.85+0.15*pop});opacity:{pop*out}"
    if kind=="title":
        return f'<div style="position:absolute;inset:0;{s};transform-origin:50% 25%"><div class=cap style="top:{p.get("y",330)}px;font-size:104px">{p["text"]}</div><div class="cap hw gold" style="top:{p.get("y",330)+140}px;font-size:78px">{p.get("sub","")}</div>{SPARK(110,p.get("y",330)-80)}{SPARK(850,p.get("y",330)+140,.7)}{BURST(860,p.get("y",330)-160)}</div>'
    if kind=="caption":
        words=p.get("words"); txt=p["text"]
        if words:  # 逐字出現：平均分配在前 0.7 秒內（whisper 的中文逐字時間不可靠，不用它）
            n=max(1,int(round(len(txt)*ease(t,0,min(0.7,dur*0.6))))); txt=txt[:n]
        g=f'<div class="hw gold">{p["gold"]}</div>' if p.get("gold") and t>p.get("gold_at",0.3) else ""
        return f'<div class=cap style="opacity:{min(1,t/0.1)*out}">{txt}{g}</div>'
    if kind=="checklist":
        items=p["items"]; done=int(min(len(items),math.floor(max(0,t-p.get("delay",0.4))/p.get("every",0.5))))
        rows="".join(f'<div class=row><span class="ck{"" if i<done else " no"}">{"✓" if i<done else ""}</span>{it}</div>' for i,it in enumerate(items))
        return f'<div class=card style="left:90px;top:{p.get("y",200)}px;width:640px;padding:40px 50px;{s};transform-origin:0 0"><div style="font-size:32px;color:#8C7B6B;font-weight:700;margin-bottom:16px">{p.get("title","")} {done}/{len(items)}</div>{rows}</div>'
    if kind=="progress":
        pct=int(100*ease(t,0.3,dur-0.6))
        return f'<div class=pill style="opacity:{pop*out}"><span class=dot></span>{p["text"]}<span class=bar><i style="width:{pct}%"></i></span><span style="font-size:28px;color:#8C7B6B">{pct}%</span></div>'
    if kind=="chat":
        typed=p["text"][:int(len(p["text"])*ease(t,0.3,0.3+p.get("type_dur",1.2)))]
        f=f'<div class=file>📎 {p["file"]}</div>' if p.get("file") and t>p.get("file_at",0.2) else ""
        cur='<span style="border-left:4px solid #222;margin-left:4px"></span>' if int(t*3)%2==0 else ""
        return f'<div class=chat style="{s};transform-origin:50% 0"><div class=lbl><span class=dot></span>Claude</div>{typed}{cur}{f}<div class=send>↑</div></div>'
    if kind=="apps":
        apps=[("CapCut","#111"),("Edits","#222"),("Premiere","#2C1F6B")]
        k=int(min(3,math.floor(max(0,t-0.5)/0.35)))
        ic="".join(f'<div style="text-align:center"><div class=icon style="background:{c}">{n[0]}{"<div class=x></div>" if i<k else ""}</div><div style="color:#fff;font-size:28px;margin-top:12px;text-shadow:0 2px 6px #000">{n}</div></div>' for i,(n,c) in enumerate(apps))
        return f'<div style="position:absolute;left:0;right:0;top:{p.get("y",160)}px;display:flex;justify-content:center;gap:60px;{s};transform-origin:50% 0">{ic}</div>'
    if kind=="number":
        sw=t>p.get("switch",1.2)
        tags="".join(f'<span class="{"s" if sw else ""}">{x}</span>' for x in p.get("tags",[]))
        big=f'<b class=strike>{p["before"]}</b><small>{p["unit"]}</small>' if not sw else f'<b class=gold>{p["after"]}</b><small>{p["unit2"]}</small>'
        if sw and t>p.get("switch",1.2)+0.3: big+='<span class=hw style="color:#8FB39A;font-size:40px;margin-left:10px">✓✓✓</span>'
        return f'<div class=num style="{s};transform-origin:0 0"><div>{big}</div><div class=subtags>{tags}</div></div>'
    if kind=="phones":  # side by side before/after
        sl=ease(t,0.2,0.7)
        return f'<div style="position:absolute;inset:0;opacity:{pop*out}"><div class=phone style="left:{-500+590*sl}px;top:380px"><span class=tag>{p.get("l","raw footage")}</span><img src="{p["left"]}"></div><div class=phone style="left:{1080-(500)*sl+80}px;top:380px"><span class=tag>{p.get("r","剪輯好的")}</span><img src="{p["right"]}"></div></div>'
    if kind=="storyboard":
        imgs="".join(f'<img src="{x}">' for x in p["frames"])
        return f'<div class=sb style="{s};transform-origin:50% 0"><h4>storyboard・{p.get("title","靜態圖")}</h4><div class=g>{imgs}</div></div>'
    if kind=="comments":
        rows="".join(f'<div class=c style="opacity:{ease(t,0.3+i*0.35,0.5+i*0.35)}"><span class=av></span><div><b>{u}</b><br>{m}</div></div>' for i,(u,m) in enumerate(p["list"]))
        return f'<div class=cmt style="transform:translateY({(1-pop)*500}px);opacity:{out}"><h4>留言</h4>{rows}</div>'
    if kind=="sparkle":  # handwritten gold text + sparkles, e.g. "isn't it amazing"
        return f'<div style="position:absolute;inset:0;opacity:{pop*out}"><div class="cap hw gold" style="top:{p.get("y",1200)}px;font-size:{p.get("size",72)}px">{p["text"]}</div>{SPARK(p.get("x1",140),p.get("y",1200)-60,.8)}{SPARK(p.get("x2",860),p.get("y",1200)+40,.6)}</div>'
    raise ValueError(kind)

async def render_overlays(plan,outdir="ov"):
    from playwright.async_api import async_playwright
    os.makedirs(outdir,exist_ok=True)
    async with async_playwright() as pw:
        b=await pw.chromium.launch(); pg=await b.new_page(viewport={"width":W,"height":H})
        for i,it in enumerate(plan):
            dur=it["end"]-it["start"]; n=int(round(dur*FPS)); d=f"{outdir}/{i:02d}"; os.makedirs(d,exist_ok=True)
            static=it["kind"] in ("caption",) and not it["p"].get("words")
            frames = [0,n-1] if False else range(n)
            for f in frames:
                t=f/FPS
                html="<html><head><meta charset=utf-8>"+CSS+"</head><body>"+comp_html(it["kind"],it["p"],t,dur)+"</body></html>"
                open(FONT_DIR+"ov.html","w").write(html)
                if f==0: await pg.goto("file://"+FONT_DIR+"ov.html"); await pg.evaluate("document.fonts.ready")
                else: await pg.set_content(html.replace('href="lxgwwenkaitc-bold.css"',f'href="file://{FONT_DIR}lxgwwenkaitc-bold.css"'))
                await pg.screenshot(path=f"{d}/{f:04d}.png",omit_background=True)
            print("rendered",i,it["kind"],n,"frames",flush=True)
        await b.close()

def composite(video,plan,out="full.mp4",outdir="ov"):
    args=["ffmpeg","-v","error","-y","-i",video]; fc=[]; prev="0:v"
    for i,it in enumerate(plan):
        args+=["-framerate",str(FPS),"-i",f"{outdir}/{i:02d}/%04d.png"]
        fc.append(f"[{i+1}:v]format=rgba,setpts=PTS+{it['start']}/TB[o{i}]"); fc.append(f"[{prev}][o{i}]overlay=0:0:eof_action=pass[v{i}]"); prev=f"v{i}"
    fc.append(f"[{prev}]format=yuv420p[v]")
    args+=["-filter_complex",";".join(fc),"-map","[v]","-map","0:a","-c:v","libx264","-preset","veryfast","-crf","20","-c:a","aac","-b:a","160k",out]
    subprocess.run(args,check=True); return out

def cut(video,keep,out="reel.mp4"):
    """keep=[(s,e),...] jump-cut: drop silence/shaky parts"""
    fc=[];cat=""
    for i,(s,e) in enumerate(keep):
        fc.append(f"[0:v]trim={s}:{e},setpts=PTS-STARTPTS[v{i}];[0:a]atrim={s}:{e},asetpts=PTS-STARTPTS,afade=t=in:d=0.05,afade=t=out:st={e-s-0.06:.2f}:d=0.06[a{i}]"); cat+=f"[v{i}][a{i}]"
    fc.append(f"{cat}concat=n={len(keep)}:v=1:a=1[v][a]")
    subprocess.run(["ffmpeg","-v","error","-y","-i",video,"-filter_complex",";".join(fc),"-map","[v]","-map","[a]","-c:v","libx264","-preset","veryfast","-crf","22","-pix_fmt","yuv420p","-c:a","aac","-b:a","128k","-movflags","+faststart",out],check=True); return out

def silence_keep(tr,total,pad=0.35,min_gap=1.2):
    """from transcript -> keep ranges; gaps > min_gap with no speech are cut"""
    keep=[];cur=None
    for s in tr:
        a,b=max(0,s["start"]-pad),min(total,s["end"]+pad)
        if cur and a-cur[1]<min_gap: cur[1]=b
        else:
            if cur: keep.append(tuple(cur))
            cur=[a,b]
    if cur: keep.append(tuple(cur))
    return keep

def halo(video,start,dur,out="halo.mp4"):
    """opening: glowing orange rays behind the head (rembg mask)"""
    from rembg import remove,new_session
    os.makedirs("_halo",exist_ok=True)
    subprocess.run(["ffmpeg","-v","error","-y","-ss",str(start),"-t",str(dur),"-i",video,"-vf","scale=540:960","_halo/in_%03d.png"],check=True)
    s=new_session("u2net_human_seg"); fs=sorted(glob.glob("_halo/in_*.png")); cache=None
    for i,f in enumerate(fs):
        fr=Image.open(f).convert("RGB"); m=remove(fr,session=s,only_mask=True).convert("L"); a=np.array(m)>128; ys,xs=np.nonzero(a)
        if len(ys)>500: top=ys.min(); cache=(int(xs[ys<top+120].mean()),top+110)
        cx,cy=cache or (270,320); fade=min(1,i/6)*min(1,(len(fs)-i)/8)
        im=Image.new("RGBA",(540,960),(0,0,0,0)); d=ImageDraw.Draw(im)
        for k in range(18):
            ang=k/18*2*math.pi+i*0.04; r2=330+40*math.sin(k*1.7)
            d.line([(cx+150*math.cos(ang),cy+150*math.sin(ang)),(cx+r2*math.cos(ang),cy+r2*math.sin(ang))],fill=(255,150,60,230),width=14)
        g=Image.new("RGBA",(540,960),(0,0,0,0)); ImageDraw.Draw(g).ellipse([cx-230,cy-230,cx+230,cy+230],fill=(255,170,90,150)); g=g.filter(ImageFilter.GaussianBlur(50))
        r=Image.alpha_composite(g,im.filter(ImageFilter.GaussianBlur(2))); ra=np.array(r).astype(np.float32); ra[...,3]*=fade*(1-np.array(m.filter(ImageFilter.MaxFilter(5)))/255)
        Image.alpha_composite(fr.convert("RGBA"),Image.fromarray(ra.astype(np.uint8))).convert("RGB").resize((W,H)).save(f.replace("in_","out_"))
    subprocess.run(["ffmpeg","-v","error","-y","-framerate",str(FPS),"-i","_halo/out_%03d.png","-c:v","libx264","-preset","veryfast","-crf","18","-pix_fmt","yuv420p",out],check=True); return out

def splice_halo(video,halo_mp4,start,dur,out="p_halo.mp4"):
    subprocess.run(["ffmpeg","-v","error","-y","-i",video,"-i",halo_mp4,"-filter_complex",f"[1:v]setpts=PTS+{start}/TB[h];[0:v][h]overlay=0:0:eof_action=pass,format=yuv420p[v]","-map","[v]","-map","0:a","-c:v","libx264","-preset","veryfast","-crf","18","-c:a","copy",out],check=True); return out

def frame(video,t,out,w=270):
    subprocess.run(["ffmpeg","-v","error","-y","-ss",str(t),"-i",video,"-frames:v","1","-vf",f"scale={w}:-2",out],check=True); return out

if __name__=="__main__":
    cmd=sys.argv[1]
    if cmd=="proxy": proxy(sys.argv[2],sys.argv[3] if len(sys.argv)>3 else "p.mp4")
    elif cmd=="transcribe": transcribe(sys.argv[2])
    elif cmd=="render": asyncio.run(render_overlays(json.load(open(sys.argv[2]))))
    elif cmd=="composite": composite(sys.argv[2],json.load(open(sys.argv[3])),sys.argv[4] if len(sys.argv)>4 else "full.mp4")
    elif cmd=="cut": cut(sys.argv[2],json.load(open(sys.argv[3])),sys.argv[4] if len(sys.argv)>4 else "reel.mp4")
