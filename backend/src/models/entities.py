from sqlalchemy import Column,Integer,String,Float,Boolean,JSON,Text,ForeignKey,UniqueConstraint
from src.config.database import Base
class User(Base):
 __tablename__='users'
 id=Column(Integer,primary_key=True);email=Column(String(100),unique=True,nullable=False);password=Column(String(200));role=Column(String(20))
class Pair(Base):
 __tablename__='pairs'
 id=Column(Integer,primary_key=True);code=Column(String(60),unique=True,nullable=False);team=Column(String(40));before=Column(Float,nullable=True);after=Column(Float,nullable=True);note=Column(Text,default='')
class Evaluation(Base):
 __tablename__='evaluations'
 id=Column(Integer,primary_key=True);name=Column(String(100));team=Column(String(40));state=Column(String(20),default='queued');result=Column(JSON,nullable=True);error=Column(Text,default='')
class Adoption(Base):
 __tablename__='adoptions'
 id=Column(Integer,primary_key=True);evaluation_id=Column(Integer,ForeignKey('evaluations.id'));decision=Column(String(30));note=Column(Text);status=Column(String(20),default='draft')
class Audit(Base):
 __tablename__='audits'
 id=Column(Integer,primary_key=True);actor=Column(String(100));action=Column(String(200));created=Column(String(40))
class Experiment(Base):
 __tablename__='experiments'
 id=Column(Integer,primary_key=True);name=Column(String(100));seed=Column(Integer);treated_count=Column(Integer);state=Column(String(20),default='registering');assigned_at=Column(String(40),default='');created=Column(String(40),default='')
class ExperimentTeam(Base):
 __tablename__='experiment_teams'
 __table_args__=(UniqueConstraint('experiment_id','name'),)
 id=Column(Integer,primary_key=True);experiment_id=Column(Integer,ForeignKey('experiments.id'));name=Column(String(40));assigned_group=Column(String(10),nullable=True)
class ExperimentAdvisor(Base):
 __tablename__='experiment_advisors'
 __table_args__=(UniqueConstraint('experiment_id','code'),)
 id=Column(Integer,primary_key=True);experiment_id=Column(Integer,ForeignKey('experiments.id'));team_id=Column(Integer,ForeignKey('experiment_teams.id'));code=Column(String(60))
class LedgerEntry(Base):
 __tablename__='ledger_entries'
 id=Column(Integer,primary_key=True);experiment_id=Column(Integer,ForeignKey('experiments.id'));advisor_id=Column(Integer,ForeignKey('experiment_advisors.id'),unique=True);assigned_script=Column(String(10));executed_script=Column(String(10),nullable=True);before=Column(Float,nullable=True);after=Column(Float,nullable=True);late=Column(Boolean,default=False);updated=Column(String(40),default='')
class Closing(Base):
 __tablename__='closings'
 id=Column(Integer,primary_key=True);experiment_id=Column(Integer,ForeignKey('experiments.id'));attempt=Column(Integer);state=Column(String(20),default='collecting');snapshot=Column(JSON,nullable=True);result=Column(JSON,nullable=True);error=Column(Text,default='');created=Column(String(40),default='');finished=Column(String(40),default='')
