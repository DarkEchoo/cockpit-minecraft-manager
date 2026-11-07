"use strict";
(()=>{
 const by=id=>document.getElementById(id), exe='/usr/local/libexec/cockpit-minecraft-backup-center';
 const output=by('mp09-output');if(!output)return;
 const controls=['history','backup','activity','verify','restore-test','retention'].map(x=>by('mp09-'+x));
 let pending=false;
 async function request(op,...args){
  if(pending)return;
  const id=by('mp-workspace')?.value;
  if(!id){output.textContent='Select a workspace first.';return;}
  if(op==='backup'&&!window.confirm('Create a backup ONLY if '+id+' is stopped? The helper will enforce stopped state.'))return;
  pending=true;controls.forEach(x=>x.disabled=true);output.textContent='Running '+op+'…';
  try{
   const params=op==='verify'||op==='restore-test'?args: [id,...args];
   const raw=await cockpit.spawn([exe,op,...params],{superuser:'require',err:'message'});
   const r=JSON.parse(raw);
   output.textContent=JSON.stringify(r,null,2);
  }catch(e){output.textContent='Error: '+(e.message||e)}
  finally{controls.forEach(x=>x.disabled=false);pending=false}
 }
 by('mp09-history').onclick=()=>request('history');
 by('mp09-activity').onclick=()=>request('activity');
 by('mp09-backup').onclick=()=>request('backup');
 by('mp09-retention').onclick=()=>request('retention-preview',by('mp09-keep').value);
 const path=()=>by('mp09-archive').value.trim();
 by('mp09-verify').onclick=()=>{if(path())request('verify',path());else output.textContent='Provide an archive path.'};
 by('mp09-restore-test').onclick=()=>{if(path())request('restore-test',path());else output.textContent='Provide an archive path.'};
})();
