import {test,expect} from '@playwright/test'
test('topic import and opt-in AI advice only updates notes after adoption',async({page,request})=>{
 let pid='';const sent:any[]=[]
 const settings={base_url:'',model:'',has_api_key:false,configured:false}
 await page.route('**/api/ai/settings',async route=>{
  if(route.request().method()==='PUT'){
   const body=route.request().postDataJSON();expect(body.model).toBe('my-model');expect(body.api_key).toBe('test-key')
   Object.assign(settings,{base_url:body.base_url,model:body.model,has_api_key:true,configured:true})
  }
  await route.fulfill({json:{data:settings,error:null,meta:{}}})
 })
 await page.route('**/api/questions/*/ai-assist',async route=>{
  sent.push(route.request().postDataJSON())
  await route.fulfill({json:{data:{answer:'建议：先找题目中的限定条件，再逐项核对。',model:'my-model'},error:null,meta:{}}})
 })
 try{
 await page.goto('/')
 await page.getByRole('button',{name:'试卷库',exact:true}).click()
 await page.locator('.el-select').first().click()
 await page.getByRole('option',{name:'专题题集 / 摘录'}).click()
 await page.getByPlaceholder('模块（选填），例如：判断推理').fill('判断推理')
 await page.getByPlaceholder('题型（选填），例如：图形推理').fill('图形推理')
 await page.locator('input[type=file]').setInputFiles('../tests/fixtures/private/synthetic-e2e.pdf')
 await expect(page.getByText('2 页 · 2 题',{exact:false})).toBeVisible()
 const papers=(await(await request.get('/api/papers')).json()).data
 pid=papers.find((p:any)=>p.title==='synthetic-e2e.pdf').id
 expect(papers.find((p:any)=>p.id===pid).collection_kind).toBe('topic')
 await page.getByRole('button',{name:'进入复盘工作台'}).click()
 await expect(page.locator('canvas')).toHaveAttribute('data-rendered-page','1')
 const note=page.getByPlaceholder('当时为什么这样选？关键遗漏是什么？下次碰到类似题时我第一步要做什么？')
 await note.fill('我的原始心得')
 await page.getByRole('button',{name:'AI 帮助：整理心得 / 讨论解法'}).click()
 await expect(page.getByText('将发送的 PDF 文字',{exact:false})).toBeVisible()
 await page.getByText('配置 AI 服务（首次使用）',{exact:true}).click()
 await page.getByPlaceholder('https://你的服务地址/v1').fill('https://provider.test/v1')
 await page.getByPlaceholder('填写服务商提供的模型标识').fill('my-model')
 await page.getByPlaceholder('填写密钥',{exact:true}).fill('test-key')
 await page.getByRole('button',{name:'保存 AI 配置',exact:true}).click()
 await expect(page.getByPlaceholder('已保存，留空保留；更换地址需重填')).toHaveValue('')
 const send=page.getByRole('button',{name:'发送给 AI',exact:true})
 await expect(send).toBeDisabled()
 await page.getByText('我已核对发送范围，同意发送至配置的 AI 服务',{exact:true}).click()
 await send.click()
 await expect(page.getByRole('button',{name:'采纳：追加到我的心得'})).toBeVisible()
 expect(sent[0].image_pages).toEqual([])
 expect(sent[0].note).toBe('我的原始心得')
 expect(sent[0].pdf_text).toContain('浏览器合成验收题')
 await expect(note).toHaveValue('我的原始心得')
 await page.getByRole('button',{name:'采纳：追加到我的心得'}).click()
 await expect(note).toHaveValue(/先找题目中的限定条件/)
 await page.getByRole('button',{name:'保存 / 重试',exact:true}).click()
 await expect(page.getByRole('status')).toHaveText('已保存')
 await page.getByText('讨论解法',{exact:true}).click()
 await page.getByPlaceholder('例如：我为什么不能用这个公式？有没有更快的方法？').fill('为什么要看限定条件？')
 await send.click()
 await expect(page.getByText('已讨论 1 轮')).toBeVisible()
 expect(sent[1].mode).toBe('discuss')
 await page.screenshot({path:'../docs/acceptance-ai.png',fullPage:true})
 }finally{if(pid)await request.delete('/api/papers/'+pid)}
})

