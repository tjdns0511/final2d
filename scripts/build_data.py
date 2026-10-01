#!/usr/bin/env python3
import json,re,time,urllib.parse,urllib.request
from html.parser import HTMLParser
from pathlib import Path

UA="WarAtlas/1.0 (historical visualization; GitHub tjdns0511/final2d)"
LISTS=["List of wars: before 1000","List of wars: 1000–1499","List of wars: 1500–1799","List of wars: 1800–1899","List of wars: 1900–1944","List of wars: 1945–1989","List of wars: 1990–2002","List of wars: 2003–present"]

def get(url):
    q=urllib.request.Request(url,headers={"User-Agent":UA,"Api-User-Agent":UA})
    with urllib.request.urlopen(q,timeout=45) as r:return json.load(r)
def api(params):
    params["format"]="json";params["formatversion"]="2"
    return get("https://en.wikipedia.org/w/api.php?"+urllib.parse.urlencode(params))

class TableParser(HTMLParser):
    def __init__(self):
        super().__init__();self.in_table=self.in_tr=self.in_cell=False;self.cell="";self.href=None;self.rows=[];self.row=[]
    def handle_starttag(self,t,a):
        d=dict(a)
        if t=="table" and "wikitable" in d.get("class",""): self.in_table=True
        elif self.in_table and t=="tr": self.in_tr=True;self.row=[]
        elif self.in_tr and t in ("td","th"): self.in_cell=True;self.cell="";self.href=None
        elif self.in_cell and t=="a" and d.get("href","").startswith("./"): self.href=d["href"][2:]
    def handle_data(self,d):
        if self.in_cell:self.cell+=d
    def handle_endtag(self,t):
        if self.in_cell and t in ("td","th"):
            self.row.append((re.sub(r"\s+"," ",self.cell).strip(),self.href));self.in_cell=False
        elif self.in_tr and t=="tr":
            if self.row:self.rows.append(self.row)
            self.in_tr=False
        elif self.in_table and t=="table":self.in_table=False

def parse_year(s):
    s=s.replace("−","-").replace("–","-")
    m=re.search(r"(\d{1,4})\s*(BC|BCE)",s,re.I)
    if m:return -int(m.group(1))
    m=re.search(r"(?<!\d)(1[0-9]{3}|20[0-9]{2}|[1-9][0-9]{0,2})(?!\d)",s)
    return int(m.group(1)) if m else None
def collect_titles():
    titles={}
    for name in LISTS:
        page=api({"action":"parse","page":name,"prop":"text"})["parse"]["text"]
        p=TableParser();p.feed(page)
        for row in p.rows:
            texts=[x[0] for x in row]
            if len(row)<2:continue
            years=[parse_year(x) for x in texts[:2]]
            link=next((x[1] for x in row if x[1]),None)
            if not link:continue
            title=urllib.parse.unquote(link).replace("_"," ")
            if title.startswith(("File:","Help:","Special:","Category:")):continue
            st=years[0]
            if st is None or st < -2500:continue
            en=years[1] if len(years)>1 and years[1] is not None else st
            titles.setdefault(title,{"start":st,"end":en})
        time.sleep(.15)
    return titles
def claims_for(titles):
    out={}
    names=list(titles)
    for i in range(0,len(names),50):
        batch=names[i:i+50]
        r=api({"action":"query","prop":"pageprops","ppprop":"wikibase_item","redirects":"1","titles":"|".join(batch)})
        qids=[p.get("pageprops",{}).get("wikibase_item") for p in r["query"]["pages"]]
        qids=[q for q in qids if q]
        if not qids:continue
        wd=get("https://www.wikidata.org/w/api.php?"+urllib.parse.urlencode({"action":"wbgetentities","ids":"|".join(qids),"props":"claims|labels|sitelinks","languages":"en","sitefilter":"enwiki","format":"json"}))
        for q,e in wd["entities"].items():out[q]=e
        time.sleep(.12)
    return out
def amount(c):
    try:return float(c["mainsnak"]["datavalue"]["value"]["amount"].lstrip("+"))
    except:return None
def coord(c):
    try:
        v=c["mainsnak"]["datavalue"]["value"];return [v["longitude"],v["latitude"]]
    except:return None
def qtime(c):
    try:
        v=c["mainsnak"]["datavalue"]["value"];s=v["time"];y=int(s[1:5]) if s[0]=="-" else int(s[1:5]);return -y if s[0]=="-" else y
    except:return None
def first(cs,p,fn):
    for c in cs.get(p,[]):
        v=fn(c)
        if v is not None:return v
def main():
    base=collect_titles(); entities=claims_for(base); feats=[];seen=set()
    for q,e in entities.items():
        sl=e.get("sitelinks",{}).get("enwiki",{}).get("title"); 
        if not sl or sl not in base:continue
        c=e.get("claims",{}); xy=first(c,"P625",coord)
        if not xy:continue
        st=first(c,"P580",qtime) or first(c,"P585",qtime) or base[sl]["start"]
        en=first(c,"P582",qtime) or base[sl]["end"] or st
        if st is None or st < -2500:continue
        if en is None:en=st
        deaths=first(c,"P1120",amount)
        key=(q,xy[0],xy[1])
        if key in seen:continue
        seen.add(key)
        p={"qid":q,"name":e.get("labels",{}).get("en",{}).get("value",sl),"start":st,"end":en,"wikipedia":"https://en.wikipedia.org/wiki/"+urllib.parse.quote(sl.replace(" ","_"))}
        if deaths and deaths>0:p["deaths"]=round(deaths)
        feats.append({"type":"Feature","geometry":{"type":"Point","coordinates":xy},"properties":p})
    feats.sort(key=lambda f:(f["properties"]["start"],f["properties"]["name"]))
    Path("data").mkdir(exist_ok=True)
    Path("data/wars.geojson").write_text(json.dumps({"type":"FeatureCollection","features":feats},ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    print("wrote",len(feats),"located conflicts")
if __name__=="__main__":main()
