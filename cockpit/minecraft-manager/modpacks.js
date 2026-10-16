'use strict';
// Independent Modpack Workspaces panel. Existing server controls are not changed.
(()=>{
 const $m=id=>document.getElementById(id);
 const exe='/usr/local/libexec/cockpit-minecraft-modpacks';
 const say=(s,error=false)=>{const el=$m('mp-output');el.textContent=typeof s==='string'?s:JSON.stringify(s,null,2);el.style.color=error?'#ff9999':''};
 const call=async(op,...args)=>{
   const output=await cockpit.spawn([exe,op,...args.map(String)],{superuser:'require',err:'message'});
   let data;try{data=JSON.parse(output);}catch{throw Error('Malformed modpack helper response')}
   if(!data.ok)throw Error(data.error||'Operation failed');return data.data;
 };
 const run=async(label,fn)=>{say(label+'…');try{say(await fn())}catch(e){say(label+': '+(e.message||String(e)),true)}};
 const update=async()=>{
   const r=await call('status');$m('mp-key').textContent=r.key_configured?'CurseForge API key configured':'No CurseForge API key; local ZIP import is available';
   const sel=$m('mp-workspace'),last=sel.value;sel.replaceChildren(new Option('Choose workspace',''));
   for(const p of r.workspaces)sel.add(new Option(p.name+' — '+p.status,p.name));sel.value=last;
   $m('mp-workspaces').textContent=r.workspaces.map(p=>p.name+' | '+p.loader+' | '+p.minecraft_version+' | '+p.status).join('\n')||'No modpack workspaces yet.';
 };
 $m('mp-refresh').onclick=()=>run('Load workspaces',update);
 $m('mp-search').onclick=()=>run('CurseForge search',async()=>{
   const results=await call('search',$m('mp-query').value,$m('mp-category').value,$m('mp-search-version').value.trim());
   $m('mp-results').replaceChildren();
   for(const p of results){const item=document.createElement('div');item.className='sub-panel';
     const title=document.createElement('strong');title.textContent=p.name+' (#'+p.id+')';
     const summary=document.createElement('p');summary.textContent=p.summary;
     const button=document.createElement('button');button.className='btn secondary';button.textContent='List releases / server packs';
     button.onclick=()=>run('CurseForge releases',async()=>{const files=await call('files',p.id);$m('mp-project-id').value=p.id;return files});
     item.append(title,summary,button);$m('mp-results').append(item);
   }
   return results.length+' projects found. Select a project to inspect files. Downloads require explicit approved API access; no server is installed automatically.';
 });
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
