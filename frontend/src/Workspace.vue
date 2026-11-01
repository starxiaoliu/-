<script setup lang="ts">
import {ref,onMounted,computed} from 'vue'
import PdfViewer from './PdfViewer.vue'
import ReviewEditor from './ReviewEditor.vue'
import {api,type Question,type Review,type Tag} from './api'
type Row=Question & {review:Review}
const props=defineProps<{paperId:string;start?:number;startFilter?:string}>()
const rows=ref<Row[]>([]),tags=ref<Tag[]>([]),active=ref<Row>(),filter=ref(props.startFilter||'all'),module=ref(''),error=ref(''),editor=ref<InstanceType<typeof ReviewEditor>>()
const modules=computed(()=>[...new Set(rows.value.map(q=>q.module))])
const visible=computed(()=>rows.value.filter(q=>(!module.value||q.module===module.value)&&(filter.value==='all'||q.answer_status===filter.value||(filter.value==='later'&&q.review.review_later)||(filter.value==='pending'&&q.review.status!=='completed')||filter.value===q.review.status||q.review.attempt_flags.includes(filter.value))))
async function leave(){return !editor.value||await editor.value.flush()}
async function choose(q:Row){if(active.value?.id===q.id)return;if(!await leave())return;active.value=q;localStorage.setItem('lastQuestion:'+props.paperId,String(q.number))}
async function next(delta:number){if(!active.value)return;const i=rows.value.findIndex(q=>q.id===active.value!.id);const q=rows.value[i+delta];if(q)await choose(q)}
function addTag(t:Tag){if(!tags.value.some(x=>x.code===t.code))tags.value.push(t)}
onMounted(async()=>{try{rows.value=await api<Row[]>('/papers/'+props.paperId+'/questions');tags.value=await api<Tag[]>('/tags');const n=props.start||Number(localStorage.getItem('lastQuestion:'+props.paperId));active.value=rows.value.find(q=>q.number===n)||rows.value[0]}catch(e){error.value=String(e)}})
defineExpose({leave})
</script>
<template><el-alert v-if="error" :title="error" type="error"/><div class="workspace"><aside><el-select v-model="module" clearable placeholder="全部模块"><el-option v-for="m in modules" :key="m" :value="m"/></el-select><el-select v-model="filter"><el-option v-for="(label,key) in {all:'全部',wrong:'先看错题',correct:'答对',unanswered:'未作答',unknown:'未知',pending:'待复盘',completed:'已完成',later:'二刷',guessed:'蒙对',hesitant:'纠结',overtime:'超时'}" :key="key" :value="key" :label="label"/></el-select><p>{{visible.length}} 题 / 完成 {{rows.filter(q=>q.review.status==='completed').length}}</p><div class="question-grid"><button v-for="q in visible" :key="q.id" :class="{active:q.id===active?.id,wrong:q.answer_status==='wrong'}" @click="choose(q)">{{q.number}}<small>{{q.review.status==='completed'?'✓':q.answer_status==='wrong'?'错':q.answer_status==='correct'?'对':'?'}}{{q.review.review_later?'刷':''}}</small></button></div><p v-if="!visible.length">没有符合条件的题目</p></aside><PdfViewer v-if="active" :url="'/api/papers/'+paperId+'/pdf'" :page="active.page_start"/><div v-if="active"><ReviewEditor :key="active.id" ref="editor" :question="active" :initial="active.review" :tags="tags" @saved="r=>{if(active)active.review=r}" @tag-added="addTag"/><div class="toolbar"><el-button :disabled="active===rows[0]" @click="next(-1)">上一题</el-button><el-button :disabled="active===rows[rows.length-1]" @click="next(1)">下一题</el-button></div></div></div></template>
