/** @typedef {{id:number,code:string,team:string,before:number|null,after:number|null,note:string}} Pair */
/** @typedef {{id:number,name:string,team:string,state:string,result:object,error:string}} Evaluation */
/** @typedef {{id:number,evaluation_id:number,decision:string,note:string,status:string}} Adoption */
/** @typedef {{id:number,name:string,seed:number,treated_count:number,state:string,assigned_at:string,created:string}} Experiment */
/** @typedef {{id:number,experiment_id:number,name:string,assigned_group:string|null,advisors:number}} ExperimentTeam */
/** @typedef {{id:number,code:string,team_id:number,team_name:string}} ExperimentAdvisor */
/** @typedef {{id:number|null,advisor_id:number,code:string,team_id:number,team_name:string,assigned_script:string|null,executed_script:string|null,before:number|null,after:number|null,improvement:number|null,cross_group:boolean,late:boolean,updated:string|null}} LedgerRow */
/** @typedef {{id:number,attempt:number,state:string,result:object|null,error:string,created:string,finished:string}} Closing */
