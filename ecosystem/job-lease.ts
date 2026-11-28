import type { Database } from "./d1-store";
export class JobLeases {
 constructor(private readonly db:Database){}
 private validate(scope:string,id:string,token:string,now:number){
  if(!scope.trim()||!id.trim()||!token.trim()||!Number.isSafeInteger(now)||now<0)throw new Error("invalid lease");
 }
 async claim(scope:string,id:string,token:string,now:number,ttl:number){
  this.validate(scope,id,token,now);
  if(!Number.isSafeInteger(ttl)||ttl<=0||!Number.isSafeInteger(now+ttl))throw new Error("invalid lease duration");
  const r=await this.db.prepare("INSERT INTO ecosystem_job_lease(scope,job_id,token,expires_at) VALUES(?,?,?,?) ON CONFLICT(scope,job_id) DO UPDATE SET token=excluded.token,expires_at=excluded.expires_at WHERE ecosystem_job_lease.completed_at IS NULL AND ecosystem_job_lease.expires_at<=? AND ecosystem_job_lease.token<>excluded.token").bind(scope,id,token,now+ttl,now).run();
  if(!r.success||typeof r.meta?.changes!=="number")throw new Error("claim failed");
  return r.meta.changes===1;
 }
 async complete(scope:string,id:string,token:string,now:number){
  this.validate(scope,id,token,now);
  const r=await this.db.prepare("UPDATE ecosystem_job_lease SET completed_at=? WHERE scope=? AND job_id=? AND token=? AND completed_at IS NULL AND expires_at>?").bind(now,scope,id,token,now).run();
  if(!r.success||typeof r.meta?.changes!=="number")throw new Error("completion failed");
  return r.meta.changes===1;
 }
}
