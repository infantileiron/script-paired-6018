import os,time,json,logging
from pathlib import Path
import redis
from src.config.database import Session
from src.models.entities import Evaluation,Closing,Experiment
from src.services.analysis import evaluate
from src.services.experiment import compute_closing
from src.services.business import now_iso
r=redis.Redis.from_url(os.environ['REDIS_URL'])
with Session() as recovery:
 for pending in recovery.query(Evaluation).filter(Evaluation.state.in_(['queued','running'])).all():
  pending.state='queued';r.rpush('paired:evaluations',pending.id)
 for pending in recovery.query(Closing).filter(Closing.state=='collecting').all():
  r.rpush('paired:closings',pending.id)
 recovery.commit()
while True:
 Path('/tmp/heartbeat').touch()
 try:
  item=r.blpop(['paired:evaluations','paired:closings'],timeout=3)
  if not item:continue
  queue=item[0].decode() if isinstance(item[0],bytes) else item[0]
  with Session() as s:
   if queue=='paired:evaluations':
    row=s.get(Evaluation,int(item[1]))
    if not row or row.state!='queued':continue
    snapshot=row.result['snapshot'];row.state='running';s.commit()
    try:
     row.result={**evaluate(snapshot),'snapshot':snapshot};row.state='done'
     Path('/artifacts/'+str(row.id)+'.json').write_text(json.dumps(row.result,ensure_ascii=False))
    except Exception as e:row.state='failed';row.error=str(e)
    s.commit()
   else:
    row=s.get(Closing,int(item[1]))
    if not row or row.state!='collecting':continue
    try:
     row.result=compute_closing(row.snapshot);row.state='done';row.finished=now_iso()
     experiment=s.get(Experiment,row.experiment_id)
     if experiment:experiment.state='closed'
     Path('/artifacts/closing-'+str(row.id)+'.json').write_text(json.dumps({'snapshot':row.snapshot,'result':row.result},ensure_ascii=False))
    except Exception as e:row.state='failed';row.error=str(e);row.finished=now_iso()
    s.commit()
 except Exception:logging.exception('worker');time.sleep(2)
