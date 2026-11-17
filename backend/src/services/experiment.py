"""团队随机试验的领域规则与结案计算。

纯标准库实现，不依赖 ORM / Web 框架，便于独立验证：
- 种子分配：固定数量团队换话术，其余维持原话术，结果可复现；
- 结案计算：团队等权比较平均改善，穷举保持换话术团队数的分配求双侧概率；
- ITT：偏离分配的顾问仍按原分配组分析；缺测整份失败，不插补不补零。
"""
import hashlib,json,math,random
from itertools import combinations
EXACT_LIMIT=200000
ITERATIONS=10000
TOLERANCE=1e-12
TREATED,CONTROL='换话术','原话术'
NEW,OLD='新话术','原话术'
class RuleError(ValueError):
 def __init__(self,message,status=409):super().__init__(message);self.status=status
def ensure_can_register(state):
 if state!='registering':raise RuleError('名册已锁定：分配后不可再登记团队或顾问')
def ensure_assignable(state,n_teams,treated_count,min_advisors):
 if state!='registering':raise RuleError('名册已锁定，不可重复分配')
 if n_teams<2:raise RuleError('至少登记2个团队才能随机分配',422)
 if not 1<=treated_count<=n_teams-1:raise RuleError('换话术团队数须介于1与团队数−1之间，保证换话术组与原话术组都有团队',422)
 if min_advisors<1:raise RuleError('每个团队至少登记1位顾问后再分配',422)
def ensure_can_record(state):
 if state not in('assigned','closed'):raise RuleError('随机分配并锁定名册后，才开始在发放台账记录实际执行')
def ensure_can_close(state,has_active):
 if state=='registering':raise RuleError('先完成随机分配再结案')
 if state=='closed':raise RuleError('已结案，结论冻结；晚到的执行记录保留为偏离，不改动旧结论')
 if has_active:raise RuleError('已有结案进行中，等待完成或失败后再重试；重试不会重复发放台账')
def mark_late(state):return state=='closed'
def assign_groups(team_ids,treated_count,seed):
 ids=sorted(team_ids);shuffled=ids[:];random.Random(seed).shuffle(shuffled)
 treated=set(shuffled[:treated_count])
 return {i:(TREATED if i in treated else CONTROL) for i in ids}
def assigned_script(group):return NEW if group==TREATED else OLD
def freeze_snapshot(experiment,teams,advisors,entries,now):
 by_advisor={e['advisor_id']:e for e in entries}
 ledger=[]
 for a in advisors:
  e=by_advisor.get(a['id'],{})
  ledger.append({'advisor_id':a['id'],'code':a['code'],'team_id':a['team_id'],'assigned_script':e.get('assigned_script'),'executed_script':e.get('executed_script'),'before':e.get('before'),'after':e.get('after')})
 payload={'teams':[{'id':t['id'],'name':t['name'],'group':t['assigned_group']} for t in teams],'ledger':ledger}
 return {'experiment':{'id':experiment['id'],'name':experiment['name'],'seed':experiment['seed'],'treated_count':experiment['treated_count']},'frozen_at':now,'checksum':hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),**payload}
def compute_closing(snapshot):
 teams=snapshot['teams'];ledger=snapshot['ledger'];seed=snapshot['experiment']['seed']
 missing=[e['code'] for e in ledger if e['executed_script'] is None or e['before'] is None or e['after'] is None]
 if missing:raise ValueError('缺测整份失败：%d 位顾问的执行或前后测不完整（%s）；补录后重新结案，不做插补或补零'%(len(missing),'、'.join(missing[:8])+('…' if len(missing)>8 else '')))
 by_team={}
 for e in ledger:by_team.setdefault(e['team_id'],[]).append(e)
 rows=[]
 for t in teams:
  entries=by_team.get(t['id'],[])
  if not entries:raise ValueError('缺测整份失败：团队 %s 没有任何发放台账记录'%t['name'])
  improvements=[e['after']-e['before'] for e in entries]
  rows.append({'team_id':t['id'],'name':t['name'],'group':t['group'],'advisors':len(entries),'improvement':sum(improvements)/len(improvements),'deviations':sum(1 for e in entries if e['executed_script']!=e['assigned_script'])})
 treated=[r for r in rows if r['group']==TREATED];control=[r for r in rows if r['group']==CONTROL]
 k,n=len(treated),len(rows)
 if k==0 or k==n:raise ValueError('分配结果必须同时包含换话术与原话术团队')
 tw,cw=1.0/k,1.0/(n-k)
 for r in rows:r['weight']=tw if r['group']==TREATED else cw;r['contribution']=r['improvement']*r['weight']
 treated_mean=sum(r['improvement'] for r in treated)*tw
 control_mean=sum(r['improvement'] for r in control)*cw
 diff=treated_mean-control_mean
 means=[r['improvement'] for r in rows];total_sum=sum(means);total=math.comb(n,k)
 def stat(combo):
  s=sum(means[j] for j in combo)
  return s/k-(total_sum-s)/(n-k)
 if total<=EXACT_LIMIT:
  extreme=sum(1 for c in combinations(range(n),k) if abs(stat(c))>=abs(diff)-TOLERANCE)
  p_value=extreme/total;method='exact';iterations=total
 else:
  rng=random.Random(seed);extreme=0
  for _ in range(ITERATIONS):
   if abs(stat(rng.sample(range(n),k)))>=abs(diff)-TOLERANCE:extreme+=1
  p_value=(extreme+1)/(ITERATIONS+1);method='monte-carlo-add-one';iterations=ITERATIONS
 name_of={t['id']:t['name'] for t in teams}
 deviations=[{'code':e['code'],'team':name_of.get(e['team_id']),'assigned_script':e['assigned_script'],'executed_script':e['executed_script']} for e in ledger if e['executed_script']!=e['assigned_script']]
 return {'teams_total':n,'treated_count':k,'advisors':len(ledger),'treated_mean':treated_mean,'control_mean':control_mean,'difference':diff,'p_value':p_value,'method':method,'iterations':iterations,'teams':rows,'deviations':deviations,'checksum':snapshot.get('checksum'),'seed':seed,'warning':'按团队等权比较平均改善，团队人数悬殊时不按顾问人数加权；偏离分配的顾问仍按原分配组分析（ITT）。双侧概率来自保持换话术团队数的全部或抽样分配。并行的原话术组吸收了同期行情变化，但团队数较少时检验力有限；统计结论不直接触发话术发布。'}
