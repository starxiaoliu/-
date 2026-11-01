<script setup lang="ts">
import {ref} from 'vue'
import {ElMessageBox} from 'element-plus'
import {api} from './api'
const emit=defineEmits<{restored:[]}>()
const file=ref<File>(),preview=ref<{counts:Record<string,number>;warning:string}>(),error=ref(''),busy=ref(false)
async function inspect(e:Event){file.value=(e.target as HTMLInputElement).files?.[0];preview.value=undefined;if(!file.value)return;busy.value=true;try{const body=new FormData();body.append('file',file.value);preview.value=await api('/backups/import',{method:'POST',body});error.value=''}catch(e){error.value=String(e)}finally{busy.value=false}}
async function restore(){if(!file.value)return;try{await ElMessageBox.confirm('恢复会替换本地全部试卷与笔记。请确认已下载当前备份。是否继续？','确认恢复',{type:'warning',confirmButtonText:'替换并恢复',cancelButtonText:'取消'})}catch{return}busy.value=true;try{const body=new FormData();body.append('file',file.value);await api('/backups/import?confirm=true',{method:'POST',body});localStorage.removeItem('lastPaper');for(const key of Object.keys(localStorage)){if(key.startsWith('review-draft:')||key.startsWith('lastQuestion:'))localStorage.removeItem(key)}error.value='';preview.value=undefined;emit('restored')}catch(e){error.value=String(e)}finally{busy.value=false}}
</script>
<template><section v-loading="busy"><h2>本地备份与恢复</h2><p>JSON 包含原始 PDF、试卷、人工校正、标签、心得及状态。请私下保管，勿上传公共仓库。</p><a href="/api/backups/export" download="xingce-backup.json"><el-button type="primary">下载完整 JSON 备份</el-button></a><h3>恢复备份</h3><p>先检查文件，确认后才会替换当前全部数据；失败校验不会修改数据库。</p><input type="file" accept=".json" @change="inspect"/><el-alert v-if="error" :title="error" type="error"/><article v-if="preview"><p v-for="(n,name) in preview.counts" :key="name">{{name}}：{{n}}</p><p>{{preview.warning}}</p><el-button type="danger" @click="restore">确认恢复</el-button></article></section></template>
