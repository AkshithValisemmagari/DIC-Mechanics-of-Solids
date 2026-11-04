/* Real Chromium smoke check. Start a dedicated lab server before running. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {chromium}=require('playwright');
const base=process.env.LAB_TEST_URL||'http://127.0.0.1:8765';
const output=process.env.LAB_BROWSER_OUTPUT||'outputs/browser-check';
(async()=>{
 fs.mkdirSync(output,{recursive:true});
 const browser=await chromium.launch({headless:true});
 try{
  for(const [name,viewport] of [['desktop',{width:1440,height:1000}],['mobile',{width:390,height:844}]]){
   const context=await browser.newContext({viewport});
   const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
   const run=async()=>{
    await page.locator('#run').click();
    await page.locator('#state').filter({hasText:'Experiment complete'}).waitFor({timeout:90000});
    assert(await page.locator('#coverageDetails').isVisible());
    assert.match(await page.locator('#metricValid').innerText(),/^\d+ \/ \d+$/);
    await page.locator('#coverageDetails summary').click();
    assert((await page.locator('#coverageExplanation').innerText()).includes('RMSE uses accepted points only'));
    await page.locator('#coverageDetails summary').click();
    assert(await page.locator('#matchQuality').isVisible());
   };
   await page.goto(base,{waitUntil:'networkidle'});
   await page.waitForFunction(()=>!document.getElementById('controls').disabled);
   await run();
   await page.locator('[data-tab="images"]').click();
   assert((await page.locator('#subsetReverse').innerText()).includes('Return error:'));
   assert((await page.locator('#buildInfo').innerText()).includes('Server build'));
   await page.waitForLoadState('networkidle');
   await page.screenshot({path:path.join(output,name+'-inspector.png'),fullPage:true});
   if(name==='mobile'){
    await page.locator('#jumpToResults').click();assert((await page.url()).endsWith('#experimentResults'));
    await page.locator('a[href="#experimentSetup"]').click();assert((await page.url()).endsWith('#experimentSetup'));
   }
   await page.locator('[data-object="plate_with_hole"]').click();
   await page.locator('#force_n').fill('0');await run();
   const data=await(await context.request.get(base+'/api/result')).json();
   assert(data.summary.eligible_reference_subsets<data.summary.candidate_subsets);
   assert(data.summary.forward_backward);
   await page.locator('[data-tab="fields"]').click();
   await page.locator('#field').selectOption('stress_xx');
   await page.locator('#truthCanvas').scrollIntoViewIfNeeded();
   assert((await page.locator('#errorLegend').innerText()).includes('Error: 0'));
   assert.equal(await page.locator('#coverageDetails').getAttribute('open'),null);
   assert(await page.locator('#truthCanvas').evaluate(c=>c.width>0&&c.height>0&&c.getContext('2d').getImageData(0,0,c.width,c.height).data.some((v,i)=>i%4===3&&v>0)));
   await page.waitForLoadState('networkidle');
   await page.screenshot({path:path.join(output,name+'-fields.png'),fullPage:true});
   await page.locator('[data-object="square_torsion"]').click();
   await page.locator('#noise_std').evaluate(el=>{el.value='0';el.dispatchEvent(new Event('input',{bubbles:true}));});await run();
   await page.locator('[data-tab="stereo"]').click();
   await page.locator('#stereoQuality').waitFor();
   assert((await page.locator('#stereoTruth').evaluate(c=>c.getBoundingClientRect().height))<=260);
   await page.waitForLoadState('networkidle');
   await page.screenshot({path:path.join(output,name+'-stereo.png'),fullPage:true});
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false,'Horizontal overflow: '+name);
   assert.deepEqual(errors,[],'Browser JavaScript errors: '+name);
   await context.close();
   console.log('PASS: real Chromium '+name+' runs, coverage, field canvas, stereo and layout smoke checks.');
  }
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
