export interface Question {id:string;number:number;module:string;subtype:string;page_start:number;page_end:number;correct_answer:string|null;user_answer:string|null;warnings:string[];confidence:string;answer_status:string;checked?:boolean}
export interface Paper {id:string;title:string;page_count:number;parse_status:string;warnings:string[];questions?:Question[];total?:number;completed?:number;accuracy?:number|null;collection_kind?:'full'|'topic';expected_count?:number|null}
export async function api<T>(path:string, init?:RequestInit):Promise<T> {
 const r=await fetch('/api'+path,init)
 const body=await r.json()
 if(!r.ok) throw new Error(typeof body.error==='string'?body.error:JSON.stringify(body.error||body.detail))
 return body.data
}
export function correction(q:Question){
 return {number:q.number,module:q.module,subtype:q.subtype,page_start:q.page_start,page_end:q.page_end,correct_answer:q.correct_answer||null,user_answer:q.user_answer||null,checked:!!q.checked}
}
export interface Review {status:string;attempt_flags:string[];tag_ids:string[];note:string;correct_method:string;next_time_rule:string;review_later:boolean;updated_at?:string}
export interface Tag {code:string;label:string;module:string;subtype:string;origin:string}
