import os,json
import redis
from fastapi import APIRouter,Depends,HTTPException,Response
from sqlalchemy.exc import IntegrityError
from src.config.database import db
from src.models.entities import User,Pair,Evaluation,Adoption,Audit,Experiment,ExperimentTeam,ExperimentAdvisor,LedgerEntry,Closing
from src.schemas.business import Login,PairInput,EvaluationInput,AdoptionInput,ExperimentInput,ExperimentTeamInput,ExperimentAdvisorInput,LedgerInput
from src.middlewares.auth import current,editor,admin
from src.utils.security import verify,token
from src.services.business import audit,dump,now_iso
from src.services.experiment import RuleError,ensure_can_register,ensure_assignable,ensure_can_record,ensure_can_close,mark_late,assign_groups,assigned_script,freeze_snapshot
from src.controllers.business import ensure_evaluation,ensure_experiment,experiment_detail
router=APIRouter()
def queue():
 return redis.Redis.from_url(os.environ['REDIS_URL'])
def rules(fn,*args):
 try:return fn(*args)
 except RuleError as e:raise HTTPException(e.status,str(e))
@router.post('/auth/login')
def login(data:Login,s=Depends(db)):
 u=s.query(User).filter_by(email=data.email).first()
 if not u or not verify(data.password,u.password):raise HTTPException(401,'账号或密码错误')
 return {'token':token(u),'user':dump(u)}
@router.get('/me')
def me(u=Depends(current)):return dump(u)
@router.get('/pairs')
def pairs(u=Depends(current),s=Depends(db)):return [dump(r) for r in s.query(Pair).order_by(Pair.id).all()]
@router.post('/pairs')
def create_pair(data:PairInput,u=Depends(editor),s=Depends(db)):
 r=Pair(**data.model_dump());s.add(r)
 try:s.commit()
 except IntegrityError:s.rollback();raise HTTPException(409,'顾问编号已存在，每位顾问仅保留一组前后测')
 audit(s,u,'录入顾问配对 '+r.code);return dump(r)
@router.put('/pairs/{i}')
def edit_pair(i:int,data:PairInput,u=Depends(editor),s=Depends(db)):
 r=s.get(Pair,i)
 if not r:raise HTTPException(404,'配对记录不存在')
 for k,v in data.model_dump().items():setattr(r,k,v)
 try:s.commit()
 except IntegrityError:s.rollback();raise HTTPException(409,'顾问编号重复')
 audit(s,u,'修订配对 '+str(i));return dump(r)
@router.get('/evaluations')
def evaluations(u=Depends(current),s=Depends(db)):return [dump(r) for r in s.query(Evaluation).order_by(Evaluation.id.desc()).all()]
@router.post('/evaluations')
def evaluate(data:EvaluationInput,u=Depends(editor),s=Depends(db)):
 rows=[dump(r) for r in s.query(Pair).order_by(Pair.id).all() if data.team=='全部' or r.team==data.team]
 r=Evaluation(**data.model_dump(),result={'snapshot':rows});s.add(r);s.commit()
 try:queue().rpush('paired:evaluations',r.id)
 except redis.RedisError:r.state='failed';r.error='队列暂不可用，请稍后重新提交';s.commit();raise HTTPException(503,r.error)
 audit(s,u,'提交评估 '+str(r.id));return dump(r)
@router.get('/evaluations/{i}')
def detail(i:int,u=Depends(current),s=Depends(db)):return dump(ensure_evaluation(s,i))
@router.get('/evaluations/{i}/export')
def export(i:int,u=Depends(current),s=Depends(db)):
 r=ensure_evaluation(s,i)
 if r.state!='done':raise HTTPException(409,'仅成功评估可导出')
 return Response(json.dumps(dump(r),ensure_ascii=False,indent=2),media_type='application/json',headers={'Content-Disposition':f'attachment; filename="script-paired-{i}.json"'})
@router.get('/adoptions')
def adoptions(u=Depends(current),s=Depends(db)):return [dump(r) for r in s.query(Adoption).order_by(Adoption.id.desc()).all()]
@router.post('/adoptions')
def adoption(data:AdoptionInput,u=Depends(editor),s=Depends(db)):
 if ensure_evaluation(s,data.evaluation_id).state!='done':raise HTTPException(409,'评估完成后才能起草采纳意见')
 r=Adoption(**data.model_dump());s.add(r);s.commit();audit(s,u,'起草采纳意见 '+str(r.id));return dump(r)
@router.post('/adoptions/{i}/approve')
def approve(i:int,u=Depends(admin),s=Depends(db)):
 r=s.get(Adoption,i)
 if not r:raise HTTPException(404,'采纳意见不存在')
 if r.status!='draft':raise HTTPException(409,'已签核意见不可重复签核')
 r.status='approved';s.commit();audit(s,u,'签核意见 '+str(i));return dump(r)
@router.get('/audits')
def audits(u=Depends(admin),s=Depends(db)):return [dump(r) for r in s.query(Audit).order_by(Audit.id.desc()).limit(100)]
@router.get('/experiments')
def experiments(u=Depends(current),s=Depends(db)):return [dump(r) for r in s.query(Experiment).order_by(Experiment.id.desc()).all()]
@router.post('/experiments')
def create_experiment(data:ExperimentInput,u=Depends(editor),s=Depends(db)):
 r=Experiment(**data.model_dump(),state='registering',created=now_iso());s.add(r);s.commit()
 audit(s,u,'创建试验 '+str(r.id));return dump(r)
@router.get('/experiments/{i}')
def experiment(i:int,u=Depends(current),s=Depends(db)):return experiment_detail(s,ensure_experiment(s,i))
@router.post('/experiments/{i}/teams')
def add_team(i:int,data:ExperimentTeamInput,u=Depends(editor),s=Depends(db)):
 e=ensure_experiment(s,i);rules(ensure_can_register,e.state)
 r=ExperimentTeam(experiment_id=e.id,name=data.name);s.add(r)
 try:s.commit()
 except IntegrityError:s.rollback();raise HTTPException(409,'团队名称在该试验中已存在')
 audit(s,u,'登记团队 '+data.name);return dump(r)
@router.post('/experiments/{i}/advisors')
def add_advisor(i:int,data:ExperimentAdvisorInput,u=Depends(editor),s=Depends(db)):
 e=ensure_experiment(s,i);rules(ensure_can_register,e.state)
 t=s.get(ExperimentTeam,data.team_id)
 if not t or t.experiment_id!=e.id:raise HTTPException(422,'团队不属于该试验')
 r=ExperimentAdvisor(experiment_id=e.id,team_id=data.team_id,code=data.code);s.add(r)
 try:s.commit()
 except IntegrityError:s.rollback();raise HTTPException(409,'顾问编号已存在于该试验名册')
 audit(s,u,'登记顾问 '+data.code);return dump(r)
@router.post('/experiments/{i}/assign')
def assign(i:int,u=Depends(editor),s=Depends(db)):
 e=ensure_experiment(s,i)
 teams=s.query(ExperimentTeam).filter_by(experiment_id=e.id).order_by(ExperimentTeam.id).all()
 advisors=s.query(ExperimentAdvisor).filter_by(experiment_id=e.id).order_by(ExperimentAdvisor.id).all()
 counts={t.id:0 for t in teams}
 for a in advisors:counts[a.team_id]=counts.get(a.team_id,0)+1
 rules(ensure_assignable,e.state,len(teams),e.treated_count,min(counts.values()) if counts else 0)
 groups=assign_groups([t.id for t in teams],e.treated_count,e.seed)
 for t in teams:t.assigned_group=groups[t.id]
 issued=0
 for a in advisors:
  if not s.query(LedgerEntry).filter_by(advisor_id=a.id).first():
   s.add(LedgerEntry(experiment_id=e.id,advisor_id=a.id,assigned_script=assigned_script(groups[a.team_id]),updated=now_iso()));issued+=1
 e.state='assigned';e.assigned_at=now_iso();s.commit()
 audit(s,u,'随机分配并锁定名册 试验'+str(e.id)+'（发放台账 '+str(issued)+' 条）');return experiment_detail(s,e)
@router.post('/experiments/{i}/ledger')
def record_ledger(i:int,data:LedgerInput,u=Depends(editor),s=Depends(db)):
 e=ensure_experiment(s,i);rules(ensure_can_record,e.state)
 a=s.get(ExperimentAdvisor,data.advisor_id)
 if not a or a.experiment_id!=e.id:raise HTTPException(422,'顾问不属于该试验名册')
 entry=s.query(LedgerEntry).filter_by(advisor_id=a.id).first()
 if not entry:
  t=s.get(ExperimentTeam,a.team_id)
  entry=LedgerEntry(experiment_id=e.id,advisor_id=a.id,assigned_script=assigned_script(t.assigned_group));s.add(entry)
 entry.executed_script=data.executed_script;entry.before=data.before;entry.after=data.after
 late=mark_late(e.state);entry.late=bool(entry.late or late);entry.updated=now_iso();s.commit()
 audit(s,u,('记录晚到执行 ' if late else '记录执行 ')+a.code);return experiment_detail(s,e)
@router.post('/experiments/{i}/close')
def close(i:int,u=Depends(editor),s=Depends(db)):
 e=ensure_experiment(s,i)
 active=s.query(Closing).filter_by(experiment_id=e.id,state='collecting').count()
 rules(ensure_can_close,e.state,active>0)
 teams=[dump(t) for t in s.query(ExperimentTeam).filter_by(experiment_id=e.id).order_by(ExperimentTeam.id).all()]
 advisors=[dump(a) for a in s.query(ExperimentAdvisor).filter_by(experiment_id=e.id).order_by(ExperimentAdvisor.id).all()]
 entries=[dump(x) for x in s.query(LedgerEntry).filter_by(experiment_id=e.id).all()]
 snapshot=freeze_snapshot(dump(e),teams,advisors,entries,now_iso())
 attempt=s.query(Closing).filter_by(experiment_id=e.id).count()+1
 c=Closing(experiment_id=e.id,attempt=attempt,state='collecting',snapshot=snapshot,created=now_iso());s.add(c);s.commit()
 try:queue().rpush('paired:closings',c.id)
 except redis.RedisError:c.state='failed';c.error='队列暂不可用，请稍后重新提交';c.finished=now_iso();s.commit();raise HTTPException(503,c.error)
 audit(s,u,'提交结案 试验'+str(e.id)+' 第'+str(attempt)+'次');return dump(c)
@router.get('/experiments/{i}/export')
def export_experiment(i:int,u=Depends(current),s=Depends(db)):
 e=ensure_experiment(s,i)
 done=s.query(Closing).filter_by(experiment_id=e.id,state='done').order_by(Closing.attempt.desc()).first()
 if not done:raise HTTPException(409,'仅结案成功的试验可导出')
 payload={**experiment_detail(s,e),'conclusion':done.result,'snapshot':done.snapshot}
 return Response(json.dumps(payload,ensure_ascii=False,indent=2),media_type='application/json',headers={'Content-Disposition':f'attachment; filename="script-experiment-{i}.json"'})
