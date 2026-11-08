import csv,sys
sys.stdout.reconfigure(encoding="utf-8")
def rows(s): return list(csv.DictReader(open(f"logs/vote_v2-408-429{s}.csv",encoding="utf-8-sig")))
def load(s): return {(r["page"],r["main"],r["new"]):r for r in rows(s) if r["outcome"]=="change"}
s=sys.argv[1]; b=load(""); g=load(s); gall={(r["page"],r["main"]):r for r in rows(s)}
print("EXTRA")
for k in sorted(set(g)-set(b)): r=g[k]; print(" ",k[0],r["script"],repr(r["main"]),"->",repr(r["new"]),"| flash",r["flash"],"mdz",r["mdz"])
print("MISSED")
for k in sorted(set(b)-set(g)):
    r=gall.get((k[0],k[1])); print(" ",k[0],repr(k[1]),"->",repr(k[2]),"| judge:",r and r["judge"], r and r["outcome"])
