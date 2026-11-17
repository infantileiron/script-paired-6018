import random
from src.config.database import Base,engine,Session
from src.models.entities import User,Pair,Experiment,ExperimentTeam,ExperimentAdvisor,LedgerEntry
from src.utils.security import hash_password
from src.services.business import now_iso
from src.services.experiment import assign_groups,assigned_script,TREATED
def seed_experiment(s):
 if s.query(Experiment).filter_by(name='11月续约话术随机试验').first():return
 now=now_iso()
 e=Experiment(name='11月续约话术随机试验',seed=20261115,treated_count=2,state='registering',created=now);s.add(e);s.flush()
 teams=[]
 for name in ('企业一组·甲班','企业一组·乙班','企业二组·甲班','企业二组·乙班'):
  t=ExperimentTeam(experiment_id=e.id,name=name);s.add(t);s.flush();teams.append(t)
 advisors=[]
 for i,t in enumerate(teams):
  for j in range(5):
   a=ExperimentAdvisor(experiment_id=e.id,team_id=t.id,code=f'SY-{i*5+j+1:03}');s.add(a);s.flush();advisors.append(a)
 groups=assign_groups([t.id for t in teams],e.treated_count,e.seed)
 for t in teams:t.assigned_group=groups[t.id]
 e.state='assigned';e.assigned_at=now
 rng=random.Random(20261115)
 for idx,a in enumerate(advisors):
  group=groups[a.team_id];script=assigned_script(group)
  executed=script
  if idx==0:executed='原话术' if script=='新话术' else '新话术'
  before=round(rng.uniform(58,85),1)
  after=round(min(100,before+rng.gauss(4 if group==TREATED else 1,5)),1)
  if idx==len(advisors)-1:after=None
  s.add(LedgerEntry(experiment_id=e.id,advisor_id=a.id,assigned_script=script,executed_script=executed,before=before,after=after,updated=now))
def seed():
 Base.metadata.create_all(engine);rng=random.Random(1115)
 with Session() as s:
  for role in ('admin','analyst','viewer'):
   email=role+'@demo.local'
   if not s.query(User).filter_by(email=email).first():s.add(User(email=email,role=role,password=hash_password('Demo123!')))
  for i in range(40):
   code=f'QY-{i+1:03}';before=round(rng.uniform(58,85),1);after=round(min(100,before+rng.gauss(4 if i<20 else 1,5)),1)
   if not s.query(Pair).filter_by(code=code).first():s.add(Pair(code=code,team='企业一组' if i<20 else '企业二组',before=None if i==38 else before,after=None if i==39 else after,note='前后各抽检5次客户沟通的平均得分；窗口均为7日'))
  seed_experiment(s)
  s.commit();print({'users':s.query(User).count(),'pairs':s.query(Pair).count(),'experiments':s.query(Experiment).count()})
if __name__=='__main__':seed()
