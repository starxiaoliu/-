<script setup lang="ts">
import {ref} from 'vue'
import {api,type Paper} from './api'
const props=defineProps<{paper:Paper}>(),emit=defineEmits<{saved:[]}>()
const kind=ref(props.paper.collection_kind||'full'),expected=ref<number|undefined>(props.paper.expected_count??undefined),module=ref(''),subtype=ref(''),busy=ref(false),error=ref(''),message=ref('')
async function save(){busy.value=true;error.value='';try{await api('/papers/'+props.paper.id+'/settings',{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({collection_kind:kind.value,expected_count:expected.value||null,module:module.value,subtype:subtype.value})});message.value='已保存题集设置。批量修改分类的题目需重新核对；原有答案和心得保留。';module.value='';subtype.value='';emit('saved')}catch(e){error.value=String(e)}finally{busy.value=false}}
</script>
<template><el-collapse><el-collapse-item title="整卷 / 专题题集设置与批量分类"><div class="toolbar"><el-select v-model="kind" aria-label="题集类型"><el-option value="full" label="完整试卷"/><el-option value="topic" label="专题题集 / 摘录"/></el-select><span>预期题数（选填）</span><el-input-number v-model="expected" :min="1" :max="1000"/></div><p>专题题集可只包含一个题型，保留原始题号（如 76、81、90），不要求从 1 开始或连续编号。统计只按实际导入的题目计算。</p><div class="toolbar"><el-input v-model="module" placeholder="统一模块，例如：判断推理（留空不修改）"/><el-input v-model="subtype" placeholder="统一题型，例如：图形推理（留空不修改）"/><el-button :loading="busy" @click="save">保存题集设置 / 批量分类</el-button></div><p v-if="message">{{message}}</p><el-alert v-if="error" :title="error" type="error" :closable="false"/></el-collapse-item></el-collapse></template>
