<script setup lang="ts">
import {ref,onMounted} from 'vue'
import {api} from './api'
const emit=defineEmits<{saved:[]}>()
const base=ref(''),model=ref(''),key=ref(''),hasKey=ref(false),busy=ref(false),error=ref(''),message=ref('')
async function load(){try{const s=await api<{base_url:string;model:string;has_api_key:boolean}>('/ai/settings');base.value=s.base_url;model.value=s.model;hasKey.value=s.has_api_key}catch(e){error.value=String(e)}}
async function save(){busy.value=true;error.value='';message.value='';try{await api('/ai/settings',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({base_url:base.value,model:model.value,api_key:key.value})});key.value='';hasKey.value=true;message.value='配置已保存到本机。尚未向服务商发送内容。';emit('saved')}catch(e){error.value=String(e)}finally{busy.value=false}}
async function clear(){busy.value=true;try{await api('/ai/settings',{method:'DELETE'});key.value='';hasKey.value=false;base.value='';model.value='';message.value='已清除本机 AI 配置';emit('saved')}catch(e){error.value=String(e)}finally{busy.value=false}}
onMounted(load)
</script>
<template><section class="ai-settings" v-loading="busy"><h3>AI 服务设置</h3><p>使用兼容 OpenAI Chat Completions 的服务。配置后，在每题心得旁主动发送请求。</p><label>API 地址（基础地址含 /v1，或完整 /chat/completions 地址）<el-input v-model="base" placeholder="https://你的服务地址/v1" autocomplete="off"/></label><label>模型名称<el-input v-model="model" placeholder="填写服务商提供的模型标识"/></label><label>API 密钥<el-input v-model="key" type="password" show-password :placeholder="hasKey?'已保存，留空保留；更换地址需重填':'填写密钥'" autocomplete="new-password"/></label><p class="muted">密钥仅保存在本机 data/ai-settings.json，不返回前端、不进入 JSON 笔记备份。该设置文件为本地明文，请私下保管。</p><el-button type="primary" @click="save">保存 AI 配置</el-button><el-button :disabled="!hasKey" @click="clear">清除配置</el-button><p v-if="message">{{message}}</p><el-alert v-if="error" :title="error" type="error" :closable="false"/></section></template>
