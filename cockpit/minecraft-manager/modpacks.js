'use strict';
// Independent Modpack Workspaces panel. Existing server controls are not changed.
(()=>{
 const $m=id=>document.getElementById(id);
 const exe='/usr/local/libexec/cockpit-minecraft-modpacks';
 const browserExe='/usr/local/libexec/cockpit-minecraft-curseforge-browser';
 const say=(s,error=false)=>{const el=$m('mp-output');el.textContent=typeof s==='string'?s:JSON.stringify(s,null,2);el.style.color=error?'#ff9999':''};
 const call=async(op,...args)=>{
   const output=await cockpit.spawn([exe,op,...args.map(String)],{superuser:'require',err:'message'});
   let data;try{data=JSON.parse(output);}catch{throw Error('Malformed modpack helper response')}
   if(!data.ok)throw Error(data.error||'Operation failed');return data.data;
 };
 const browse=async(op,...args)=>{
   const output=await cockpit.spawn([browserExe,op,...args.map(String)],{superuser:'require',err:'message'});
   let data;try{data=JSON.parse(output);}catch{throw Error('Malformed CurseForge browser response')}
   if(!data.ok)throw Error(data.error||'CurseForge request failed');return data.data;
 };
 const run=async(label,fn)=>{say(label+'…');try{say(await fn())}catch(e){say(label+': '+(e.message||String(e)),true)}};
 const update=async()=>{
   const r=await call('status');$m('mp-key').textContent=r.key_configured?'CurseForge API key configured':'No CurseForge API key; local ZIP import is available';
   const sel=$m('mp-workspace'),last=sel.value;sel.replaceChildren(new Option('Choose workspace',''));
   for(const p of r.workspaces)sel.add(new Option(p.name+' — '+p.status,p.name));sel.value=last;
   $m('mp-workspaces').textContent=r.workspaces.map(p=>p.name+' | '+p.loader+' | '+p.minecraft_version+' | '+p.status).join('\n')||'No modpack workspaces yet.';
 };
 $m('mp-refresh').onclick=()=>run('Load workspaces',update);
 const versionSelect=$m('mp-search-version');
 const detailPanel=$m('mp-project-detail');
 const resultsPanel=$m('mp-results');
 const searchBtn=$m('mp-search');
 const categoryRoot=$m('mp-category');
 const queryInput=$m('mp-query');
 const el=(tag,cls,text)=>{const node=document.createElement(tag);if(cls)node.className=cls;if(text!==undefined)node.textContent=String(text);return node;};
 const safeUrl=(url)=>{try{const u=new URL(url);return u.protocol==='https:'&&['media.forgecdn.net','mediafilez.forgecdn.net','edge.forgecdn.net','media.curseforge.com','static-cdn.jtvnw.net'].includes(u.hostname)?u.href:'';}catch{return '';}};
 const mcVersion=v=>/^\d+(?:\.\d+){1,3}$/.test(v);
 const filters=el('div','form-grid');
 const makeSelect=(label,id,entries)=>{
   const holder=el('label','field',label);
   const select=el('select');select.id=id;
   for(const [value,title] of entries)select.add(new Option(title,value));
   holder.append(select);filters.append(holder);
   return select;
 };
 const categoryFilter=makeSelect('Subcategory','mp-filter-subcategory',[['','All categories']]);
 const loaderFilter=makeSelect('Mod loader','mp-filter-loader',[
   ['any','Any loader'],['forge','Forge'],['neoforge','NeoForge'],['fabric','Fabric'],['quilt','Quilt']]);
 const sortFilter=makeSelect('Sort results','mp-filter-sort',[
   ['relevance','Best match'],['popular','Most popular'],['downloads','Top downloaded'],
   ['updated','Recently updated'],['released','Recently released'],
   ['featured','Featured'],['rating','Highest rated'],['name','Name A–Z']]);
 const controls=el('div','toolbar');
 const topBtn=el('button','btn secondary','Top downloaded');
 topBtn.type='button';
 const popularBtn=el('button','btn secondary','Most popular');
 popularBtn.type='button';
 const featuredBtn=el('button','btn secondary','Featured');
 featuredBtn.type='button';
 const updatedBtn=el('button','btn secondary','Recently updated');
 updatedBtn.type='button';
 const releasedBtn=el('button','btn secondary','New releases');
 releasedBtn.type='button';
 const ratedBtn=el('button','btn secondary','Top rated');
 ratedBtn.type='button';
 const clearBtn=el('button','btn secondary','Reset filters');
 clearBtn.type='button';
 const pagination=el('nav','mp-browser-pagination');
 pagination.setAttribute('aria-label','CurseForge search pages');
 pagination.hidden=true;
 const countText=el('p','hint');
 const searchPanel=searchBtn.parentElement;
 searchPanel.insertBefore(filters,searchBtn);
 searchPanel.insertBefore(controls,resultsPanel);
 controls.classList.add('mp-browser-presets');
 controls.append(topBtn,popularBtn,featuredBtn,updatedBtn,releasedBtn,ratedBtn,clearBtn);
 searchPanel.insertBefore(countText,resultsPanel);
 resultsPanel.after(pagination);
 let activeSearch=0,activeDetails=0,searchBusy=false,activeCard=null,currentPage=1,totalPages=1,hasMore=false;
 const loadVersions=async()=>{
   try{
     const values=await browse('versions');
     const saved=versionSelect.value;
     versionSelect.replaceChildren(new Option('All Minecraft versions',''));
     for(const v of values){if(mcVersion(v))versionSelect.add(new Option(v,v));}
     if([...versionSelect.options].some(x=>x.value===saved))versionSelect.value=saved;
   }catch(e){countText.textContent='Version list unavailable: '+String(e.message||e);}
 };
 const loadCategories=async()=>{
   const requested=categoryRoot.value;
   const previous=categoryFilter.value;
   categoryFilter.replaceChildren(new Option('All categories',''));
   categoryFilter.disabled=true;
   try{
     const values=await browse('categories',requested);
     if(requested!==categoryRoot.value)return;
     for(const category of values){categoryFilter.add(new Option(category.name,String(category.id)));}
     if([...categoryFilter.options].some(o=>o.value===previous))categoryFilter.value=previous;
   }catch(e){countText.textContent='Subcategory list unavailable: '+String(e.message||e);}
   finally{if(requested===categoryRoot.value)categoryFilter.disabled=false;}
 };
 categoryRoot.addEventListener('change',()=>{categoryFilter.value='';loadCategories();});
 const readFilters=()=>[queryInput.value,categoryRoot.value,versionSelect.value,
     categoryFilter.value,sortFilter.value,loaderFilter.value];
 const showCard=p=>{
   const item=el('div','sub-panel mp-browser-card');
   const art=safeUrl(p.icon);
   if(art){
     const img=el('img','mp-browser-icon');
     img.src=art;img.alt=p.name+' icon';img.width=64;img.height=64;img.loading='lazy';img.referrerPolicy='no-referrer';
     item.append(img);
   }
   const body=el('div','mp-browser-card-content');
   body.append(el('strong','',p.name),el('p','',p.summary||'No summary available.'));
   const authors=p.authors?.length?'By '+p.authors.join(', ')+' · ':'';
   body.append(el('p','hint',authors+Number(p.downloads||0).toLocaleString()+' downloads'));
   item.append(body);
   const detail=el('button','btn secondary','Details / versions');
   detail.type='button';detail.setAttribute('aria-expanded','false');
   detail.onclick=()=>displayProject(p.id,item,detail);
   item.append(detail);
   resultsPanel.append(item);
 };
 const maxPage=498; // Backend limits the search offset to 9940 (20 items/page).
 const drawPages=()=>{
   pagination.replaceChildren();
   if(totalPages<=1&&!hasMore){pagination.hidden=true;return;}
   pagination.hidden=false;
   const button=(label,page,disabled=false,current=false)=>{
     const btn=el('button','btn secondary',label);btn.type='button';
     btn.disabled=disabled||searchBusy;btn.setAttribute('aria-label',label==='Previous'||label==='Next'?label+' page':'Page '+page);
     if(current){btn.classList.add('mp-page-current');btn.setAttribute('aria-current','page');}
     btn.onclick=()=>search(page);
     pagination.append(btn);
   };
   button('Previous',currentPage-1,currentPage<=1);
   const knownEnd=Math.min(maxPage,Math.max(totalPages,currentPage+(hasMore?1:0)));
   const selected=new Set([1,knownEnd]);
   for(let p=Math.max(1,currentPage-2);p<=Math.min(knownEnd,currentPage+2);p++)selected.add(p);
   let last=0;
   for(const p of [...selected].sort((x,y)=>x-y)){
     if(p>last+1)pagination.append(el('span','mp-page-ellipsis','…'));
     button(String(p),p,false,p===currentPage);last=p;
   }
   button('Next',currentPage+1,currentPage>=knownEnd);
 };
 const search=async(page=1)=>{
   if(searchBusy)return;
   const values=readFilters();
   if(values[5]!=='any'&&!values[2]){countText.textContent='Choose a Minecraft version to filter by mod loader.';return;}
   if(!Number.isInteger(page)||page<1||page>maxPage)return;
   const requestId=++activeSearch;
   searchBusy=true;searchBtn.disabled=true;
   const priorPage=currentPage;
   countText.textContent='Loading page '+page+'…';
   activeDetails++;activeCard=null;detailPanel.remove();detailPanel.hidden=true;
   resultsPanel.replaceChildren();pagination.hidden=true;
   try{
     const sort=values[4]==='relevance'&&!values[0].trim()?'popular':values[4];
     const data=await browse('search-page',...values.slice(0,4),sort,values[5],String((page-1)*20));
     if(requestId!==activeSearch)return;
     for(const project of data.items||[])showCard(project);
     currentPage=page;
     const hasTotal=Number.isInteger(data.total)&&data.total>=0;
     totalPages=hasTotal?Math.max(1,Math.min(maxPage,Math.ceil(data.total/20))):Math.max(page,1);
     hasMore=data.next_index!==null&&data.next_index!==undefined;
     const shown=(data.items||[]).length;
     const first=shown?(page-1)*20+1:0;
     const last=(page-1)*20+shown;
     countText.textContent=shown?'Showing '+first+'–'+last+
       (hasTotal?' of '+Number(data.total).toLocaleString():'')+' results · Page '+page+
       (hasTotal?' of '+totalPages:''):'No projects found on page '+page+'.';
   }catch(e){currentPage=priorPage;countText.textContent='Search failed: '+String(e.message||e);}
   finally{searchBusy=false;searchBtn.disabled=false;drawPages();}
 };
 searchBtn.onclick=()=>search(1);
 queryInput.addEventListener('keydown',e=>{if(e.key==='Enter')search();});
 const quickSort=sort=>{sortFilter.value=sort;search();};
 topBtn.onclick=()=>quickSort('downloads');
 popularBtn.onclick=()=>quickSort('popular');
 featuredBtn.onclick=()=>quickSort('featured');
 updatedBtn.onclick=()=>quickSort('updated');
 releasedBtn.onclick=()=>quickSort('released');
 ratedBtn.onclick=()=>quickSort('rating');
 clearBtn.onclick=()=>{
   queryInput.value='';
   versionSelect.value='';
   categoryFilter.value='';
   loaderFilter.value='any';
   sortFilter.value='popular';
   search();
 };
 const showServerWizard=(project,file,container)=>{
   const previous=container.querySelector('.mp-server-wizard');
   if(previous)previous.remove();
   const wrap=el('section','mp-server-wizard');
   const heading=el('h4','','Create Minecraft server · '+project.name);
   wrap.append(heading,el('p','hint','Configure a new server using this CurseForge release. Review checks are read-only. Creation is not enabled until a compatible server package and backup integration have been verified.'));
   const fields=el('div','mp-wizard-grid');
   const field=(title,type,value,options)=>{
     const label=el('label','field',title);
     let control;
     if(options){
       control=el('select');
       for(const [v,caption] of options)control.add(new Option(caption,v));
     }else{
       control=el('input');control.type=type;control.value=value;
     }
     label.append(control);fields.append(label);
     return control;
   };
   const suggested=('cf-'+project.name.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'')).slice(0,35).replace(/-$/,'');
   const name=field('Server ID','text',suggested);
   name.maxLength=35;name.pattern='[a-z][a-z0-9-]{1,34}';
   const path=field('Server path','text','/opt/minecraft/managed/'+suggested);
   const port=field('Port (0 = automatic)','number','0');port.min='0';port.max='65535';
   const ram=field('Maximum RAM (GiB)','number','8');ram.min='2';ram.max='64';
   const cpu=field('CPU cores (planned limit)','number','2');cpu.min='1';cpu.max='64';
   const schedule=field('Backup schedule','',undefined,[
     ['off','Off / configure later'],['hourly','Hourly'],['6hours','Every 6 hours'],
     ['12hours','Every 12 hours'],['daily','Daily'],['weekly','Weekly'],
     ['custom','Custom interval']]);
   const interval=field('Backup interval (minutes, custom)','number','1440');interval.min='15';interval.max='10080';
   const repo=field('Existing Restic backup repository','text','');
   repo.placeholder='/mnt/backups/minecraft-restic';
   const exportDir=field('Restore export directory (optional)','text','');
   exportDir.placeholder='/srv/minecraft-restore';
   name.addEventListener('input',()=>{
     const slug=name.value;
     if(path.dataset.userEdited!=='true')path.value='/opt/minecraft/managed/'+slug;
   });
   path.addEventListener('input',()=>path.dataset.userEdited='true');
   wrap.append(fields);
   const accept=el('label','mp-wizard-eula');
   const eula=el('input');eula.type='checkbox';
   accept.append(eula,document.createTextNode(' I have read and agree to the Minecraft EULA for a new server.'));
   wrap.append(accept);
   const actions=el('div','toolbar');
   const review=el('button','btn secondary','Review server setup');
   review.type='button';
   const close=el('button','btn secondary','Close setup');
   close.type='button';close.onclick=()=>wrap.remove();
   actions.append(review,close);wrap.append(actions);
   const report=el('pre','mp-wizard-report');
   report.textContent='No server will be created during review.';
   wrap.append(report);
   review.onclick=async()=>{
     review.disabled=true;report.textContent='Checking selected release and server settings…';
     try{
       const plan=await browse('server-plan',project.id,file.id,name.value,path.value,
         ram.value,cpu.value,port.value,repo.value,schedule.value,interval.value,
         exportDir.value,String(eula.checked));
       report.textContent=JSON.stringify(plan,null,2);
       if(!plan.create_enabled){
         report.textContent+='\\n\\nCreation remains disabled: '+plan.next_step;
       }
     }catch(err){report.textContent='Setup review failed: '+String(err.message||err);}
     finally{review.disabled=false;}
   };
   container.append(wrap);
 };
 const displayProject=async(id,card,button)=>{
   // One expanded panel at a time, immediately below the corresponding result.
   if(activeCard===card&&!detailPanel.hidden){
     activeDetails++;
     detailPanel.hidden=true;
     detailPanel.remove();
     button.setAttribute('aria-expanded','false');
     button.textContent='Details / versions';
     activeCard=null;
     return;
   }
   if(activeCard){
     const previous=activeCard.querySelector('[aria-expanded="true"]');
     if(previous){previous.setAttribute('aria-expanded','false');previous.textContent='Details / versions';}
   }
   activeCard=card;
   button.setAttribute('aria-expanded','true');
   button.textContent='Hide details';
   card.after(detailPanel);
   const detailId=++activeDetails;
   detailPanel.hidden=false;
   detailPanel.classList.add('mp-browser-inline-detail');
   detailPanel.replaceChildren(el('p','hint','Loading project overview…'));
   try{
     const d=await browse('project',id);
     if(detailId!==activeDetails)return;
     detailPanel.replaceChildren();
     const headingRow=el('div','mp-browser-project-heading');
     const art=safeUrl(d.icon);
     if(art){
       const img=el('img','mp-browser-icon');
       img.src=art;img.alt=d.name+' icon';img.loading='lazy';img.width=80;img.height=80;img.referrerPolicy='no-referrer';
       headingRow.append(img);
     }
     const info=el('div','');
     info.append(el('h3','',d.name),el('p','',d.summary||'No summary available.'));
     headingRow.append(info);detailPanel.append(headingRow);
     if(d.authors?.length)detailPanel.append(el('p','hint','By '+d.authors.join(', ')));
     const descriptionLabel=el('h4','','Description');
     const desc=el('div','mp-browser-description','Loading description…');
     desc.setAttribute('role','region');
     desc.setAttribute('aria-label','Project description');
     detailPanel.append(descriptionLabel,desc);
     const filesTitle=el('h4','','Available release files');
     const releases=el('div','');
     const loadFilesButton=el('button','btn secondary','Load release versions');
     loadFilesButton.type='button';
     releases.append(loadFilesButton,el('p','hint','Release files are loaded only when requested to keep the Cockpit page responsive.'));
     detailPanel.append(filesTitle,releases);
     // Separate slow network requests from the initial project display.
     browse('description',id).then(data=>{
       if(detailId===activeDetails)desc.textContent=data.description||'No description available.';
     }).catch(err=>{if(detailId===activeDetails)desc.textContent='Description unavailable: '+String(err.message||err);});
     loadFilesButton.onclick=async()=>{
       loadFilesButton.disabled=true;loadFilesButton.textContent='Loading releases…';
       try{
         const files=await browse('files',id);
         if(detailId!==activeDetails)return;
         releases.replaceChildren();
         if(!files.length){releases.append(el('p','hint','No release files reported.'));return;}
         const supported=[...new Set(files.flatMap(f=>(f.game_versions||[]).filter(mcVersion)))];
         if(supported.length)releases.append(el('p','hint','Minecraft versions in these releases: '+supported.join(', ')));
         const fileLabel=el('label','field','Select release');
         const choice=el('select');
         for(const file of files){
           const vs=(file.game_versions||[]).filter(mcVersion).join(', ');
           choice.add(new Option(file.name+' — '+(vs||'Minecraft version not specified'),String(file.id)));
         }
         fileLabel.append(choice);releases.append(fileLabel);
         const select=el('button','btn secondary','Use selected file in workspace');
         select.type='button';
         select.onclick=()=>{
           const found=files.find(f=>String(f.id)===choice.value);
           if(!found)return;
           $m('mp-project-id').value=d.id;$m('mp-file-id').value=found.id;
           say('Selected '+d.name+' / '+found.name+'. Choose a workspace and click Add compatible file. No download was performed.');
         };
         const createServer=el('button','btn secondary','Create Minecraft server…');
         createServer.type='button';
         createServer.onclick=()=>{
           const chosen=files.find(f=>String(f.id)===choice.value);
           if(!chosen)return;
           showServerWizard(d,chosen,releases);
         };
         releases.append(select,createServer,
           el('p','hint','Showing up to 50 latest files; server pack, loader and dependency compatibility must be verified before installation.'));
       }catch(err){
         if(detailId===activeDetails){
           loadFilesButton.disabled=false;loadFilesButton.textContent='Retry loading releases';
           releases.append(el('p','hint','Release lookup failed: '+String(err.message||err)));
         }
       }
     };
   }catch(e){
     if(detailId===activeDetails)detailPanel.replaceChildren(el('p','',String(e.message||e)));
   }
 };
 loadVersions();
 loadCategories();
 $m('mp-new').onclick=()=>run('Create custom modpack manifest',async()=>{const r=await call('create-manifest',$m('mp-name').value,$m('mp-version').value,$m('mp-loader').value);await update();return r});
 $m('mp-import').onclick=async()=>{
   const file=$m('mp-zip').files[0];if(!file)return say('Choose a ZIP file first.',true);
   if(file.size>1024*1024*1024)return say('ZIP exceeds 1 GiB limit.',true);
   const name=$m('mp-name').value;
   if(!confirm('Stage '+file.name+' in a NEW isolated modpack workspace '+name+'? The archive will be inspected and cannot modify existing Minecraft servers.'))return;
   say('Uploading ZIP and validating archive…');
   try{
     const bytes=new Uint8Array(await file.arrayBuffer());
     const proc=cockpit.spawn([exe,'import',name,file.name],{superuser:'require',err:'message',binary:true});
     proc.input(bytes);
     const output=await proc;
     const decoded=new TextDecoder().decode(new Uint8Array(output));const data=JSON.parse(decoded);
     if(!data.ok)throw Error(data.error);say(data.data);await update();
   }catch(e){say('Import failed: '+(e.message||e),true)}
 };
 $m('mp-detail').onclick=()=>run('Inspect workspace',()=>call('detail',$m('mp-workspace').value));
 $m('mp-addmod').onclick=()=>run('Add mod to manifest',()=>call('add-mod',$m('mp-workspace').value,$m('mp-project-id').value,$m('mp-file-id').value));
 const chosen=()=>{const id=$m('mp-workspace').value;if(!id)throw Error('Select a workspace first');return id};
 $m('mp-loader-plan').onclick=()=>run('Loader plan and official available versions',()=>call('loader-plan',chosen()));
 $m('mp-preflight').onclick=()=>run('Read-only deployment preflight',()=>call('preflight',chosen()));
 $m('mp-stage-fabric').onclick=()=>{let id;try{id=chosen()}catch(e){return say(e.message,true)}
   if(!confirm('Download the official Fabric launcher into NEW workspace '+id+'? No server will start.'))return;
   run('Stage Fabric launcher',async()=>{const r=await call('stage-fabric',id,$m('mp-fabric-loader').value.trim(),$m('mp-fabric-installer').value.trim());await update();return r});
 };
 $m('mp-deploy').onclick=()=>{let id;try{id=chosen()}catch(e){return say(e.message,true)}if(!$m('mp-eula').checked)return say('Accept the Minecraft EULA before deploying.',true);if(!confirm('Deploy '+id+' as a NEW stopped Minecraft service? Only use known standalone server.jar packs.'))return;run('Deploy',async()=>{const r=await call('deploy',id,$m('mp-port').value,$m('mp-ram').value,'accept');await update();return r})};
 $m('mp-snapshot').onclick=()=>run('Create full snapshot',()=>call('snapshot',chosen()));
 $m('mp-snapshots').onclick=()=>run('List snapshots',()=>call('snapshots',chosen()));
 $m('mp-logs').onclick=()=>run('Server logs',()=>call('logs',chosen()));
 $m('mp-mods').onclick=()=>run('Installed mods',()=>call('inventory',chosen()));
 $m('mp-restore').onclick=()=>{let id;try{id=chosen()}catch(e){return say(e.message,true)}const snap=$m('mp-snapshot-id').value.trim();if(!confirm('Restore snapshot '+snap+' for '+id+'? Server MUST be stopped. A current-state snapshot will be created first.'))return;run('Restore full snapshot',()=>call('restore',id,snap))};
 for(const [button,op] of [['mp-disable','mod-disable'],['mp-enable','mod-enable']]){
   $m(button).onclick=()=>{let id;try{id=chosen()}catch(e){return say(e.message,true)}const mod=$m('mp-mod-file').value.trim();if(!confirm(op+' '+mod+' on stopped server '+id+'? A full backup will be made first.'))return;run('Change mod state',()=>call(op,id,mod))};
 }
 $m('mp-export').onclick=()=>run('Export manifest',async()=>{
   const value=await call('export',$m('mp-workspace').value);
   const blob=new Blob([JSON.stringify(value,null,2)],{type:'application/json'});
   const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=value.id+'-modpack-manifest.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
   return 'Manifest exported (metadata only, not a playable modpack ZIP).';
 });
 document.querySelectorAll('[data-tab="modpacks"]').forEach(b=>b.addEventListener('click',()=>run('Refresh modpack workspaces',update)));
})();
