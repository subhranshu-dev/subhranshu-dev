#!/usr/bin/env python3
from __future__ import annotations
import datetime as dt
import json, os, urllib.request, urllib.error
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path("assets/panda-contributions.gif")
GRAPHQL = "https://api.github.com/graphql"

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays { contributionCount date weekday }
        }
      }
    }
  }
}
"""

def get_data(username, token):
    now = dt.datetime.now(dt.timezone.utc)
    payload = json.dumps({
        "query": QUERY,
        "variables": {"login": username,
                       "from": (now-dt.timedelta(days=365)).isoformat(),
                       "to": now.isoformat()}
    }).encode()
    req = urllib.request.Request(
        GRAPHQL, data=payload,
        headers={"Authorization": f"bearer {token}",
                 "Content-Type": "application/json",
                 "User-Agent": "panda-contribution-game"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(e.read().decode(errors="replace"))
    if data.get("errors") or not data.get("data", {}).get("user"):
        raise RuntimeError(json.dumps(data, indent=2))
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days=[]
    for x,w in enumerate(cal["weeks"]):
        for d in w["contributionDays"]:
            days.append({"x":x,"y":int(d["weekday"]),
                         "count":int(d["contributionCount"]),
                         "date":d["date"]})
    return days, int(cal["totalContributions"])

def font(size, bold=False):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]
    for p in paths:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def main():
    token=os.environ["GITHUB_TOKEN"]
    username=os.environ["GITHUB_USERNAME"]
    days,total=get_data(username,token)
    by={(d["x"],d["y"]):d for d in days}
    route=[]
    for x in range(max(d["x"] for d in days)+1):
        ys=range(7) if x%2==0 else range(6,-1,-1)
        for y in ys:
            d=by.get((x,y))
            if d and d["count"]>0:
                route.append(d)
    if not route:
        route=[{"x":0,"y":3,"count":1,"date":""}]
    maxc=max(d["count"] for d in days) or 1

    # Compact but wide premium card.
    cell=12; gap=4; left=38; top=72
    cols=max(d["x"] for d in days)+1
    W=max(980,left+cols*(cell+gap)+35); H=220
    frames=[]

    def color(c):
        if c<=0:return (22,27,34)
        r=c/maxc
        if r<=.25:return (14,68,41)
        if r<=.5:return (0,109,50)
        if r<=.75:return (38,166,65)
        return (57,211,83)

    # Animate through contribution cells; each snack gets 3 frames.
    frame_count=max(72, len(route)*2)
    for f in range(frame_count):
        im=Image.new("RGB",(W,H),(8,11,18))
        dr=ImageDraw.Draw(im)
        # subtle premium border
        dr.rounded_rectangle((2,2,W-3,H-3), radius=18, outline=(31,41,55), width=2)
        dr.text((24,17), f"PANDA CONTRIBUTION RUN  •  {username.upper()}",
                font=font(15,True), fill=(245,247,250))
        dr.text((24,40),"Every contribution is a snack  •  Panda runs  •  Code gets eaten",
                font=font(10), fill=(125,211,252))
        dr.line((24,58,W-24,58), fill=(57,211,83), width=1)

        # Cells, with the currently eaten cell dimmed.
        current = int((f / frame_count) * len(route))
        for d in days:
            x,y,c=d["x"],d["y"],d["count"]
            x0=left+x*(cell+gap); y0=top+y*(cell+gap)
            fill=color(c)
            idx=next((i for i,z in enumerate(route) if z["x"]==x and z["y"]==y),None)
            if idx is not None and idx < current:
                fill=(10,35,23)
            dr.rounded_rectangle((x0,y0,x0+cell,y0+cell), radius=3, fill=fill)

        # Panda location: center on current contribution cell.
        d=route[min(current, len(route)-1)]
        cx=left+d["x"]*(cell+gap)+cell//2
        cy=top+d["y"]*(cell+gap)+cell//2
        bob=-2 if f%2 else 0
        px,py=cx-10,cy-10+bob

        # cute panda
        dr.ellipse((px,py,px+20,py+20), fill=(245,247,250))
        dr.ellipse((px-2,py-2,px+7,py+7), fill=(12,16,20))
        dr.ellipse((px+13,py-2,px+22,py+7), fill=(12,16,20))
        dr.ellipse((px+1,py+7,px+8,py+15), fill=(12,16,20))
        dr.ellipse((px+12,py+7,px+19,py+15), fill=(12,16,20))
        dr.ellipse((px+5,py+9,px+7,py+11), fill=(255,255,255))
        dr.ellipse((px+13,py+9,px+15,py+11), fill=(255,255,255))
        dr.ellipse((px+8,py+13,px+12,py+17), fill=(12,16,20))
        if f%4<2:
            dr.arc((px+8,py+14,px+13,py+19),0,180,fill=(12,16,20),width=1)
        else:
            dr.line((px+9,py+17,px+12,py+17),fill=(12,16,20),width=1)
        dr.ellipse((px+1,py+18,px+8,py+21), fill=(12,16,20))
        dr.ellipse((px+12,py+18,px+19,py+21), fill=(12,16,20))

        # snack particles at the current cell.
        if f%3==0:
            dr.text((px+18,py-8),"*",font=font(12,True),fill=(163,255,122))

        dr.ellipse((24,195,34,205),fill=(57,211,83))
        dr.text((42,193),f"{total:,} total contributions",
                font=font(10),fill=(156,163,175))
        dr.text((W-225,193),"STATUS: EATING CODE ✓",
                font=font(10,True),fill=(74,222,128))
        frames.append(im)

    OUT.parent.mkdir(parents=True,exist_ok=True)
    frames[0].save(OUT,save_all=True,append_images=frames[1:],
                   duration=70,loop=0,optimize=True)
    print(f"Generated {OUT} with {len(frames)} frames.")

if __name__=="__main__":
    main()
