'use strict';
(()=>{
 const $=id=>document.getElementById(id);
 const helper='/usr/local/libexec/cockpit-minecraft-join-control';
 const state=$('join-live-state');
 if(!state)return;
 async function call(op,payload){
   const options={superuser:'require',err:'message'};
   const process=cockpit.spawn([helper,op],options);
   // cockpit.spawn ignores an options.input field. Send JSON through stdin.
   if(payload!==undefined)process.input(JSON.stringify(payload));
   const raw=await process;
   const obj=JSON.parse(raw);
   if(!obj.ok)throw Error(obj.error||'Operation failed');
   return obj.data;
 }
 async function safe(fn){try{await fn();}catch(e){state.textContent='Error: '+String(e.message||e);}}
 async function refresh(){const info=await call('status');
   $('join-message').value=info.config.join_message;
   $('leave-message').value=info.config.leave_message;
   $('join-color').value=info.config.color;
   state.textContent=(info.active?'Running':'Stopped')+' · Startup '+(info.enabled?'enabled':'disabled')+' · Vanilla only';
 }
 $('join-load').onclick=()=>safe(refresh);
 $('join-save').onclick=()=>safe(async()=>{
    if(!confirm('Save join and leave templates for Vanilla Minecraft? The announcer service may briefly restart. Minecraft will not restart.'))return;
    const result=await call('save',{join_message:$('join-message').value,leave_message:$('leave-message').value,color:$('join-color').value});state.textContent=result.message;await refresh();
 });
 $('join-enable').onclick=()=>safe(async()=>{const r=await call('enable');state.textContent=r.message;await refresh();});
 $('join-disable').onclick=()=>safe(async()=>{if(!confirm('Disable custom join/leave announcements?'))return;const r=await call('disable');state.textContent=r.message;await refresh();});
 $('join-test').onclick=()=>safe(async()=>{const r=await call('test');state.textContent=r.message;});
 $('join-history-load').onclick=()=>safe(async()=>{$('join-history').textContent=(await call('history')).lines||'No recorded activity yet.';});
 // Other manager tabs and periodic announcements are unaffected.
 refresh().catch(e=>{state.textContent='Announcer unavailable: '+String(e.message||e);});
})();
