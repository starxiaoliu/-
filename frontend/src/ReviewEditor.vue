<script setup lang="ts">
import {ref,watch,onBeforeUnmount,computed} from 'vue'
import {api,type Question,type Review,type Tag} from './api'
import AiAssistant from './AiAssistant.vue'
const props=defineProps<{question:Question;initial:Review;tags:Tag[]}>()
const emit=defineEmits<{saved:[r:Review];tagAdded:[t:Tag]}>()
const key='review-draft:'+props.question.id
const error=ref(''),state=ref('已保存'),custom=ref('')
let initial=JSON.parse(JSON.stringify(props.initial))
try{const draft=localStorage.getItem(key);if(draft){initial=JSON.parse(draft);state.value='未保存（已恢复本地草稿）'}}catch{error.value='本地草稿读取失败'}
const form=ref<Review>(initial)
let timer:ReturnType<typeof setTimeout>|undefined,revision=0,savedRevision=0,inflight:Promise<boolean>|undefined
const candidates=computed(()=>props.tags.filter(t=>form.value.tag_ids.includes(t.code)||(t.origin!=='hidden'&&(!t.module||t.module===props.question.module||props.question.module.startsWith(t.module))&&(!t.subtype||!props.question.subtype||t.subtype===props.question.subtype))))
function persist(){try{localStorage.setItem(key,JSON.stringify(form.value))}catch{error.value='本地草稿存储失败，请立即点击保存';return false}return true}
watch(form,()=>{revision++;persist();state.value='未保存';clearTimeout(timer);timer=setTimeout(()=>void flush(),650)},{deep:true,flush:'sync'})
async function flush():Promise<boolean>{
 clearTimeout(timer)
 if(inflight){if(!await inflight)return false;return flush()}
 if(savedRevision===revision&&state.value==='已保存')return true
 const rev=revision,body=JSON.stringify(form.value)
 state.value='保存中'
 inflight=(async()=>{try{
 const r=await api<Review>('/questions/'+props.question.id+'/review',{method:'PUT',headers:{'Content-Type':'application/json'},body})
 savedRevision=rev
 if(revision===rev){state.value='已保存';localStorage.removeItem(key)}else{state.value='未保存'}
 error.value='';emit('saved',r);return true
 }catch(e){error.value=String(e);state.value='保存失败，草稿保留';persist();return false}})()
 const success=await inflight;inflight=undefined
 if(success&&revision!==rev)return flush()
 return success
}
async function addTag(){if(!custom.value.trim())return;try{const t=await api<Tag>('/tags',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({label:custom.value.trim(),module:props.question.module,subtype:props.question.subtype})});emit('tagAdded',t);if(!form.value.tag_ids.includes(t.code))form.value.tag_ids.push(t.code);custom.value=''}catch(e){error.value=String(e)}}
function complete(){if(form.value.status==='completed'){form.value.status='in_progress';return}if(![form.value.note,form.value.correct_method,form.value.next_time_rule].some(s=>s.trim())&&!form.value.tag_ids.length){error.value='请先写笔记或选择标签';return}form.value.status='completed';void flush()}
function beforeUnload(e:BeforeUnloadEvent){if(state.value!=='已保存'){persist();e.preventDefault()}}
window.addEventListener('beforeunload',beforeUnload)
onBeforeUnmount(()=>{clearTimeout(timer);window.removeEventListener('beforeunload',beforeUnload);if(state.value!=='已保存')persist()})
defineExpose({flush})
</script>
<template><section class="editor"><h2>第 {{question.number}} 题 · {{question.subtype||question.module}}</h2><p>我的答案 {{question.user_answer||'未知'}} · 正确答案 {{question.correct_answer||'未知'}} · {{question.answer_status}}</p><h3>作答情况</h3><el-checkbox-group v-model="form.attempt_flags"><el-checkbox label="蒙对 / 猜对" value="guessed"/><el-checkbox label="犹豫纠结" value="hesitant"/><el-checkbox label="明显超时" value="overtime"/><el-checkbox label="题目没看完" value="unread_stem"/></el-checkbox-group><h3>候选易错点</h3><p class="muted">仅为记录提示，请按自己的思考选择。</p><el-checkbox-group v-model="form.tag_ids"><el-checkbox v-for="t in candidates" :key="t.code" :value="t.code">{{t.label}}</el-checkbox></el-checkbox-group><div class="toolbar"><el-input v-model="custom" placeholder="自定义标签" @keyup.enter="addTag"/><el-button @click="addTag">添加标签</el-button></div><label>我的复盘心得<el-input v-model="form.note" type="textarea" :rows="10" placeholder="当时为什么这样选？关键遗漏是什么？下次碰到类似题时我第一步要做什么？"/></label><AiAssistant :question="question" :note="form.note" @append="text=>form.note+=(form.note.trim()?'\n\n':'')+text"/><el-collapse><el-collapse-item title="正确思路 / 下次识别信号"><label>正确思路 / 更快做法<el-input v-model="form.correct_method" type="textarea"/></label><label>下次识别信号<el-input v-model="form.next_time_rule" type="textarea"/></label></el-collapse-item></el-collapse><el-checkbox v-model="form.review_later">加入二刷</el-checkbox><div class="toolbar"><el-button type="primary" @click="complete">{{form.status==='completed'?'撤销完成':'标记已完成'}}</el-button><el-button @click="flush">保存 / 重试</el-button><span role="status">{{state}}</span></div><el-alert v-if="error" type="error" :closable="false" :title="error"/></section></template>
