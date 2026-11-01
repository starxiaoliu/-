<script setup lang="ts">
import {ref,watch,onBeforeUnmount,nextTick} from 'vue'
import {getDocument,GlobalWorkerOptions,type PDFDocumentProxy,type RenderTask} from 'pdfjs-dist'
import worker from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
GlobalWorkerOptions.workerSrc=worker
const props=defineProps<{url:string;page:number}>()
const canvas=ref<HTMLCanvasElement>(),current=ref(1),zoom=ref(1.2),count=ref(1),error=ref(''),loading=ref(true)
let doc:PDFDocumentProxy|undefined,task:RenderTask|undefined,sourceVersion=0,renderVersion=0,queue:Promise<void>=Promise.resolve()
function render(){
 const version=++renderVersion,target=doc,pageNumber=current.value,scale=zoom.value
 task?.cancel();loading.value=true
 queue=queue.catch(()=>{}).then(async()=>{
  if(version!==renderVersion||!target||!canvas.value)return
  try{
   const page=await target.getPage(pageNumber)
   if(version!==renderVersion||!canvas.value)return
   const viewport=page.getViewport({scale}),c=canvas.value
   c.width=viewport.width;c.height=viewport.height;c.dataset.renderedPage=''
   task=page.render({canvasContext:c.getContext('2d')!,viewport})
   await task.promise
   if(version===renderVersion){c.dataset.renderedPage=String(pageNumber);error.value='';loading.value=false}
  }catch(e){if(version===renderVersion&&(e as Error).name!=='RenderingCancelledException'){error.value=String(e);loading.value=false}}
 })
 return queue
}
watch(()=>props.url,async url=>{
 const version=++sourceVersion;++renderVersion;task?.cancel()
 await queue.catch(()=>{});const old=doc;doc=undefined;await old?.destroy()
 try{
  const loaded=await getDocument(url).promise
  if(version!==sourceVersion){await loaded.destroy();return}
  doc=loaded;count.value=doc.numPages;current.value=Math.min(count.value,props.page)
  await nextTick();await render()
 }catch(e){if(version===sourceVersion){error.value=String(e);loading.value=false}}
},{immediate:true})
watch(()=>props.page,p=>{current.value=p})
watch([current,zoom],()=>{void render()})
onBeforeUnmount(()=>{sourceVersion++;renderVersion++;task?.cancel();void queue.finally(()=>doc?.destroy())})
</script>
<template><section class="viewer"><div class="toolbar"><el-button :disabled="current<=1" @click="current--">上一页</el-button><el-input-number v-model="current" :min="1" :max="count"/><span>/ {{count}}</span><el-button :disabled="current>=count" @click="current++">下一页</el-button><el-button @click="zoom=Math.max(.5,zoom-.2)">缩小</el-button><el-button @click="zoom+=.2">放大</el-button><a :href="url" target="_blank">独立打开原卷</a></div><p v-if="error" role="alert">{{error}}</p><p v-if="loading">正在渲染原卷…</p><div class="canvas-scroll"><canvas ref="canvas"/></div></section></template>
