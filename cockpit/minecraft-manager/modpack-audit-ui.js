"use strict";
(()=>{
 const by=id=>document.getElementById(id);
 const exe='/usr/local/libexec/cockpit-minecraft-modpack-audit';
 const output=by('mp06-output');if(!output)return;
 let working=false;
 async function call(op,...args){
  if(working)return; working=true;
  const buttons=['mp06-audit','mp06-guidance','mp06-readiness','mp06-preview','mp07-sources','mp07-backup'].map(by);
  for(const b of buttons)b.disabled=true;
  output.textContent='Checking '+op+'…';
  try{
   const id=by('mp-workspace').value;
   if(!id)throw Error('Select a modpack workspace first.');
   const raw=await cockpit.spawn([exe,op,id,...args],{superuser:'require',err:'message'});
   let data;try{data=JSON.parse(raw)}catch{throw Error('Invalid helper response')}
   output.textContent=JSON.stringify(data,null,2);
  }catch(e){output.textContent='Error: '+(e.message||String(e))}
  finally{working=false;for(const b of buttons)b.disabled=false;}
 }
 by('mp07-sources').onclick=()=>call('loader-source-plan');
 by('mp07-backup').onclick=()=>{const path=by('mp07-backup-path').value.trim(); if(!path){output.textContent='Enter an existing backup destination directory.';return} call('backup-destination-plan',path)};
 by('mp06-audit').onclick=()=>call('audit');
 by('mp06-guidance').onclick=()=>call('loader-guidance');
 by('mp06-readiness').onclick=()=>call('update-readiness');
 by('mp06-preview').onclick=()=>{
  const path=by('mp06-zip-path').value.trim();
  if(!path){output.textContent='Enter a server-side ZIP path first.';return}
  call('update-preview',path)
 };
})();
