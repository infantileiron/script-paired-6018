from fastapi import HTTPException
from src.models.entities import Evaluation,Experiment,ExperimentTeam,ExperimentAdvisor,LedgerEntry,Closing
from src.services.business import dump
def ensure_evaluation(s,i):
 row=s.get(Evaluation,i)
 if not row:raise HTTPException(404,'评估任务不存在')
 return row
def ensure_experiment(s,i):
 row=s.get(Experiment,i)
 if not row:raise HTTPException(404,'试验不存在')
 return row
def experiment_detail(s,e):
 teams=s.query(ExperimentTeam).filter_by(experiment_id=e.id).order_by(ExperimentTeam.id).all()
 advisors=s.query(ExperimentAdvisor).filter_by(experiment_id=e.id).order_by(ExperimentAdvisor.id).all()
 entries={x.advisor_id:x for x in s.query(LedgerEntry).filter_by(experiment_id=e.id).all()}
 closings=s.query(Closing).filter_by(experiment_id=e.id).order_by(Closing.attempt.desc()).all()
 name_of={t.id:t.name for t in teams}
 ledger=[]
 for a in advisors:
  x=entries.get(a.id)
  row={'id':None,'advisor_id':a.id,'code':a.code,'team_id':a.team_id,'team_name':name_of.get(a.team_id),'assigned_script':None,'executed_script':None,'before':None,'after':None,'improvement':None,'cross_group':False,'late':False,'updated':None}
  if x:
   row.update({'id':x.id,'assigned_script':x.assigned_script,'executed_script':x.executed_script,'before':x.before,'after':x.after,'improvement':x.after-x.before if x.before is not None and x.after is not None else None,'cross_group':bool(x.assigned_script and x.executed_script and x.executed_script!=x.assigned_script),'late':bool(x.late),'updated':x.updated})
  ledger.append(row)
 history=[]
 for c in closings:
  d=dump(c);d.pop('snapshot',None);history.append(d)
 return {**dump(e),'teams':[{**dump(t),'advisors':sum(1 for a in advisors if a.team_id==t.id)} for t in teams],'advisors':[{'id':a.id,'code':a.code,'team_id':a.team_id,'team_name':name_of.get(a.team_id)} for a in advisors],'ledger':ledger,'closings':history}
