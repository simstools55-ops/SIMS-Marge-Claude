import pytest
from src.merge_engine import assess_merge, validate_request

def art(i,q,body,clicks=10,imp=100,pos=8,**kw):
    d={"article_id":i,"url":"https://x/"+i,"article_title":q,"article_body":body,"main_query":q,"queries":[q],"clicks":clicks,"impressions":imp,"ctr":clicks/imp,"position":pos,"search_intent":q}
    d.update(kw); return d

def req(a,b,**kw):
    d={"case_id":"CASE-20260805-A000001-001","treatment_request_id":"TRQ-001","target_articles":[a,b],"scope":{}}
    d.update(kw); return d

def test_missing_case_id():
    r=req(art('A1','wifi error','same text '*30),art('A2','wifi error','same text '*30)); del r['case_id']; assert 'missing:case_id' in validate_request(r)
def test_requires_two_articles(): assert 'target_articles:minItems=2' in validate_request({"case_id":"C","treatment_request_id":"T","target_articles":[]})
def test_duplicate_article_id(): assert any('duplicate_article_id' in x for x in validate_request(req(art('A1','q','x'),art('A1','q','y'))))
def test_confirmed_merge(): assert assess_merge(req(art('A1','wifi error','same text '*50),art('A2','wifi error','same text '*48)))['merge_decision']=='MERGE_REQUIRED'
def test_keep_both_different_intent(): assert assess_merge(req(art('A1','wifi setup','router setting '*40),art('A2','excel formula','spreadsheet function '*40)))['merge_decision']=='KEEP_BOTH'
def test_role_separation():
    a=art('A1','notion japan','company salary overview '*30); b=art('A2','notion 採用','company jobs hiring '*30); b['search_intent']='notion japan recruitment'
    assert assess_merge(req(a,b))['merge_decision'] in ('ROLE_SEPARATION_REQUIRED','KEEP_BOTH')
def test_low_evidence(): assert assess_merge(req(art('A1','q','same '*30,0,1),art('A2','q','same '*30,0,2)))['merge_decision']=='EVIDENCE_INSUFFICIENT'
def test_primary_prefers_performance():
    x=assess_merge(req(art('A1','q','same '*30,100,1000,pos=3),art('A2','q','same '*30,5,100,pos=12))); assert x['primary_article_id']=='A1'
def test_preservation_map():
    x=assess_merge(req(art('A1','q','same '*30,preservation_items=['体験談']),art('A2','q','same '*30,preservation_items=['比較表']))); assert len(x['merge_plan']['preservation_map'])==2
def test_writer_referral_on_merge():
    x=assess_merge(req(art('A1','q','same '*30),art('A2','q','same '*30))); assert any(r['target_product']=='WRITER' for r in x['follow_up_referrals'])
def test_creator_referral_for_separate_intent():
    b=art('A2','q','same '*30,separate_intent_candidate='別意図'); x=assess_merge(req(art('A1','q','same '*30),b)); assert any(r['target_product']=='CREATOR' for r in x['follow_up_referrals'])
def test_redirect_user_decision():
    x=assess_merge(req(art('A1','q','same '*30,backlinks=3),art('A2','q','same '*30),scope={'redirect_allowed':True})); assert any(i['type']=='REDIRECT_DECISION' for i in x['user_decision_items'])
def test_rollback_always_present(): assert assess_merge(req(art('A1','q','same '*30),art('A2','q','same '*30)))['merge_plan']['rollback_plan']
def test_ids_preserved():
    x=assess_merge(req(art('A1','q','same '*30),art('A2','q','same '*30))); assert x['case_id']=='CASE-20260805-A000001-001' and x['treatment_request_id']=='TRQ-001'
