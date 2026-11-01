import {test,expect} from '@playwright/test'
import {readFileSync} from 'node:fs'
test('upload PDF, save separate notes, recover failed draft, statistics, knowledge and backup',async({page,request})=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message))
 let pid=''
 try {
 await page.goto('/')
 await page.getByRole('button',{name:'试卷库',exact:true}).click()
 await page.locator('input[type=file]').setInputFiles('../tests/fixtures/private/synthetic-e2e.pdf')
 await expect(page.getByText('2 页 · 2 题',{exact:false})).toBeVisible()
 await expect.poll(()=>page.locator('canvas').evaluate((c:any)=>c.width)).toBeGreaterThan(0)
 const papers=(await (await request.get('/api/papers')).json()).data
 pid=papers.find((p:any)=>p.title==='synthetic-e2e.pdf').id
 await page.getByRole('button',{name:'进入复盘工作台'}).click()
 const note=page.getByPlaceholder('当时为什么这样选？关键遗漏是什么？下次碰到类似题时我第一步要做什么？')
 await note.fill('正确题也可以记录：先找关键词😀')
 await page.screenshot({path:'../docs/acceptance-workspace.png',fullPage:true})
 await page.getByRole('button',{name:'下一题',exact:true}).click()
 await expect(note).toHaveValue('')
 await note.fill('第二题独立笔记')
 await page.getByRole('button',{name:'标记已完成',exact:true}).click()
 await expect(page.getByRole('status')).toHaveText('已保存')
 await page.getByText('加入二刷',{exact:true}).click()
 await page.getByRole('button',{name:'上一题',exact:true}).click()
 await expect(note).toHaveValue('正确题也可以记录：先找关键词😀')
 // Fail network writes; local draft must survive reload and support explicit retry.
 await page.route('**/api/questions/*/review',route=>route.request().method()==='PUT'?route.abort():route.continue())
 await note.fill('保存失败也不能丢失的草稿')
 await expect(page.getByRole('status')).toHaveText('保存失败，草稿保留')
 page.on('dialog',d=>d.accept())
 await page.reload()
 await expect(note).toHaveValue('保存失败也不能丢失的草稿')
 await page.unroute('**/api/questions/*/review')
 await page.getByRole('button',{name:'保存 / 重试',exact:true}).click()
 await expect(page.getByRole('status')).toHaveText('已保存')
 await page.getByRole('button',{name:'本卷统计',exact:true}).click()
 await expect(page.getByText('实际记录的标签频次')).toBeVisible()
 await expect(page.getByText('尚未记录易错标签')).toBeVisible()
 await page.getByRole('button',{name:'笔记库',exact:true}).click()
 await expect(page.getByText('保存失败也不能丢失的草稿',{exact:true})).toBeVisible()
 await page.getByRole('button',{name:'备份恢复',exact:true}).click()
 await expect(page.getByRole('button',{name:'下载完整 JSON 备份'})).toBeVisible()
 const backup=await (await request.get('/api/backups/export')).json()
 expect(backup.includes_pdf).toBe(true)
 await page.screenshot({path:'../docs/acceptance-backup.png',fullPage:true})
 expect(errors).toEqual([])
 }finally{if(pid)await request.delete('/api/papers/'+pid)}
})
