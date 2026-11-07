"use strict";
(()=>{
 const el=id=>document.getElementById(id), out=el('mp11-output');
 if(!out)return;
 const buttons=['status','check','enable','disable'].map(x=>el('mp11-'+x));
 let busy=false;
 async function action(op){
  if(busy)return;
  const workspace=el('mp-workspace')?.value;
  if(!workspace){out.textContent='Select a workspace.';return;}
  if(op==='enable'&&!confirm('Enable the DAILY backup timer for the configured workspace? The timer will run automatically at its next scheduled time, but will refuse an active server.'))return;
  if(op==='disable'&&!confirm('Disable the configured backup timer? This will not stop Minecraft.'))return;
  busy=true;buttons.forEach(b=>b.disabled=true);out.textContent='Checking scheduler…';
  try{
   const raw=await cockpit.spawn(['/usr/local/libexec/cockpit-mc-schedule',op,workspace],{superuser:'require',err:'message'});
   const res=JSON.parse(raw);out.textContent=JSON.stringify(res,null,2);
  }catch(e){out.textContent='Error: '+(e.message||e)}
  finally{busy=false;buttons.forEach(b=>b.disabled=false)}
 }
 ['status','check','enable','disable'].forEach(op=>el('mp11-'+op).onclick=()=>action(op));
})();
