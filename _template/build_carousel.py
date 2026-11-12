import asyncio, json, sys, os
from playwright.async_api import async_playwright
from PIL import Image
P="/tmp/f/package/"
head="""<link rel=stylesheet href="lxgwwenkaitc-bold.css"><style>
*{margin:0;padding:0;box-sizing:border-box}
body{width:1080px;height:1350px;position:relative;overflow:hidden;color:#fff;font-family:'Noto Sans CJK TC'}
.bg{position:absolute;inset:-20px;background:url(BG) center 70%/cover}
.shade{position:absolute;inset:0}
.hw{font-family:'LXGW WenKai TC';font-weight:700}
em{font-style:normal;color:#F6C344}
.tag{color:#F6C344;font-size:44px}
.brand{position:absolute;left:90px;bottom:80px;font-family:'Noto Serif CJK TC';font-size:30px;letter-spacing:8px;opacity:.9}
.handle{position:absolute;right:90px;bottom:80px;font-size:30px;opacity:.85}
.pg{position:absolute;right:90px;top:80px;font-size:28px;opacity:.75}
svg{position:absolute}
p{font-size:44px;line-height:1.75;color:#F3ECE4}
.box{position:absolute;left:90px;right:90px}
</style>"""
burst=lambda pos:f'<svg width="170" height="170" viewBox="0 0 100 100" style="{pos}"><path d="M30 70 18 30M50 64 58 18M66 74 92 46" stroke="#fff" stroke-width="5" stroke-linecap="round"/></svg>'
spark=lambda pos:f'<svg width="110" height="150" viewBox="0 0 60 80" style="{pos}"><path d="M30 4C33 26 38 32 56 36 38 40 33 48 30 76 27 48 22 40 4 36 22 32 27 26 30 4Z" fill="none" stroke="#F6C344" stroke-width="4" stroke-linejoin="round"/></svg>'
arrow='<svg width="220" height="120" viewBox="0 0 220 120" style="right:80px;bottom:150px"><path d="M10 30C60 110 150 100 200 60" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round"/><path d="M175 50 202 58 188 84" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/></svg><div class="hw" style="position:absolute;right:300px;bottom:190px;font-size:40px">下一頁</div>'
def page(kind,tag,h,body,i,n,bg):
    blur='<div class=bg style="filter:blur(6px) brightness(.8)"></div><div class=shade style="background:rgba(20,14,10,.64)"></div>'
    pgn=f'<div class=pg>{i}/{n}</div>'
    if kind=="cover":
        return f"""<div class=bg></div><div class=shade style="background:linear-gradient(180deg,rgba(20,14,10,.55),rgba(20,14,10,.35) 40%,rgba(20,14,10,.78))"></div>{burst('right:90px;top:120px')}{spark('left:70px;top:180px')}
<div class=box style="top:400px"><div class="hw tag">\\ {tag} /</div><div class=hw style="font-size:112px;line-height:1.28;margin-top:30px;text-shadow:0 4px 18px rgba(0,0,0,.5)">{h}</div></div>
<div class=brand>SUNNY 品牌萃取所</div><div class=handle>@sunny_lin67</div>"""
    if kind=="num":
        return f"""{blur}{spark('right:90px;top:150px')}{pgn}<div class=box style="top:250px">
<div style="font-family:'Noto Serif CJK TC';font-weight:900;font-size:150px;color:#F6C344;line-height:1">0{tag}</div>
<div class=hw style="font-size:90px;line-height:1.3;margin-top:30px">{h}</div>
<div style="width:110px;height:6px;background:#F6C344;margin:50px 0"></div><p>{body}</p></div>{arrow if i<n else ''}<div class=brand>SUNNY 品牌萃取所</div>"""
    if kind=="text":
        return f"""{blur}{burst('right:80px;top:140px')}{pgn}<div class=box style="top:300px">
{f'<div class="hw tag">{tag}</div>' if tag else ''}<div class=hw style="font-size:92px;line-height:1.3;margin-top:30px">{h}</div>
<div style="width:110px;height:6px;background:#F6C344;margin:50px 0"></div><p>{body}</p></div>{arrow}<div class=brand>SUNNY 品牌萃取所</div>"""
    if kind=="sum":
        return f"""<div class=bg style="background-position:center 30%;filter:brightness(.7)"></div><div class=shade style="background:rgba(20,14,10,.55)"></div>{spark('left:90px;top:300px')}{spark('right:110px;bottom:330px;transform:scale(.7)')}{pgn}
<div class=box style="top:470px;text-align:center"><div class="hw tag">{tag or '重點整理'}</div><div class=hw style="font-size:96px;line-height:1.4;margin-top:40px">{h}</div></div><div class=brand>SUNNY 品牌萃取所</div>"""
    return f"""<div class=bg style="background-position:center 20%;filter:brightness(.85)"></div><div class=shade style="background:rgba(20,14,10,.6)"></div>{burst('left:80px;top:150px;transform:scaleX(-1)')}{pgn}
<div class=box style="top:380px;text-align:center"><div class="hw" style="font-size:100px;color:#F6C344">{h}</div><p style="margin-top:60px">{body}</p></div>
<div class=brand>SUNNY 品牌萃取所</div><div class=handle>@sunny_lin67</div>"""
async def main(spec,out,bg):
    pages=json.load(open(spec)); os.makedirs(out,exist_ok=True); n=len(pages)
    async with async_playwright() as p:
        b=await p.chromium.launch(); pg=await b.new_page(viewport={'width':1080,'height':1350})
        for i,(k,t,h,body) in enumerate(pages,1):
            html="<html><head><meta charset=utf-8>"+head.replace("BG",bg)+"</head><body>"+page(k,t,h,body,i,n,bg)+"</body></html>"
            f=P+"tmp.html"; open(f,"w").write(html)
            await pg.goto("file://"+f); await pg.evaluate("document.fonts.ready"); await pg.wait_for_timeout(500)
            await pg.screenshot(path=f"{out}/p{i:02d}.jpg",type="jpeg",quality=90)
        await b.close()
    ims=[Image.open(f"{out}/p{i:02d}.jpg").resize((270,338)) for i in range(1,n+1)]
    s=Image.new('RGB',(270*5,338*((n+4)//5)),'white')
    for k,im in enumerate(ims): s.paste(im,((k%5)*270,(k//5)*338))
    s.save(f"{out}-preview.jpg",quality=88)
asyncio.run(main(*sys.argv[1:4]))
