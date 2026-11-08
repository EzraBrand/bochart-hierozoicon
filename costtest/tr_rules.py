import json,glob,sys,os,re
sys.stdout.reconfigure(encoding="utf-8")
ref={}
for f in glob.glob("data/entries/shafan/chunks/*.json"):
    b=os.path.basename(f).split("-"); ref[f"{b[0]}-{int(b[1])}"]=json.load(open(f,encoding="utf-8"))["blocks"]
AR=re.compile(r"[؀-ۿ][؀-ۿً-ْ ]*")
GR=re.compile(r"[Ͱ-Ͽἀ-῿][Ͱ-Ͽἀ-῿̀-ͯ]*(?:[ ,·.]+[Ͱ-Ͽἀ-῿][Ͱ-Ͽἀ-῿]*)*")
MARK=re.compile(r"\[(?:I{1,3}, \d+|col\. \d+)\]|\^\{[^}]+\}")
def stats(blocks):
    t="\n".join(b["text"] for b in blocks)
    ar=[m for m in AR.finditer(t) if m.group().strip()]
    ar_ok=sum(1 for m in ar if re.match(r"\s*\[", t[m.end():m.end()+3]))
    gr=list(GR.finditer(t)); gr_ok=sum(1 for m in gr if re.match(r"\s*\[", t[m.end():m.end()+3]))
    return dict(words=len(t.split()), marks=len(MARK.findall(t)), ar=f"{ar_ok}/{len(ar)}", gr=f"{gr_ok}/{len(gr)}",
                i=t.count("<i>"), bad=sum(t.lower().count(w) for w in ["coney","rock badger","rock-badger"]), pal=t.count("Palestin"), q=t.count("[?]"))
print("pilot     ", {k:stats(v) for k,v in ref.items() if k in ("text-1","text-5","text-10","notes-1")})
for d in sorted(glob.glob("costtest/translate_exp/*")):
    print(os.path.basename(d), {os.path.basename(f)[:-5]: stats(json.load(open(f,encoding="utf-8"))["blocks"]) for f in sorted(glob.glob(d+"/*.json"))})
