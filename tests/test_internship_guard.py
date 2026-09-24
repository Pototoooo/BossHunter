from unittest.mock import patch
import pytest
from bosshunter.employment import classify_employment,internship_rejection
from bosshunter.ai.prefilter import quick_score
from bosshunter.collection.models import classify_recruitment_type,PlatformCollectionRequest
from bosshunter.collection.platforms.boss import BossCollector,JS_VERIFY_INTERNSHIP_FILTER,build_boss_filter_query
from test_boss_collector import BossCollectorCollectionTests
C={'profile':{'allow_internship':True,'filter_unparsed_salary':False},'platforms':{'boss':{'search':{'filters':{'job_type':['实习']}}}}}
@pytest.mark.parametrize('title,jd,expected',[
 ('Go实习生','开发','internship'),('Backend intern','work','internship'),
 ('后端开发','职位类型：实习','internship'),('校招开发','应届生','unknown'),
 ('Java开发','有实习经历优先','unknown'),('非实习后端','开发','full_time'),
 ('实习生','职位类型：全职','unknown'),('兼职开发','','part_time')])
def test_classify(title,jd,expected):
 j={'title':title,'jd':jd,'salary':'10-20K'}
 assert classify_employment(j)==expected
 assert bool(internship_rejection(j,C))==(expected!='internship')
 assert (quick_score(j,C)[0]>0)==(expected=='internship')
def test_scope_and_classification():
 assert not internship_rejection({'title':'全职','source_platform':'zhilian'},C)
 assert not internship_rejection({'title':'全职'}, {})
 assert classify_recruitment_type('Go实习生')=='unknown'
 assert 'jobType=1902' in build_boss_filter_query({'job_type':['实习']})
@pytest.mark.parametrize('title,jd,count',[('Go实习生','开发',1),('正式开发','开发',0),('后端开发','职位类型：实习',1),('校招开发','有实习经历优先',0)])
def test_collector_detail_guard(title,jd,count):
 helper=BossCollectorCollectionTests()
 row={'title':title,'company':'测试企业','url':'/job_detail/guard.html','salary':'10-20K'}
 browser=helper._make_browser(list_jobs=[row],detail={**row,'jd':jd})
 original=browser.evaluate
 browser.evaluate=lambda t,s: True if s==JS_VERIFY_INTERNSHIP_FILTER else original(t,s)
 hooks,items=helper._make_hooks()
 with patch('bosshunter.collection.platforms.boss.time.sleep'):
  BossCollector(browser=browser,config=C,throttle_factory=lambda **kw:helper._make_throttle(),sleep=lambda _:None).collect(PlatformCollectionRequest('boss',['Go'],['深圳'],{'深圳':'101280600'},max_pages=1,filters={'job_type':['实习']}),hooks)
 assert len(items)==count
def test_filter_not_applied_stops():
 helper=BossCollectorCollectionTests();hooks,items=helper._make_hooks()
 result=BossCollector(browser=helper._make_browser(),sleep=lambda _:None,throttle_factory=lambda **kw:helper._make_throttle()).collect(PlatformCollectionRequest('boss',['Go'],['深圳'],{'深圳':'101280600'},max_pages=1,filters={'job_type':['实习']}),hooks)
 assert result.reason_code=='internship_filter_not_applied'
 assert items==[]

def test_sender_blocks_historical_nonintern_before_browser():
 from unittest.mock import MagicMock
 from bosshunter.executor.sender import send_greetings
 from copy import deepcopy
 c=deepcopy(C)
 with patch('bosshunter.executor.sender.get_db',return_value=MagicMock()), patch('bosshunter.executor.sender.PlatformAccessGuard'), patch('bosshunter.executor.sender.get_jobs_ready_to_send',return_value=[{'id':'old','title':'校招工程师','jd':'有实习经历优先','source_platform':'boss'}]), patch('bosshunter.executor.sender._send_greeting_once') as send:
  assert send_greetings(c,force=True)==0
  assert c['_workbench_send_report']['employment_blocked_ids']==['old']
  send.assert_not_called()
