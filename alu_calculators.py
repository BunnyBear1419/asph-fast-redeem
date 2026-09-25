"""Pure calculators for Shohan's Companion. Inputs are explicit; no game data is invented."""
from __future__ import annotations
from dataclasses import dataclass
import re
from typing import Any, Mapping
from alu_data import ALUDataStore, VerificationStatus

def number(value: Any) -> float | None:
    try:
        if value is None or not str(value).strip(): return None
        return float(str(value).replace(",","").replace("%","").strip())
    except (TypeError, ValueError): return None

def parse_stats(value: Any) -> dict[str,float]:
    if not value: return {}
    out={}
    for m in re.finditer(r"([A-Za-z][A-Za-z _-]{1,30})\s*(?:=|:|\s)\s*(-?\d+(?:\.\d+)?)",str(value)):
        key=re.sub(r"[^a-z0-9]+","_",m.group(1).strip().casefold()).strip("_")
        if key: out[key]=float(m.group(2))
    return out

def compare_stats(a: Mapping[str,float], b: Mapping[str,float]) -> list[dict[str,Any]]:
    rows=[]
    for key in sorted(set(a)|set(b)):
        av,bv=a.get(key),b.get(key)
        delta=None if av is None or bv is None else bv-av
        pct=None if delta is None or av==0 else delta/av*100
        rows.append({"stat":key,"a":av,"b":bv,"delta":delta,"percent":pct})
    return rows

def hunt_estimate(current: float,target: float,drop_rate: float)->dict[str,float]:
    if drop_rate<=0: raise ValueError("Drop rate must be greater than zero.")
    missing=max(0.0,target-current)
    return {"missing":missing,"expected_attempts":missing/(drop_rate/100),"drop_rate":drop_rate}

def priority_plan(days:float|None,reward:float|None,progress:float|None,readiness:float|None)->dict[str,float]:
    urgency=100 if days is not None and days<=0 else max(0,100-(min(days if days is not None else 30,30)/30*100))
    reward=max(0,min(100,reward or 0)); progress=max(0,min(100,progress or 0)); readiness=max(0,min(100,readiness or 0))
    score=urgency*.35+reward*.25+progress*.20+readiness*.20
    return {"score":round(score,2),"urgency":round(urgency,2),"reward":round(reward,2),"progress":round(progress,2),"readiness":round(readiness,2)}

def race_model(a:Mapping[str,float],b:Mapping[str,float],races:int)->dict[str,Any]:
    keys=sorted(set(a)&set(b))
    if not keys: raise ValueError("At least one shared numeric stat is required.")
    av=sum(a[k] for k in keys)/len(keys); bv=sum(b[k] for k in keys)/len(keys); total=av+bv
    share=.5 if total==0 else av/total
    return {"shared_stats":keys,"a_score":av,"b_score":bv,"a_share":share,"b_share":1-share,"expected_a_wins":share*max(1,races),"expected_b_wins":(1-share)*max(1,races)}

def rating_difference(rating:float,reference:float)->dict[str,float]:
    return {"rating":rating,"reference":reference,"difference":rating-reference}

def event_plan(attempts:float|None,progress:float|None,target:float|None)->dict[str,Any]:
    remaining=None if progress is None or target is None else max(0,target-progress)
    pct=None if progress is None or not target else max(0,min(100,progress/target*100))
    return {"attempts":attempts,"progress":progress,"target":target,"remaining":remaining,"completion_percent":pct}

def search_summary(store:ALUDataStore,kind:str,query:str)->list[dict[str,Any]]:
    if kind=="cars": rows=store.search_cars(query)
    elif kind=="tracks": rows=store.search_tracks(query)
    elif kind=="events": rows=store.search_events(query)
    else: raise ValueError("Unsupported search kind")
    return [{"id":x.id,"name":x.name,"verification":x.verification.value,"source":x.source} for x in rows[:25]]
