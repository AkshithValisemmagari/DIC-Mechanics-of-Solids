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
   await page.locator('[data-tab="methods"]').click();
   assert(await page.locator('#readableResults').isVisible());
   assert((await page.locator('#resultsErrors').innerText()).includes('Stress components'));
   assert.equal(await page.locator('#technicalDetails').getAttribute('open'),null);
   await page.locator('#componentResults summary').click();
   assert((await page.locator('#componentErrors').innerText()).includes('Engineering shear'));
   await page.locator('#componentResults summary').click();
   await context.grantPermissions(['clipboard-read','clipboard-write'],{origin:base});
   await page.locator('#technicalDetails summary').click();
   const raw=await page.locator('#raw').innerText();
   await page.locator('#copyTechnical').click();
   await page.getByText('JSON copied.',{exact:true}).waitFor();
   assert.equal(await page.evaluate(()=>navigator.clipboard.readText()),raw);
   await page.locator('#technicalDetails summary').click();
   await page.screenshot({path:path.join(output,name+'-results.png'),fullPage:true});
   // Reproduce the public-site failure: one After preview recovers automatically,
   // the other exhausts 502 retries and must expose a persistent Retry button.
   const previewRequests=new Map();let failRight=true;
   await page.route('**/runs/**/*.png*',async route=>{
    const file=new URL(route.request().url()).pathname.split('/').pop();
    if(!/^(left|right)_(reference|deformed)(_smoothed)?\.png$/.test(file))return route.continue();
    const count=(previewRequests.get(file)||0)+1;previewRequests.set(file,count);
    if((file==='left_deformed_smoothed.png'&&count===1)||(file==='right_deformed_smoothed.png'&&failRight))
     return route.fulfill({status:502,contentType:'text/plain',body:'Bad Gateway (delivery regression test)'});
    return route.continue();
   });
   await page.locator('[data-object="square_torsion"]').click();
   await page.locator('details').filter({has:page.locator('#denoise_sigma')}).evaluate(el=>{el.open=true;});
   await page.locator('#denoise_sigma').selectOption('0.7');
   await page.locator('#noise_std').evaluate(el=>{el.value='0';el.dispatchEvent(new Event('input',{bubbles:true}));});await run();
   await page.locator('[data-tab="stereo"]').click();
   await page.locator('#stereoQuality').waitFor();
   const cameraKeys=['left_reference','right_reference','left_deformed','right_deformed'];
   const beforePreview=await(await context.request.get(base+'/api/result')).json();
   await page.locator('#stereoRetry_right_deformed').waitFor({state:'visible'});
   for(const key of cameraKeys.slice(0,3))await page.locator('#stereoStatus_'+key).waitFor({state:'hidden'});
   assert.equal(previewRequests.get('left_deformed_smoothed.png'),2);
   assert.equal(previewRequests.get('right_deformed_smoothed.png'),3);
   assert([...previewRequests.keys()].every(file=>file.includes('_smoothed')),'Unused original previews must not be requested');
   await page.locator('#stereoField').selectOption('u');
   assert(await page.locator('#stereoRetry_right_deformed').isVisible(),'Field redraw must preserve image failure');
   await page.screenshot({path:path.join(output,name+'-preview-error.png'),fullPage:true});
   failRight=false;await page.locator('#stereoRetry_right_deformed').click();
   async function assertFourCameraImages(){
    for(const key of cameraKeys){
     await page.locator('#stereoStatus_'+key).waitFor({state:'hidden'});
     assert(await page.locator('#stereo_'+key).evaluate(canvas=>{
      const pixels=canvas.getContext('2d').getImageData(0,0,canvas.width,canvas.height).data;
      let lo=255,hi=0;for(let i=0;i<pixels.length;i+=4){lo=Math.min(lo,pixels[i]);hi=Math.max(hi,pixels[i]);}
      return hi-lo>20;
     }),'Camera image must actually be drawn: '+key);
    }
   }
   await assertFourCameraImages();
   await page.locator('#stereoImageMode').selectOption('original');await assertFourCameraImages();
   const requestCount=[...previewRequests.values()].reduce((a,b)=>a+b,0);
   await page.locator('#stereoImageMode').selectOption('smoothed');await assertFourCameraImages();
   assert.equal([...previewRequests.values()].reduce((a,b)=>a+b,0),requestCount,'Reuse loaded previews when switching modes');
   const afterPreview=await(await context.request.get(base+'/api/result')).json();
   assert.deepEqual(afterPreview.summary,beforePreview.summary,'Preview delivery must not change numerical results');
   await page.locator('[data-tab="methods"]').click();
   assert((await page.locator('#resultsExplanation').innerText()).includes('Bulk stress remains analytical'));
   assert(!(await page.locator('#resultsErrors').innerText()).includes('Stress components'));
   await page.locator('[data-tab="stereo"]').click();
   assert((await page.locator('#stereoTruth').evaluate(c=>c.getBoundingClientRect().height))<=260);
   await page.waitForLoadState('networkidle');
   await page.screenshot({path:path.join(output,name+'-stereo.png'),fullPage:true});
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false,'Horizontal overflow: '+name);
   assert.deepEqual(errors,[],'Browser JavaScript errors: '+name);
   await context.close();
   console.log('PASS: real Chromium '+name+' runs, coverage, field canvas, all four stereo previews, 502 retries, manual recovery, mode switching and layout smoke checks.');
  }
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
