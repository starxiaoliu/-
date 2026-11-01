import {describe,it,expect} from 'vitest'
import {correction,type Question} from './api'
describe('校验字段',()=>{it('清空答案保存为未知，不默认成未作答或 A',()=>{
 const q={number:1,module:'政治理论',subtype:'',page_start:1,page_end:1,correct_answer:'',user_answer:''} as Question
 expect(correction(q).correct_answer).toBeNull()
 expect(correction(q).user_answer).toBeNull()
})})
