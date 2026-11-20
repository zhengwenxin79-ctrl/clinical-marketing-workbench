/* 全部写入都在临时副本；使用独立Chrome for Testing，不触碰日常Chrome。 */
const fs=require('fs'),path=require('path'),os=require('os'),assert=require('assert');
const {spawn,execFileSync}=require('child_process');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'/tmp/clinical-ranking-verify/node_modules/playwright');
const center=path.dirname(__dirname),output=path.join(__dirname,'核验记录'),checks=[],errors=[];
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'cds-maintenance-ui-')),copy=path.join(temp,'center');
let server,browser;
function check(condition,message){assert(condition,message);checks.push(message);}
async function ready(proc){return new Promise((resolve,reject)=>{let out='';const timer=setTimeout(()=>reject(Error('维护服务启动超时')),15000);proc.stdout.on('data',b=>{out+=b.toString();const match=out.match(/http:\/\/127\.0\.0\.1:\d+\//);if(match){clearTimeout(timer);resolve(match[0]);}});proc.on('exit',code=>{clearTimeout(timer);reject(Error('维护服务提前结束 '+code));});});}
async function idle(page){await page.waitForFunction(()=>document.body.dataset.busy==='false',{timeout:30000});}
(async()=>{try{
 fs.mkdirSync(copy,{recursive:true});fs.mkdirSync(path.join(copy,'数据库'));fs.mkdirSync(path.join(copy,'规则与说明'));
 for(const name of ['原始资料','脚本','维护台'])fs.cpSync(path.join(center,name),path.join(copy,name),{recursive:true,filter:p=>!p.includes('核验记录')&&!p.includes('__pycache__')});
 fs.cpSync(path.join(center,'会议视图/src'),path.join(copy,'会议视图/src'),{recursive:true});
 fs.copyFileSync(path.join(center,'规则与说明/004_维护记录.sql'),path.join(copy,'规则与说明/004_维护记录.sql'));
 execFileSync('python3',['-c','import sqlite3,sys; a=sqlite3.connect("file:"+sys.argv[1]+"?mode=ro",uri=True); b=sqlite3.connect(sys.argv[2]); a.backup(b); b.close(); a.close()',path.join(center,'数据库/marketing.db'),path.join(copy,'数据库/marketing.db')]);
 server=spawn('python3',[path.join(copy,'脚本/启动维护台.py'),'--root',copy,'--port','0'],{stdio:['ignore','pipe','pipe']});
 const url=await ready(server);let serverErr='';server.stderr.on('data',b=>serverErr+=b.toString());
 const before=await(await fetch(url+'api/status')).json();
 const forbidden=await fetch(url+'api/import-sample',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
 check(forbidden.status===403,'不带维护令牌的写入请求被拒绝');
 browser=await chromium.launchPersistentContext(path.join(temp,'automation-profile'),{executablePath:'/Users/zwx/.local/bin/automation-chrome',headless:true,viewport:{width:1440,height:1000}});
 await browser.route('**/*',route=>{const u=new URL(route.request().url());return u.hostname==='127.0.0.1'?route.continue():route.abort();});
 const page=browser.pages()[0]||await browser.newPage();page.on('pageerror',e=>errors.push(e.message));
 await page.goto(url);await idle(page);fs.mkdirSync(output,{recursive:true});
 check(await page.locator('nav [data-step]').count()===4,'四个入口均显示');
 check((await page.locator('#stats').innerText()).includes('606'),'读取当前数据库606条报告');
 await page.screenshot({path:path.join(output,'01-导入资料-桌面.png'),fullPage:true});
 await page.locator('#import-sample').click();await idle(page);
 check(await page.locator('#panel-diff').isVisible(),'导入样例后进入变化清单');
 check((await page.locator('#diff-content').innerText()).includes('无变化'),'相同CDS资料明确展示无变化');
 await page.screenshot({path:path.join(output,'02-查看变化-桌面.png'),fullPage:true});
 await page.locator('#go-confirm').click();await page.locator('#confirm-check').check();await page.locator('#confirm-run').click();await idle(page);
 check(await page.locator('#panel-export').isVisible(),'人工确认后进入核验导出');
 await page.locator('#export-run').click();await idle(page);
 check((await page.locator('#export-content').innerText()).includes('核验通过'),'网页完成导入、差异、确认、核验导出全流程');
 const after=await(await fetch(url+'api/status')).json();
 check(after.counts.reports===before.counts.reports&&after.counts.topics===before.counts.topics,'试跑没有复制报告或改动议题数量');
 await page.screenshot({path:path.join(output,'03-核验导出-桌面.png'),fullPage:true});
 await page.reload();await idle(page);check((await page.locator('#export-content').innerText()).includes('核验通过'),'刷新页面后确认与核验记录仍可读取');
 await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(output,'04-核验导出-手机.png'),fullPage:true});
 check(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),'手机布局没有整体横向溢出');
 await page.locator('[data-step=import]').click();await page.screenshot({path:path.join(output,'05-导入资料-手机.png'),fullPage:true});
 await page.setViewportSize({width:1440,height:1000});
 const data=JSON.parse(fs.readFileSync(path.join(copy,'原始资料/CDS2026/官方日程/CDS_全日程结构化.json'),'utf8'));data.items[0].time='14:01-14:18';
 await page.locator('#source-file').setInputFiles({name:'隔离测试-时间更新.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(data))});await page.locator('#import-file').click();await idle(page);
 check((await page.locator('#diff-content').innerText()).includes('14:01'),'上传新资料能展示字段更新前后');
 await page.screenshot({path:path.join(output,'06-时间差异-隔离测试.png'),fullPage:true});
 await page.locator('#go-confirm').click();await page.locator('#confirm-check').check();await page.locator('#confirm-run').click();await idle(page);await page.locator('#export-run').click();await idle(page);
 check((await page.locator('#export-content').innerText()).includes('核验通过'),'隔离副本真实字段更新也完成网页核验导出');
 await page.locator('[data-step=import]').click();data.items[0].title+='【仅隔离测试】';await page.locator('#source-file').setInputFiles({name:'隔离测试-主题变化.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(data))});await page.locator('#import-file').click();await idle(page);
 check(await page.locator('#go-confirm').isDisabled(),'题名变化会显示待复核并禁用确认入口');
 const recordLink=await page.locator('#records-link').getAttribute('href');const rec=await fetch(url+recordLink.slice(1));check(rec.status===200,'批次原件与日志下载入口可访问');
 check(errors.length===0,'没有浏览器脚本错误');
 const result={result:'passed',checked_at:new Date().toISOString(),environment:'macOS · 独立Chrome for Testing · 临时数据副本',checks,errors,formal_database_mutated:false};fs.writeFileSync(path.join(output,'网页验收结果.json'),JSON.stringify(result,null,2)+'\n');process.stdout.write(JSON.stringify(result,null,2)+'\n');
}catch(e){process.exitCode=1;console.error(e);fs.mkdirSync(output,{recursive:true});fs.writeFileSync(path.join(output,'网页验收失败.json'),JSON.stringify({error:String(e),checks,errors},null,2));}
finally{if(browser)await browser.close();if(server){server.kill('SIGINT');await new Promise(resolve=>{const timer=setTimeout(()=>{server.kill('SIGTERM');resolve();},4000);server.once('exit',()=>{clearTimeout(timer);resolve();});});}fs.rmSync(temp,{recursive:true,force:true});}})();
