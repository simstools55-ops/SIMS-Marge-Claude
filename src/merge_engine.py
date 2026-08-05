from __future__ import annotations
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Dict, List

REQUIRED_ARTICLE_FIELDS = {"article_id", "url", "article_title", "article_body", "main_query", "clicks", "impressions", "ctr", "position"}


def validate_request(request: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    for field in ("case_id", "treatment_request_id", "target_articles"):
        if not request.get(field): errors.append(f"missing:{field}")
    articles = request.get("target_articles") or []
    if len(articles) < 2: errors.append("target_articles:minItems=2")
    ids=set()
    for idx,a in enumerate(articles):
        missing=REQUIRED_ARTICLE_FIELDS-set(a)
        errors += [f"target_articles[{idx}].missing:{x}" for x in sorted(missing)]
        aid=a.get("article_id")
        if aid in ids: errors.append(f"duplicate_article_id:{aid}")
        ids.add(aid)
    return errors


def _tokens(text: str) -> set[str]:
    return {x.strip().lower() for x in text.replace("/"," ").replace("｜"," ").split() if x.strip()}


def _query_overlap(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    qa=set([a.get("main_query","")] + list(a.get("queries",[])))
    qb=set([b.get("main_query","")] + list(b.get("queries",[])))
    qa={x.strip().lower() for x in qa if x}; qb={x.strip().lower() for x in qb if x}
    if not qa or not qb: return 0.0
    return len(qa & qb)/len(qa | qb)


def _intent_overlap(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    ia=(a.get("search_intent") or a.get("main_query") or "").lower()
    ib=(b.get("search_intent") or b.get("main_query") or "").lower()
    return SequenceMatcher(None,ia,ib).ratio()


def _content_overlap(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    return SequenceMatcher(None,(a.get("article_body") or "")[:12000],(b.get("article_body") or "")[:12000]).ratio()


def _article_score(a: Dict[str, Any]) -> float:
    clicks=max(float(a.get("clicks",0)),0); impressions=max(float(a.get("impressions",0)),0)
    ctr=max(float(a.get("ctr",0)),0); position=max(float(a.get("position",100)),0.1)
    backlinks=max(float(a.get("backlinks",0)),0); internal=max(float(a.get("internal_link_count",0)),0)
    unique=max(float(a.get("unique_value_score",0.5)),0); strategic=max(float(a.get("strategic_fit_score",0.5)),0)
    seo=min(clicks/1000,1)*0.35 + min(impressions/20000,1)*0.2 + min(ctr/0.1,1)*0.2 + min(10/position,1)*0.25
    authority=min(backlinks/20,1)*0.6 + min(internal/30,1)*0.4
    content=min(unique,1)
    return round(seo*35 + authority*20 + content*30 + min(strategic,1)*15,2)


def assess_merge(request: Dict[str, Any]) -> Dict[str, Any]:
    errors=validate_request(request)
    if errors:
        return {"result_status":"VALIDATION_FAILED","errors":errors,"merge_decision":"EVIDENCE_INSUFFICIENT"}
    articles=request["target_articles"]
    pairs=[]
    for i in range(len(articles)):
        for j in range(i+1,len(articles)):
            q=_query_overlap(articles[i],articles[j]); intent=_intent_overlap(articles[i],articles[j]); content=_content_overlap(articles[i],articles[j])
            pairs.append({"articles":[articles[i]["article_id"],articles[j]["article_id"]],"query_overlap":round(q,3),"intent_overlap":round(intent,3),"content_overlap":round(content,3)})
    qavg=sum(x["query_overlap"] for x in pairs)/len(pairs); iavg=sum(x["intent_overlap"] for x in pairs)/len(pairs); cavg=sum(x["content_overlap"] for x in pairs)/len(pairs)
    evidence_sufficient=all(float(a.get("impressions",0))>=10 or a.get("backlinks",0)>0 for a in articles)
    if not evidence_sufficient:
        confidence="POSSIBLE"; decision="EVIDENCE_INSUFFICIENT"
    elif qavg>=0.45 and iavg>=0.75 and cavg>=0.45:
        confidence="CONFIRMED"; decision="MERGE_REQUIRED"
    elif iavg>=0.72 and (qavg>=0.2 or cavg>=0.3):
        confidence="LIKELY"; decision="MERGE_REQUIRED"
    elif iavg<0.55:
        confidence="UNLIKELY"; decision="KEEP_BOTH"
    else:
        confidence="POSSIBLE"; decision="ROLE_SEPARATION_REQUIRED"
    scored=sorted([{"article_id":a["article_id"],"score":_article_score(a)} for a in articles],key=lambda x:x["score"],reverse=True)
    primary=scored[0]["article_id"] if decision!="EVIDENCE_INSUFFICIENT" else None
    absorbed=[a["article_id"] for a in articles if a["article_id"]!=primary] if primary and decision=="MERGE_REQUIRED" else []
    preserved=[]
    for a in articles:
        for item in a.get("preservation_items",[]):
            preserved.append({"source_article_id":a["article_id"],"item":item,"action":"MOVE_TO_PRIMARY" if a["article_id"]!=primary else "KEEP_AS_IS"})
    user_items=[]
    if decision=="MERGE_REQUIRED":
        user_items.append({"type":"PRIMARY_ARTICLE_APPROVAL","required":True})
        if request.get("scope",{}).get("redirect_allowed") or any(a.get("backlinks",0)>0 for a in articles):
            user_items.append({"type":"REDIRECT_DECISION","required":True})
    referrals=[]
    if decision=="MERGE_REQUIRED": referrals.append({"target_product":"WRITER","treatment_type":"WRITER_FULL_REWRITE","reason":"Merge Planを原稿化する"})
    for a in articles:
        if a.get("separate_intent_candidate"):
            referrals.append({"target_product":"CREATOR","treatment_type":"CREATOR_INTENT_SPLIT","reason":a["separate_intent_candidate"]})
    return {
      "case_id":request["case_id"],"treatment_request_id":request["treatment_request_id"],"result_status":"SUCCESS" if decision!="EVIDENCE_INSUFFICIENT" else "EVIDENCE_INSUFFICIENT",
      "cannibalization_confidence":confidence,"merge_decision":decision,"pair_analysis":pairs,
      "primary_article_id":primary,"article_scores":scored,"absorbed_article_ids":absorbed,
      "merge_plan":{
        "primary_article_id":primary,"absorbed_article_ids":absorbed,"preservation_map":preserved,
        "query_mapping":[],"publication_sequence":["UPDATE_PRIMARY","VERIFY_PRIMARY","UPDATE_INTERNAL_LINKS","HANDLE_ABSORBED_ARTICLES","START_MONITORING"] if decision=="MERGE_REQUIRED" else [],
        "rollback_plan":["SAVE_ALL_ORIGINAL_ARTICLES","SAVE_METADATA_AND_LINKS","RECORD_REDIRECT_NOINDEX_STATE","DO_NOT_AUTO_ROLLBACK"]
      },
      "user_decision_items":user_items,"follow_up_referrals":referrals,
      "recommended_next_status":"TREATMENT_REVIEW_PENDING" if decision in ("MERGE_REQUIRED","ROLE_SEPARATION_REQUIRED") else "COMPLETED_NO_ACTION" if decision=="KEEP_BOTH" else "EVIDENCE_INSUFFICIENT"
    }
