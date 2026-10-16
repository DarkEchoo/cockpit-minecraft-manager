'use strict';
const $ = id => document.getElementById(id);
// CONSOLE_PREFIX_V6: Shared Minecraft tellraw formatter, raw RCON commands unaffected.
const consoleSenderColors=['red','dark_red','gold','yellow','green','aqua','blue','white','gray'];
function consoleBroadcastCommand(text, color='white', bold=false) {
  if(typeof text!=='string'||!text.length||text.length>140||/[\x00-\x1f\x7f]/.test(text))throw Error('Invalid announcement text');
  if(!consoleSenderColors.includes(color))throw Error('Invalid message color');
  return 'tellraw @a '+JSON.stringify([
    {text:'[Console]: ',color:'red',bold:true},
    {text:text,color:color,bold:!!bold}
  ]);
}

let servers = [];
let busy = false;
function message(t, bad=false) { $('message').textContent=t; $('message').style.color=bad?'#c22':'inherit'; }
async function api(...args) {
  const result = await cockpit.spawn(['/usr/local/libexec/cockpit-minecraft-helper', ...args], {superuser:'require', err:'message'});
  let data;
  try {data = JSON.parse(result);} catch {throw Error('Unexpected helper output: '+result.slice(0,300));}
  if (!data.ok) throw Error(data.error||'Command failed');
  return data.data;
}
async function action(label, fn) {
  if(busy) return;
  busy=true; message(label+'...');
  document.querySelectorAll('button').forEach(b=>b.disabled=true);
  try {await fn();message(label+' completed.');}catch(e){message(label+': '+String(e.message||e),true);}
  finally {busy=false;document.querySelectorAll('button').forEach(b=>b.disabled=false);display(); updateEditingGuards();}
}
function selection(){return $('server').value;}
async function refresh() {
  const previous=selection();
  const data=await api('list');servers=data;
  $('server').replaceChildren();
  for(const s of data){const opt=document.createElement('option');opt.value=s.id;opt.textContent=`${s.label} (${s.state})`; $('server').append(opt);}
  if(data.some(x=>x.id===previous))$('server').value=previous;
  display(); syncBrandingTargets(); await logs(); await loadPlayerActivity(); await loadFiles();
}
function display(){const s=servers.find(x=>x.id===selection());if(!s)return;
 $('info').textContent=`Service: ${s.unit} | Status: ${s.state} | Port: ${s.port} | Directory: ${s.path}`;
 $('send').disabled=!s.rcon || s.state!=='active';$('command').disabled=!s.rcon || s.state!=='active';
 $('enable-rcon').disabled=s.id==='neoforge'||s.rcon||s.state==='active';
 $('backup').textContent='Back up '+s.label+' now';
 updateEditingGuards();
 $('rcon-status').textContent=s.rcon?'RCON configured':(s.state==='active'?'RCON not configured — stop server to enable':'RCON not configured');
}
async function logs(){if(!selection() ||busy)return;try{$('logs').textContent=await api('logs',selection());$('logs').scrollTop=$('logs').scrollHeight;}catch(e){$('logs').textContent='Unable to read logs: '+e.message;}}
async function service(op) {const s=servers.find(x=>x.id===selection());if(!s)return;
 if(op==='stop' || op==='restart' || op==='start') {const others=servers.filter(x=>x.id!==s.id&&x.state==='active').map(x=>x.label);if(!confirm(`${op.toUpperCase()} ${s.label}?`+(others.length?`\n\nTo maintain one running server, this will STOP: ${others.join(', ')}.`:'')+((op==='stop'||op==='restart')?'\nConnected players may be disconnected.':'')))return;}
 await action(op+' '+s.label,async()=>{await api('service',s.id,op);await refresh();});}
$('server').addEventListener('change',()=>{display();$('backup-list').textContent='Click Refresh selected server history.';logs();loadPlayerActivity();loadFiles();loadBackupSettings();});
$('refresh').onclick=()=>action('Refresh',refresh);
$('start').onclick=()=>service('start');$('stop').onclick=()=>service('stop');$('restart').onclick=()=>service('restart');
$('enable-rcon').onclick=()=>{const s=servers.find(x=>x.id===selection());if(!s || s.id==='neoforge')return;
 if(!confirm(`Enable local-only RCON on ${s.label}? The server must be stopped. This modifies only its server.properties.`))return;
 action('Enable RCON',async()=>{const result=await api('enable-rcon',s.id);await refresh();message(result);});};
$('switch').onclick=()=>{const s=servers.find(x=>x.id===selection());if(!s)return;
 const others=servers.filter(x=>x.id!==s.id&&x.state==='active').map(x=>x.label);
 if(!confirm(`Switch to ${s.label}?\n\nThis will STOP: ${others.length?others.join(', '):'no other active servers'}.\nThen start the selected server. Connected players will be disconnected.`))return;
 action('Switch server',async()=>{await api('switch',s.id);await refresh();});};
$('send').onclick=()=>{let cmd=$('command').value.trim();if(!cmd)return;
 action('RCON command',async()=>{const r=await api('command',selection(),cmd);$('logs').textContent+=`\n> ${cmd}\n${r}\n`;$('command').value='';});};
$('command').addEventListener('keydown',e=>{if(e.key==='Enter')$('send').click();});
$('backup').onclick=()=>{const s=servers.find(x=>x.id===selection());if(!s)return;
 if(!confirm(`Back up ${s.label} to your encrypted Restic repository?\n\nIf it is running, this temporarily stops and restarts that server. Connected players will be disconnected.`))return;
 action('Manual backup',async()=>{const msg=await api('backup',s.id);$('backup-list').textContent=await api('snapshots',s.id);await refresh();message(msg);});};
async function loadBackupSettings(){
 const id=selection(); if(!id)return;
 try {const s=await api('backup-settings',id);
  $('backup-schedule').value=s.schedule;
  $('backup-interval').value=s.interval_minutes;
  $('backup-repository').value=s.repository;
  $('backup-repository').readOnly=!!s.legacy_repository_locked;
  $('backup-repo-note').textContent=s.legacy_repository_locked?'NeoForge uses its existing backup service; repository locked to protect existing snapshots.':'Repository must already be initialized and mounted. No migration is performed.';
  $('restore-export-directory').value=s.restore_export;
  $('backup-schedule-status').textContent=s.schedule==='off'?'Automatic backups disabled.':'Enabled: '+s.schedule;
 }catch(e){$('backup-schedule-status').textContent='Settings unavailable: '+e.message;}
}
$('backup-settings-save').onclick=()=>{
 const id=selection(),schedule=$('backup-schedule').value;
 if(schedule!=='off'&&!confirm('Enable automatic backups for '+id+'? Running servers may temporarily stop; players may be disconnected.'))return;
 action('Save backup settings',async()=>{
   await api('backup-settings-save',id,$('backup-repository').value.trim(),$('restore-export-directory').value.trim(),schedule,$('backup-interval').value);
   await loadBackupSettings();
 });
};
$('restore-export-go').onclick=()=>{
 const id=selection(),snapshot=$('restore-select').value;
 if(!snapshot)return message('Load and select a snapshot first.',true);
 if(!confirm('Export the selected snapshot into the configured EMPTY directory? Live server files will not change.'))return;
 action('Export restore snapshot',async()=>{const result=await api('restore-export',id,snapshot);$('restore-status').textContent=result;message(result);});
};
$('snapshots').onclick=()=>action('Backup history',async()=>{$('backup-list').textContent=await api('snapshots',selection());});
$('load-versions').onclick=()=>action('Load versions',async()=>{const vv=await api('versions');$('version').replaceChildren();vv.forEach(v=>{const o=document.createElement('option');o.value=v;o.textContent=v;$('version').append(o);});});
$('check-build').onclick=()=>{const id=selection(),found=servers.find(s=>s.id===id);if(!found||!found.label.startsWith('Spigot ')){ $('build-log').textContent='Select a managed Spigot server from the main server selector first.';return; }action('Check Spigot build status',async()=>{const r=await api('build-status',id);$('build-log').textContent='Status: '+r.status+'\n'+r.log;});};
$('relocate-server').onclick=()=>{const s=servers.find(x=>x.id===selection()),dir=$('move-directory').value.trim();if(!s||!dir)return message('Enter a new destination directory.',true);if(s.id==='neoforge'||s.state!=='inactive')return message('Stop a managed Vanilla or Spigot server first.',true);if(!confirm(`Copy ${s.id} to ${dir}? The original files are kept and the service directory will change.`))return;action('Relocate server',async()=>{const result=await api('relocate',s.id,dir);await refresh();message(result);});};

// Automatically normalize new Minecraft server names.
function normalizeServerName(value) {
  return value.toLowerCase()
    .replace(/['’]/g, '')
    .replace(/\s+/g, '-')
    .replace(/[^a-z0-9-]/g, '')
    .replace(/-+/g, '-')
    .replace(/^-+/g, '');
}
$('name').addEventListener('input', function() {
  const cursor = this.selectionStart;
  const normalized = normalizeServerName(this.value);
  const prefix = normalizeServerName(this.value.slice(0, cursor));
  this.value = normalized;
  this.setSelectionRange(prefix.length, prefix.length);
});

$('create').onclick=()=>{
 const name=normalizeServerName($('name').value).replace(/-+$/g,'');
 $('name').value=name;
 if(!/^[a-z][a-z0-9-]{1,34}$/.test(name)){
   message('Server name must be 2-35 characters, start with a letter, and contain only lowercase letters, numbers or hyphens.',true);
   return;
 }
 const version=$('version').value,port=$('port').value;
 if(!$('eula').checked){message('You must accept the Minecraft EULA.',true);return;}

 const schedule=$('create-backup-schedule').value;
 const interval=$('create-backup-interval').value;
 const repository=$('create-backup-repository').value.trim();
 const restoreExport=$('create-restore-export').value.trim();
 if(schedule!=='off'&&!confirm('Automatic backups will be enabled after server creation. Backup jobs may briefly stop the server and disconnect players. Continue?'))return;
 action('Create server',async()=>{
   const result=await api('create-with-backup',name,version,port,$('server-type').value,$('create-directory').value.trim(),repository,restoreExport,schedule,interval);
   await refresh();
   $('server').value=name;display();await loadBackupSettings();
   message('Created '+name+'; backups: '+result.backup_schedule+'. Server remains stopped.');
 });};
refresh().then(loadBackupSettings).catch(e=>message('Unable to load Minecraft servers: '+e.message,true));
// Avoid unnecessary Cockpit bridge processes and journal reads on hidden tabs.
let logRefreshRunning=false;
let metricsRefreshRunning=false;
let previousCpuSample=null;
async function smartRefresh() {
  if (document.hidden || busy) return;
  const active=document.querySelector('[data-view="console"].active');
  if (active && !logRefreshRunning) {
    logRefreshRunning=true;
    try { await logs(); await loadPlayerActivity(); } finally { logRefreshRunning=false; }
  }
  if (document.querySelector('[data-view="performance"].active') && !metricsRefreshRunning) {
    metricsRefreshRunning=true;
    try { await loadMetrics(false); } finally { metricsRefreshRunning=false; }
  }
}
setInterval(smartRefresh, 15000);

// Privileged file operations accept only paths validated by the Python helper.
let fileEntries=[];let openedFile='';
async function fileInput(op,args,input,binary=false){
 const proc=cockpit.spawn(['/usr/local/libexec/cockpit-minecraft-helper',op,...args],{superuser:'require',err:'message',binary});
 proc.input(input);
 let output=await proc;
 if(binary){output=new TextDecoder().decode(new Uint8Array(output));}
 let parsed;
 try{parsed=JSON.parse(output);}catch{throw Error('Unexpected helper output');}
 if(!parsed.ok)throw Error(parsed.error||'File action failed');
 return parsed.data;
}
async function loadFiles(){
 openedFile='';$('file-editor').style.display='none';$('file-save').style.display='none';$('file-label').textContent='';
 const id=selection();if(!id)return;
 try{
   fileEntries=await api('files',id);
   $('file-select').replaceChildren(new Option('Select a file', ''));
   fileEntries.forEach(f=>$('file-select').add(new Option(`${f.path} (${f.bytes} bytes)`,f.path)));
 }catch(e){$('file-label').textContent='Unable to list files: '+e.message;}
 updateUpload();
}
function updateUpload(){
 let id=selection(),s=servers.find(x=>x.id===id);
 let kind=$('upload-kind').value;
 let type=id==='neoforge'?'neoforge':s?.label?.toLowerCase().startsWith('spigot')?'spigot':'vanilla';
 let incompatible=(kind==='mods'&&type!=='neoforge')||(kind==='plugins'&&type!=='spigot');
 $('upload-button').disabled=incompatible||s?.state!=='inactive'&&s?.state!=='failed';
 $('upload-status').textContent=incompatible?`The ${kind} folder is not supported for this server type.`:(s?.state==='active'?'Stop this server before uploading files.':'');
}
$('server').addEventListener('change',updateUpload);
$('upload-kind').onchange=updateUpload;
$('file-refresh').onclick=()=>action('Refresh files',loadFiles);
$('file-open').onclick=()=>action('Read config',async()=>{
 const id=selection(),rel=$('file-select').value,entry=fileEntries.find(f=>f.path===rel);
 if(!entry||entry.kind!=='config')throw Error('Choose a configuration file to edit');
 const data=await api('file-read',id,rel);
 openedFile=rel;$('file-editor').value=data;$('file-label').textContent=rel+(rel==='server.properties'?' — live-safe keys apply through RCON; other edits require restart':' — stop the server before saving');
 $('file-editor').style.display='block';$('file-save').style.display='inline-block';updateEditingGuards();
});
$('file-save').onclick=()=>{
 const id=selection(),rel=openedFile;if(!rel)return;
 if(!confirm(`Save ${rel} in ${id}? A .cockpit-backup copy will be created. If server.properties is saved while running, only supported commands can apply live; all other edits require restart. No automatic restart.`))return;
 action('Save configuration',async()=>{
   const result=await fileInput('file-save',[id,rel],$('file-editor').value);
   await loadFiles();message(result);
 });
};
$('upload-button').onclick=()=>{
 const file=$('upload-file').files[0],id=selection(),kind=$('upload-kind').value;
 if(!file){message('Select a file to upload.',true);return;}
 if(file.size>(kind==='icon'?2:300)*1024*1024){message('File too large.',true);return;}
 if(!confirm(`Upload ${file.name} (${file.size} bytes) to ${id}? The server must be stopped.`))return;
 action('Upload file',async()=>{
   // Cockpit supports binary streaming to process stdin; no public upload endpoint.
   const bytes=new Uint8Array(await file.arrayBuffer());
   const result=await fileInput('file-upload',[id,kind,file.name],bytes,true);
   $('upload-file').value='';await loadFiles();message(result);
 });
};

// The browser guard is UX only. Every privileged write is separately checked
// against systemd state by the helper immediately before modifying disk.
function updateEditingGuards(){
 const s=servers.find(x=>x.id===selection()); const can=!!s&&s.state==='inactive'&&!busy;
 const live=!!s&&s.state==='active'&&!busy;
 const canEdit=can||(live&&openedFile==='server.properties');
 $('file-save').disabled=!canEdit||!openedFile;
 $('file-editor').readOnly=!canEdit;
 $('settings-save').disabled=!(can||live)||!settingsLoaded;
 $('restore-go').disabled=!can||!$('restore-select').value;
 $('settings-warning').textContent=can?'Server stopped: settings save for next start.':live?'Server running: difficulty, default gamemode and whitelist may apply via RCON; other settings require restart. World restores remain locked.':'Server changing state: editing locked.';
 document.querySelectorAll('.addon-toggle').forEach(b=>b.disabled=!can);
}
const settingTypes={
 'white-list':['bool'], 'enforce-whitelist':['bool'],
 difficulty:['enum','peaceful','easy','normal','hard'],
 gamemode:['enum','survival','creative','adventure','spectator'],
 hardcore:['bool'],pvp:['bool'],
 'max-players':['number',1,200], 'view-distance':['number',2,32],
 'simulation-distance':['number',2,32], 'motd':['text'],
 'spawn-protection':['number',0,128]
};
let settingsLoaded=false;
async function loadSettings(){
 settingsLoaded=false; $('settings-fields').replaceChildren(); updateEditingGuards();
 const vals=await api('settings',selection());
 for(const [name, spec] of Object.entries(settingTypes)){
   const label=document.createElement('label');label.className='field';label.textContent=name;
   let input;
   if(spec[0]==='bool'||spec[0]==='enum'){
     input=document.createElement('select');
     const options=spec[0]==='bool'?['true','false']:spec.slice(1);
     for(const value of options)input.add(new Option(value,value));
   }else{
     input=document.createElement('input');input.type=spec[0];
     if(spec[0]==='number'){input.min=spec[1];input.max=spec[2];input.step='1';}
     else input.maxLength=120;
   }
   input.dataset.setting=name;
   input.value=vals[name]??(spec[0]==='bool'?'false':spec[0]==='number'?String(spec[1]):'');
   label.append(input);$('settings-fields').append(label);
 }
 settingsLoaded=true;updateEditingGuards();
}
$('settings-refresh').onclick=()=>action('Load settings',loadSettings);
$('settings-save').onclick=()=>{
 if(!settingsLoaded)return;
 const s=servers.find(x=>x.id===selection());if(!s||!['active','inactive'].includes(s.state))return;
 if(!confirm(`Save server.properties for ${s.label}? A local backup is created. Supported settings apply live via RCON if running; the rest require a restart. No automatic restart.`))return;
 action('Save settings',async()=>{
   const vals={};document.querySelectorAll('[data-setting]').forEach(el=>vals[el.dataset.setting]=el.value);
   const result=await fileInput('settings-save',[s.id],JSON.stringify(vals));
   await loadSettings();message(result);
 });
};
async function loadPlayers(){
 const id=selection();let out='';
 for(const cmd of ['list','whitelist-list']){
   try{out+=cmd+': '+await api('players',id,cmd)+'\n';}catch(e){out+=cmd+': '+e.message+'\n';}
 }
 $('players-output').textContent=out;
}
$('players-refresh').onclick=()=>action('Refresh players',loadPlayers);
for(const kind of ['on','off'])$('whitelist-'+kind).onclick=()=>{
 if(!confirm('Turn whitelist '+kind+' on selected server?'))return;
 action('Whitelist '+kind,async()=>{message(await api('players',selection(),'whitelist-'+kind));await loadPlayers();});
};
$('player-apply').onclick=()=>{
 const name=$('player-name').value.trim(),op=$('player-operation').value;
 if(!/^[a-zA-Z0-9_]{3,16}$/.test(name)){message('Enter a valid Minecraft Java username.',true);return;}
 if(!confirm(`${op} ${name} on ${selection()}?`))return;
 action('Player management',async()=>{message(await api('players',selection(),op,name));await loadPlayers();});
};
async function loadMetrics(showMessage=true) {
 const id=selection();
 if(!id)return;
 const d=await api('stats',id);
 if(id!==selection())return;
 const grid=$('stats-grid');grid.replaceChildren();
 let cpuRate='Collecting baseline';
 const now=performance.now();
 if(d.cpu_seconds!=null) {
   if(previousCpuSample && previousCpuSample.id===id && previousCpuSample.pid===d.pid && d.cpu_seconds>=previousCpuSample.cpu) {
     const elapsed=(now-previousCpuSample.time)/1000;
     if(elapsed>0.5)cpuRate=((d.cpu_seconds-previousCpuSample.cpu)/elapsed*100).toFixed(1)+'% of one CPU core';
   }
   previousCpuSample={id,pid:d.pid,cpu:d.cpu_seconds,time:now};
 } else previousCpuSample=null;
 const entries=[['Service',d.state],
 ['RAM (service cgroup)',d.memory_bytes==null?'N/A':(d.memory_bytes/1048576).toFixed(1)+' MiB'],
 ['CPU utilization',cpuRate],
 ['CPU accumulated',d.cpu_seconds==null?'N/A':d.cpu_seconds+' s'],
 ['Uptime',d.uptime_seconds==null?'Offline':Math.floor(d.uptime_seconds/60)+' min'],
 ['Disk free',(d.disk_free_bytes/1073741824).toFixed(1)+' GiB'],
 ['Online players',d.players??'RCON unavailable'],
 ['TPS / MSPT','Not available from this server']];
 for(const [label,value] of entries) {
   const c=document.createElement('div');c.className='stat-card';
   const heading=document.createElement('strong');heading.textContent=label;
   const body=document.createElement('span');body.textContent=String(value);
   c.append(heading,body);grid.append(c);
 }
 if(showMessage)message('Metrics refreshed.');
}
$('stats-refresh').onclick=()=>action('Load performance metrics',()=>loadMetrics());
async function loadAddons(){
 const data=await api('addons',selection()),container=$('addons-list');container.replaceChildren();
 if(!data.length){container.textContent='No supported JAR files found for this server.';return;}
 for(const item of data){const row=document.createElement('div');row.className='addon-row';
 const name=document.createElement('span');name.textContent=item.name+' · '+(item.bytes/1048576).toFixed(2)+' MiB';
 const b=document.createElement('button');b.className='btn secondary addon-toggle';b.textContent=item.enabled?'Disable':'Enable';
 b.onclick=()=>{if(!confirm(`${item.enabled?'Disable':'Enable'} ${item.name}? Server must be stopped.`))return;
 action('Update add-on',async()=>{await api('addon-toggle',selection(),item.name,item.enabled?'disable':'enable');await loadAddons();});};
 row.append(name,b);container.append(row);}
 updateEditingGuards();
}
$('addons-refresh').onclick=()=>action('Load add-ons',loadAddons);
$('restore-refresh').onclick=()=>action('Load recovery snapshots',async()=>{
 const snaps=await api('snapshots-json',selection());
 const target=$('restore-select');target.replaceChildren(new Option('Choose a snapshot...', ''));
 snaps.sort((a,b)=>String(b.time).localeCompare(String(a.time)));
 for(const snap of snaps)target.add(new Option(`${snap.time} · ${snap.id.slice(0,12)}`,snap.id));
 updateEditingGuards();
});
$('restore-select').addEventListener('change',updateEditingGuards);
$('restore-go').onclick=()=>{
 const id=selection(),snap=$('restore-select').value;
 if(!snap||servers.find(s=>s.id===id)?.state!=='inactive')return;
 const response=prompt(`RESTORE will replace files for ${id}. First a recovery snapshot will be created and old files kept.\nType exactly: RESTORE ${id}`);
 if(response!==`RESTORE ${id}`){message('Restore cancelled.');return;}
 action('Restore server snapshot',async()=>{
   const result=await api('restore',id,snap,response);
   $('restore-status').textContent=result;message(result);
   await refresh();
 });
};
$('server').addEventListener('change',()=>{
 settingsLoaded=false;$('settings-fields').replaceChildren();
 $('restore-select').replaceChildren(new Option('Choose a snapshot...', ''));
 $('addons-list').textContent='Click Refresh add-ons.';
 $('players-output').textContent='Click Refresh players.';
 $('stats-grid').textContent='Click Refresh metrics.';
 updateEditingGuards();
});

// World and JVM insights are read-only and requested only when the tab is opened.
let insightsRunning=false;
async function loadInsights() {
  if(insightsRunning || busy || !selection())return;
  insightsRunning=true;
  const selected=selection();
  try {
    const d=await api('insights',selected);
    if(selection()!==selected)return;
    const summary=$('insights-summary');summary.replaceChildren();
    const entries=[
      ['Service',d.state],['JVM maximum heap',d.java.heap_max||'Not detected'],
      ['JVM initial heap',d.java.heap_min||'Not detected'],
      ['Garbage collector',d.java.gc||'JVM default / unknown'],
      ['CPU affinity',d.limits.AllowedCPUs||'System default'],
      ['Memory limit',d.limits.MemoryMax||'System default'],
      ['Service restarts',d.limits.NRestarts||'0'],
      ['Service tasks',d.limits.TasksCurrent||'Unavailable']
    ];
    for(const [name,value] of entries) {
      const item=document.createElement('div');item.className='stat-card';
      const label=document.createElement('strong');label.textContent=name;
      const val=document.createElement('span');val.textContent=String(value);
      item.append(label,val);summary.append(item);
    }
    const worlds=$('insights-worlds');worlds.replaceChildren();
    if(!d.worlds.length)worlds.textContent='No world directories detected.';
    for(const w of d.worlds) {
      const item=document.createElement('div');item.className='stat-card';
      item.textContent=w.name+' — '+(w.bytes/1048576).toFixed(1)+' MiB, '+w.files+' entries'+(w.truncated?' (partial scan)':'');
      worlds.append(item);
    }
    $('insights-notices').textContent=d.notices.length?d.notices.join(' • '):'No warnings from the read-only checks.';
  }catch(e){$('insights-notices').textContent='Insights unavailable: '+e.message;}
  finally{insightsRunning=false;}
}
$('insights-refresh').onclick=loadInsights;
document.querySelectorAll('[data-tab="insights"]').forEach(button=>button.addEventListener('click',loadInsights));

// Operational history is fetched on demand; never retain player names across page reloads.
let opsLoading=false;
async function loadOperations() {
 if(opsLoading||busy||!selection())return;
 opsLoading=true;const id=selection();
 try {
  const [history,policy]=await Promise.all([api('history',id),api('resource-policy',id)]);
  if(id!==selection())return;
  const health=$('ops-health');health.replaceChildren();
  for(const [name,value] of Object.entries(history.summary)) {
    const el=document.createElement('div');el.className='stat-card';
    const heading=document.createElement('strong');heading.textContent=name;
    const body=document.createElement('span');body.textContent=value||'Not reported';
    el.append(heading,body);health.append(el);
  }
  $('ops-scope').textContent=history.scope;
  const events=$('ops-events');events.replaceChildren();
  if(!history.events.length)events.textContent='No matching activity or warnings in the available journal.';
  for(const event of history.events.slice().reverse()) {
    const el=document.createElement('div');el.className='stat-card';
    el.textContent=event.time+' • '+event.type+' • '+event.detail;events.append(el);
  }
  $('ops-policy').textContent='CPU quota: '+(policy.CPUQuotaPerSecUSec||'Unknown')+' • MemoryHigh: '+(policy.MemoryHigh||'Unknown')+' • MemoryMax: '+(policy.MemoryMax||'Unknown')+' • CPU affinity: '+(policy.AllowedCPUs||'Default')+' • Restart: '+(policy.Restart||'Unknown');
  $('ops-apply').disabled=id==='neoforge'||history.summary.ActiveState!=='active';
 }catch(e){$('ops-policy').textContent='Could not load operations: '+e.message;}
 finally{opsLoading=false;}
}
$('ops-refresh').onclick=loadOperations;
document.querySelectorAll('[data-tab="operations"]').forEach(b=>b.addEventListener('click',loadOperations));
$('ops-apply').onclick=()=>{
 const id=selection(),pct=$('ops-quota').value;
 if(id==='neoforge')return message('NeoForge resource changes are disabled.',true);
 if(!confirm('Apply a '+(pct==='off'?'unlimited':pct+'%')+' runtime CPU quota to '+id+'? This may reduce Minecraft performance. No restart or permanent unit change will occur.'))return;
 action('Apply runtime CPU quota',async()=>{const result=await api('cpu-quota',id,pct);message('Applied '+result.applied+' (runtime only). Refresh Operations to verify.');});
};

// v5: no background polling; bounded session-only performance snapshots.
const ccSamples=new Map();
let ccBusy=false;
function ccText(id,value){$(id).textContent=String(value??'Unavailable');}
async function loadControlCenter(){
 if(ccBusy||busy||!selection())return;
 ccBusy=true;const selected=selection();
 try{
  const d=await api('control-center',selected);
  if(selected!==selection())return;
  const health=$('cc-health');health.replaceChildren();
  const entries=[['Service',d.state],['Restart policy',d.restart_policy],
   ['Restart count',d.history.summary.NRestarts],['Last result',d.history.summary.Result],
   ['JVM max heap',d.insights.java.heap_max||'Unknown'],['JVM min heap',d.insights.java.heap_min||'Unknown'],
   ['CPU quota',d.policy.CPUQuotaPerSecUSec||'Default'],
   ['Backup repository',d.backup.repository_detected?'Detected (not verified)':'Not detected']];
  for(const [label,value] of entries){const item=document.createElement('div');item.className='stat-card';
   const strong=document.createElement('strong');strong.textContent=label;
   const span=document.createElement('span');span.textContent=String(value??'Unknown');item.append(strong,span);health.append(item);}
  const events=$('cc-players');events.replaceChildren();
  if(!d.history.events.length)events.textContent='No matching join/leave/crash events in the available journal.';
  for(const ev of d.history.events.slice(-40).reverse()){const div=document.createElement('div');div.className='stat-card';div.textContent=ev.time+' • '+ev.type+' • '+ev.detail;events.append(div);}
  const worlds=$('cc-worlds');worlds.replaceChildren();
  for(const w of d.insights.worlds){const div=document.createElement('div');div.className='stat-card';div.textContent=w.name+' • '+(w.bytes/1048576).toFixed(1)+' MiB'+(w.truncated?' (partial scan)':'');worlds.append(div);}
  if(!d.insights.worlds.length)worlds.textContent='No worlds detected.';
  const samples=ccSamples.get(selected)||[];
  samples.push({time:new Date().toLocaleTimeString(),state:d.state,restarts:d.history.summary.NRestarts});
  if(samples.length>30)samples.shift();ccSamples.set(selected,samples);
  ccText('cc-trends',samples.map(x=>x.time+' • '+x.state+' • restarts '+x.restarts).join('\n'));
  ccText('cc-advice',[...d.recommendations,...d.insights.notices].join(' • '));
 }catch(e){ccText('cc-advice','Control Center unavailable: '+e.message);}
 finally{ccBusy=false;}
}
$('cc-refresh').onclick=loadControlCenter;
document.querySelectorAll('[data-tab="control-center"]').forEach(b=>b.addEventListener('click',loadControlCenter));
$('cc-plan').onclick=async()=>{
 try{const d=await api('resource-plan',selection(),$('cc-min').value,$('cc-max').value,$('cc-cores').value);
 ccText('cc-plan-result',[d.minimum_heap,d.maximum_heap,'CPU quota proposal: '+d.proposed_cpu_quota,
 'Physical RAM: '+d.physical_ram_gib+' GiB',d.status,...d.warnings,d.next_step].join(' • '));}
 catch(e){ccText('cc-plan-result','Invalid plan: '+e.message);}
};

// v6 persistent tuning: opt-in, NeoForge only, server must be stopped.
$('v6-load-heap').onclick=async()=>{try{const d=await api('v6-heap-read');$('v6-min').value=d.minimum_gib;$('v6-max').value=d.maximum_gib;$('v6-heap-status').textContent=`Current: -Xms${d.minimum_gib}G -Xmx${d.maximum_gib}G | ${d.server_state} | ${d.file}`;}catch(e){$('v6-heap-status').textContent=e.message;}};
$('v6-save-heap').onclick=()=>{if(selection()!=='neoforge')return message('Select NeoForge first.',true);const mn=$('v6-min').value,mx=$('v6-max').value;if(!confirm(`Save persistent NeoForge JVM heap -Xms${mn}G -Xmx${mx}G? Server must be stopped. A backup will be created. No restart.`))return;action('Save NeoForge JVM heap',async()=>{const d=await api('v6-heap-save',mn,mx);$('v6-heap-status').textContent=`Saved. Backup: ${d.backup}. Effective on next start.`;});};
$('v6-load-recovery').onclick=async()=>{try{const d=await api('v6-recovery-read');$('v6-recovery-status').textContent=JSON.stringify(d.settings)+' | Server: '+d.state;}catch(e){$('v6-recovery-status').textContent=e.message;}};
$('v6-save-recovery').onclick=()=>{if(selection()!=='neoforge')return message('Select NeoForge first.',true);const delay=$('v6-delay').value,burst=$('v6-burst').value,interval=$('v6-interval').value;if(!confirm(`Set NeoForge restart-on-failure delay ${delay}s, max ${burst} starts per ${interval}s? Server must be stopped. This modifies systemd policy, but does not start Minecraft.`))return;action('Save NeoForge crash recovery',async()=>{const d=await api('v6-recovery-save',delay,burst,interval);$('v6-recovery-status').textContent='Saved: '+d.file+' | Previous override backup: '+(d.previous_override_backup||'No previous v6 override');});};

// v7: charts use SVG DOM nodes, with safe textContent and no third-party dependencies.
function v7Chart(parent,title,rows,key,unit){
 const wrap=document.createElement('div');wrap.className='sub-panel';
 const heading=document.createElement('h3');heading.textContent=title;wrap.append(heading);
 const valid=rows.filter(r=>Number.isFinite(r[key]));
 if(!valid.length){const p=document.createElement('p');p.textContent='No measurements in this period.';wrap.append(p);parent.append(wrap);return;}
 const ns='http://www.w3.org/2000/svg',w=780,h=180,pad=25;
 const svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox',`0 0 ${w} ${h}`);svg.setAttribute('role','img');svg.setAttribute('aria-label',title);svg.style.width='100%';svg.style.maxHeight='220px';
 const start=rows[0].ts,end=rows[rows.length-1].ts||start+1;
 const ymax=Math.max(1,...valid.map(r=>r[key]))*1.15;
 const x=r=>pad+(r.ts-start)/Math.max(1,end-start)*(w-2*pad);
 const y=r=>h-pad-r[key]/ymax*(h-2*pad);
 for(let n=0;n<=4;n++){const line=document.createElementNS(ns,'line');line.setAttribute('x1',pad);line.setAttribute('x2',w-pad);line.setAttribute('y1',pad+n*(h-2*pad)/4);line.setAttribute('y2',pad+n*(h-2*pad)/4);line.setAttribute('stroke','currentColor');line.setAttribute('opacity','0.15');svg.append(line);}
 let segment=[];
 function flush(){if(!segment.length)return;const path=document.createElementNS(ns,'polyline');path.setAttribute('points',segment.join(' '));path.setAttribute('fill','none');path.setAttribute('stroke','#4e9bde');path.setAttribute('stroke-width','2.5');path.setAttribute('stroke-linejoin','round');svg.append(path);segment=[];}
 for(const r of rows){if(Number.isFinite(r[key]))segment.push(`${x(r).toFixed(1)},${y(r).toFixed(1)}`);else flush();}flush();
 wrap.append(svg);
 const stats=document.createElement('p');stats.className='hint';const avg=valid.reduce((a,r)=>a+r[key],0)/valid.length;
 stats.textContent=`Latest: ${valid[valid.length-1][key].toFixed(2)} ${unit} • Average: ${avg.toFixed(2)} ${unit} • Peak: ${(ymax/1.15).toFixed(2)} ${unit} • ${valid.length} measured points`;
 wrap.append(stats);parent.append(wrap);
}
let v7Loading=false;
async function loadV7Metrics(){
 if(v7Loading||!selection())return;v7Loading=true;
 const id=selection(),status=$('v7-metrics-status'),charts=$('v7-metrics-graphs');status.textContent='Loading performance history...';
 try{const d=await api('v7-metrics',id,$('v7-window').value);if(id!==selection())return;
 charts.replaceChildren();status.textContent=d.samples.length?`${d.samples.length} historical samples displayed • collected every minute • retained for 7 days`:(d.message||'No history yet');
 v7Chart(charts,'Memory usage',d.samples,'memory_gib','GiB');v7Chart(charts,'CPU usage',d.samples,'cpu_percent','%');
 }catch(e){status.textContent='History unavailable: '+e.message;}finally{v7Loading=false;}
}
$('v7-refresh').onclick=loadV7Metrics;
$('v7-window').onchange=loadV7Metrics;
document.querySelectorAll('[data-tab="control-center"]').forEach(b=>b.addEventListener('click',loadV7Metrics));

// Player activity: read-only, scoped to selected service, no RCON traffic.
let activityEvents=[];
let activityPaused=false;
let activityBusy=false;
let activityServer='';
function activityRender(){
  const box=$('player-activity');
  const category=$('activity-filter').value;
  const query=$('activity-search').value.toLocaleLowerCase();
  const shown=activityEvents.filter(e=>(category==='all'||e.type===category) && e.text.toLocaleLowerCase().includes(query));
  const nodes=shown.map(e=>{
    const row=document.createElement('div');row.className='activity-event activity-'+e.type;
    const tag=document.createElement('span');tag.className='activity-type';tag.textContent=e.type;
    const msg=document.createElement('span');msg.textContent=e.text;
    row.append(tag,msg);return row;
  });
  box.replaceChildren(...nodes);
  if(!nodes.length)box.textContent='No matching player activity in the available logs.';
  $('activity-count').textContent=shown.length+' events';
  if($('activity-autoscroll').checked)box.scrollTop=box.scrollHeight;
}
async function loadPlayerActivity(){
  const id=selection();
  if(!id||activityPaused||activityBusy||busy)return;
  activityBusy=true;
  try{
    const d=await api('player-activity',id);
    if(selection()!==id)return;
    activityServer=id;activityEvents=d.events||[];
    activityRender();
    $('activity-status').textContent=d.scope+' '+d.note;
  }catch(e){$('activity-status').textContent='Player activity unavailable: '+String(e.message||e);}
  finally{activityBusy=false;}
}
$('activity-filter').addEventListener('change',activityRender);
$('activity-search').addEventListener('input',activityRender);
$('activity-autoscroll').addEventListener('change',activityRender);
$('activity-refresh').addEventListener('click',()=>{activityPaused=false;$('activity-pause').textContent='Pause';loadPlayerActivity();});
$('activity-pause').addEventListener('click',()=>{activityPaused=!activityPaused;$('activity-pause').textContent=activityPaused?'Resume':'Pause';if(!activityPaused)loadPlayerActivity();});
$('activity-export').addEventListener('click',()=>{
  const category=$('activity-filter').value,query=$('activity-search').value.toLocaleLowerCase();
  const rows=activityEvents.filter(e=>(category==='all'||e.type===category)&&e.text.toLocaleLowerCase().includes(query));
  const csv=['type,message',...rows.map(e=>[e.type,e.text].map(x=>'"'+String(x).replaceAll('"','""')+'"').join(','))].join('\r\n');
  const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));
  const a=document.createElement('a');a.href=url;a.download='minecraft-activity-'+activityServer+'.csv';a.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
});

// Advanced Control Center: bounded analytics, using existing player-activity journal API.
async function advancedRefresh() {
  const id=selection(); if(!id)return;
  const status=$('advanced-status'); status.textContent='Loading player activity…';
  try {
    const data=await api('player-activity',id);
    if(id!==selection())return;
    const events=Array.isArray(data.events)?data.events:[];
    const kinds=['join','leave','chat','announcement','command','moderation'];
    const counts=Object.fromEntries(kinds.map(k=>[k,0]));
    const hourly=new Map();
    for(const e of events){
      if(Object.hasOwn(counts,e.type))counts[e.type]++;
      const stamp=String(e.text||'').match(/(?:^|\s)(\d{2}:\d{2}):\d{2}(?:[+-]\d{2}:?\d{2})?/);
      if(stamp){const hour=stamp[1].slice(0,2)+':00';hourly.set(hour,(hourly.get(hour)||0)+1);}
    }
    const cards=$('advanced-summary');cards.replaceChildren();
    for(const [kind,count] of Object.entries(counts)){
      const div=document.createElement('div'); div.className='sub-panel';
      const title=document.createElement('strong');title.textContent=kind[0].toUpperCase()+kind.slice(1);
      const number=document.createElement('div');number.textContent=String(count);number.style.fontSize='1.5rem';
      div.append(title,number);cards.append(div);
    }
    const times=$('advanced-hourly');times.replaceChildren();
    if(hourly.size){
      const heading=document.createElement('strong');heading.textContent='Events by hour (journal timestamp)';times.append(heading);
      for(const [hour,n] of [...hourly].sort((a,b)=>a[0].localeCompare(b[0]))){
        const line=document.createElement('div');line.textContent=hour+' — '+n+' event'+(n===1?'':'s');times.append(line);
      }
    }
    status.textContent=events.length+' recognized events · '+String(data.scope||'bounded journal history')+'.';
  }catch(e){status.textContent='Activity summary unavailable: '+String(e.message||e);}
}
$('advanced-refresh').addEventListener('click',advancedRefresh);
document.querySelectorAll('[data-tab="advanced"]').forEach(b=>b.addEventListener('click',advancedRefresh));
$('advanced-announce').addEventListener('click',()=>{
 const server=servers.find(s=>s.id===selection());
 const msg=$('advanced-announcement').value.trim();
 if(!server || server.state!=='active' || !server.rcon){$('advanced-announce-status').textContent='Selected server must be running with RCON configured.';return;}
 if(!msg || msg.length>140 || /[\r\n\x00-\x1f\x7f]/.test(msg)){$('advanced-announce-status').textContent='Enter a valid 1–140 character message.';return;}
 if(!confirm('Broadcast to everyone on '+server.label+'?\n\n'+msg))return;
 action('Announcement',async()=>{
   const response=await api('command',server.id,consoleBroadcastCommand(msg, $('periodic-color')?.value||'white', $('periodic-bold')?.checked||false));
   $('advanced-announce-status').textContent='Sent [Console]: '+msg+' · '+String(response||'Delivered');
   $('advanced-announcement').value='';
 });
});

// Persistent per-server periodic announcements. Backend validates all inputs.
async function periodicLoad(){
  const id=selection();if(!id)return;
  try {
    const c=await api('schedule-read',id);
    $('periodic-enabled').checked=!!c.enabled;
    $('periodic-minutes').value=c.interval_minutes||60;
    $('periodic-messages').value=(c.messages||[]).join('\n');
    $('periodic-online-only').checked=!!c.only_with_players;
    $('periodic-color').value=c.color||'white';$('periodic-bold').checked=!!c.bold;
    $('periodic-quiet-enabled').checked=!!c.quiet_hours?.enabled;
    $('periodic-quiet-start').value=c.quiet_hours?.start||'23:00';
    $('periodic-quiet-end').value=c.quiet_hours?.end||'08:00';
    $('periodic-preview').textContent='Next message ('+((c.next_index||0)+1)+'/'+((c.messages||[]).length||0)+'): '+((c.messages||[])[c.next_index||0]||'No messages configured');
    $('periodic-status').textContent=(c.enabled?'Enabled':'Disabled')+' · '+(c.next_due?('Next check after '+new Date(c.next_due*1000).toLocaleString()):'No scheduled send')+(c.last_sent?' · Last sent '+new Date(c.last_sent*1000).toLocaleString():'');
  }catch(e){$('periodic-status').textContent='Unavailable: '+String(e.message||e);}
}
$('periodic-load').addEventListener('click',periodicLoad);
$('periodic-save').addEventListener('click',async()=>{
  const id=selection();if(!id)return;
  const enabled=$('periodic-enabled').checked;
  const minutes=Number($('periodic-minutes').value);
  const only_with_players=$('periodic-online-only').checked;
  const color=$('periodic-color').value;const bold=$('periodic-bold').checked;
  const quiet_hours={enabled:$('periodic-quiet-enabled').checked,start:$('periodic-quiet-start').value,end:$('periodic-quiet-end').value};
  const messages=$('periodic-messages').value.split(/\r?\n/).map(v=>v.trim()).filter(Boolean);
  if(!Number.isInteger(minutes)||minutes<5||minutes>1440||messages.length<1||messages.length>8||messages.some(m=>m.length>140||/[\x00-\x1f\x7f]/.test(m)||m.startsWith('/'))){$('periodic-status').textContent='Use 5–1440 minutes and 1–8 printable messages of 1–140 characters (not starting with /).';return;}
  if(!confirm('Save '+(enabled?'ENABLED':'disabled')+' announcements for '+id+' every '+minutes+' minutes?'))return;
  await action('Save announcement schedule',async()=>{
    const payload=JSON.stringify({enabled,interval_minutes:minutes,messages,only_with_players,quiet_hours,color,bold});
    const raw=await cockpit.spawn(['/usr/local/libexec/cockpit-minecraft-helper','schedule-save',id],{superuser:'require',err:'message',input:payload});
    const response=JSON.parse(raw);if(!response.ok)throw Error(response.error||'Save failed');
    await periodicLoad();
  });
});
$('periodic-test').addEventListener('click',()=>{
 const id=selection();if(!id||!confirm('Send the next scheduled message to '+id+' immediately? This advances message rotation but does not change the next scheduled time.'))return;
 action('Send scheduled announcement',async()=>{$('periodic-status').textContent=String(await api('schedule-test',id));await periodicLoad();});
});
$('periodic-history-btn').addEventListener('click',async()=>{
 try{$('periodic-history').textContent=(await api('schedule-history',selection())).join('\n')||'No sends recorded.';}
 catch(e){$('periodic-history').textContent=String(e.message||e);}
});
document.querySelectorAll('[data-tab="advanced"]').forEach(b=>b.addEventListener('click',periodicLoad));
$('server').addEventListener('change',periodicLoad);

// QOL v3: Branding, announcement presets and readable status.
const announcementPresets={welcome:'Welcome! Be respectful, avoid griefing, and have fun.',backup:'Remember: back up valuable builds before major changes.',discord:'Join our community for updates and server announcements.',lag:'Experiencing lag? Reduce excessive entities and report issues to an admin.'};
$('announcement-preset-add').addEventListener('click',()=>{
 const value=announcementPresets[$('announcement-preset').value];if(!value)return;
 const input=$('periodic-messages');const current=input.value.split(/\r?\n/).map(x=>x.trim()).filter(Boolean);
 if(current.length>=8){$('periodic-status').textContent='Eight messages maximum; remove one before adding.';return;}
 if(!current.includes(value))input.value=[...current,value].join('\n');
 $('periodic-status').textContent='Preset added locally. Save schedule to apply.';
});
// BRANDING_V7: Independent server selector and safe, direct server-icon upload.
function brandingServerId(){return $('brand-server').value;}
function brandingServer(){return servers.find(s=>s.id===brandingServerId());}
function syncBrandingTargets(){
 const picker=$('brand-server'), previous=picker.value;
 picker.replaceChildren();
 for(const s of servers){const opt=new Option(`${s.label} — ${s.id} (${s.state}, port ${s.port})`,s.id);picker.add(opt);}
 if(servers.some(s=>s.id===previous))picker.value=previous;
 else if(servers.some(s=>s.id===selection()))picker.value=selection();
 updateBrandDestination();
}
function updateBrandDestination(){
 const s=brandingServer();
 $('brand-destination').textContent=s?`Target: ${s.id} | ${s.state} | ${s.path}/server.properties | ${s.path}/server-icon.png`:'No branding target selected';
 $('brand-icon-upload').disabled=!s||s.state!=='inactive';
 $('brand-icon-status').textContent=!s?'Select a server.':s.state==='inactive'?'Icon uploads available. Changes appear after starting Minecraft.':'Stop this server to upload or replace its icon.';
}
async function brandSpawn(command,operation,id,payload,binary=false){
 const proc=cockpit.spawn([command,operation,id],{superuser:'require',err:'message',binary});
 let timer;
 try{
   const timeout=new Promise((_,reject)=>{timer=setTimeout(()=>{try{proc.close('terminated')}catch{}reject(new Error('Operation timed out after 20 seconds'))},20000)});
   if(payload!==undefined)proc.input(payload);
   let raw=await Promise.race([proc,timeout]);
   if(binary)raw=new TextDecoder().decode(new Uint8Array(raw));
   const result=JSON.parse(raw);
   if(!result.ok)throw Error(result.error||'Backend request failed');
   return result.data;
 }finally{clearTimeout(timer)}
}
let brandingLoadToken=0;
async function loadBranding(){
 const id=brandingServerId();if(!id)return;
 const token=++brandingLoadToken;
 $('brand-status').textContent='Loading branding for '+id+'...';
 try{
  const [branding,settings,icon]=await Promise.all([
   brandSpawn('/usr/local/libexec/cockpit-minecraft-branding','read',id),
   api('settings',id),
   api('branding-icon-status',id)
  ]);
  if(token!==brandingLoadToken||id!==brandingServerId())return;
  $('brand-label').value=branding.label||'';
  $('brand-motd').value=settings.motd||'';
  $('brand-status').textContent=`Loaded ${id}. Icon: ${icon.exists?`${icon.bytes} bytes at ${icon.path}`:'not installed'}; MOTD/icon need restart.`;
 }catch(e){if(token===brandingLoadToken)$('brand-status').textContent='Branding load failed: '+String(e.message||e)}
}
$('brand-server').addEventListener('change',()=>{++brandingLoadToken;updateBrandDestination();loadBranding()});
$('brand-load').addEventListener('click',loadBranding);
$('brand-save').addEventListener('click',async()=>{
 const id=brandingServerId(),label=$('brand-label').value.trim(),motd=$('brand-motd').value.trim();
 const status=$('brand-status'),button=$('brand-save');
 if(!id)return;
 if(label.length>56||/[\x00-\x1f\x7f]/.test(label)||motd.length>120||/[\r\n]/.test(motd))return void(status.textContent='Invalid name or MOTD');
 if(!confirm(`Save branding for ${id} at ${brandingServer()?.path}? Minecraft will NOT restart.`))return;
 button.disabled=true;let step='friendly name';
 try{
  status.textContent='Saving name to '+id+'...';
  await brandSpawn('/usr/local/libexec/cockpit-minecraft-branding','save',id,JSON.stringify({label}));
  step='MOTD';status.textContent='Name saved. Saving MOTD to '+id+'...';
  await brandSpawn('/usr/local/libexec/cockpit-minecraft-helper','settings-save',id,JSON.stringify({motd}));
  status.textContent=`Saved branding for ${id}. MOTD requires restart. You can refresh the Overview list separately.`;
 }catch(e){status.textContent=`Failed at ${step} for ${id}: ${String(e.message||e)}`}
 finally{button.disabled=false}
});
let brandPreviewURL=null;
$('brand-icon-file').addEventListener('change',async()=>{
 const file=$('brand-icon-file').files[0],img=$('brand-icon-preview');
 if(brandPreviewURL){URL.revokeObjectURL(brandPreviewURL);brandPreviewURL=null}
 img.style.display='none';
 if(!file)return;
 if(file.type!=='image/png'||file.size>2*1024*1024||file.size===0){$('brand-icon-status').textContent='Choose a PNG under 2 MB.';return}
 try{
  brandPreviewURL=URL.createObjectURL(file); const temp=new Image();temp.src=brandPreviewURL;await temp.decode();
  if(temp.naturalWidth!==64||temp.naturalHeight!==64)throw Error('Icon must be exactly 64 × 64 pixels');
  img.src=brandPreviewURL;img.style.display='block';$('brand-icon-status').textContent=`Ready: ${file.name} (${file.size} bytes) for ${brandingServerId()}.`;
 }catch(e){img.style.display='none';$('brand-icon-status').textContent='Invalid icon: '+String(e.message||e)}
});
$('brand-icon-upload').addEventListener('click',async()=>{
 const id=brandingServerId(),s=brandingServer(),file=$('brand-icon-file').files[0],button=$('brand-icon-upload'),status=$('brand-icon-status');
 if(!s||s.state!=='inactive')return void(status.textContent='Stop the selected server before uploading its icon.');
 if(!file||file.type!=='image/png'||file.size<24||file.size>2*1024*1024)return void(status.textContent='Choose a 64×64 PNG under 2MB first.');
 if(!confirm(`Upload icon to ${id}?\n${s.path}/server-icon.png\nExisting icon will be backed up. Minecraft will not restart.`))return;
 button.disabled=true;status.textContent='Uploading icon to '+id+'...';
 try{
  const bytes=new Uint8Array(await file.arrayBuffer());
  const result=await brandSpawn('/usr/local/libexec/cockpit-minecraft-helper','branding-icon-upload',id,bytes,true);
  status.textContent=`Saved ${result.path} (${result.bytes} bytes). Restart ${id} to activate.`;
 }catch(e){status.textContent='Icon upload failed: '+String(e.message||e)}
 finally{updateBrandDestination()}
});
document.querySelectorAll('[data-tab="advanced"]').forEach(b=>b.addEventListener('click',()=>{syncBrandingTargets();loadBranding()}));
async function updateBrandSelector(){
 const id=selection();if(!id)return;try{const raw=await cockpit.spawn(['/usr/local/libexec/cockpit-minecraft-branding','read',id],{superuser:'require',err:'message'});const r=JSON.parse(raw);if(r.ok&&r.data.label){const opt=[...$('server').options].find(o=>o.value===id);if(opt)opt.textContent=r.data.label+' ('+(servers.find(s=>s.id===id)?.state||'unknown')+')';}}catch{}
}
$('server').addEventListener('change',updateBrandSelector);
document.querySelectorAll('[data-tab="advanced"]').forEach(b=>b.addEventListener('click',updateBrandSelector));

// v4 Player Records & Storage, isolated from existing manager APIs.
async function v4Call(...args){
 const raw=await cockpit.spawn(['/usr/local/libexec/cockpit-minecraft-records',...args],{superuser:'require',err:'message'});
 const result=JSON.parse(raw); if(!result.ok)throw new Error(result.error||'Records backend failed');return result.data;
}
function v4List(target, entries){const box=$(target);box.replaceChildren();for(const [key,val] of entries){const item=document.createElement('div');item.className='notice';const b=document.createElement('strong');b.textContent=key+': ';item.append(b,document.createTextNode(String(val)));box.append(item);}}
async function v4Refresh(){const id=selection();if(!id)return;try{
 $('v4-storage').textContent='Reading server files…';$('v4-backups').textContent='Reading Restic snapshots…';$('v4-players').textContent='Reading retained player logs…';
 const d=await v4Call('report',id);
 v4List('v4-storage',[['Directory',d.storage.path],['Total server files',d.storage.total_human],['World directory',d.storage.world_path],['World size',d.storage.world_human],['Scanned files',d.storage.files],['Scan complete',d.storage.complete?'Yes':'No — limit reached']]);
 v4List('v4-backups',[['Repository',d.backups.repository],['Repository disk usage',d.backups.repo_human],['All snapshots in repository',d.backups.total],['Selected-server snapshots',d.backups.selected],['Other / unmatched snapshots',d.backups.other],['Oldest matching backup',d.backups.oldest||'None'],['Newest matching backup',d.backups.newest||'None'],['Notes',d.backups.warning||'Read-only; repository data is deduplicated']]);
 const list=$('v4-backups'); const pre=document.createElement('pre');pre.className='log';pre.textContent=d.backups.snapshots.map(x=>`${x.time||'?'}  ${x.id.slice(0,12)}  ${x.match?'THIS SERVER':'other'}  ${x.paths.join(', ')}`).join('\n')||'No snapshots found';list.append(pre);
 v4List('v4-players',[['Unique players observed',d.players.length],['Stored events',d.event_count],['Journal scan',d.scan_note]]);
 const players=document.createElement('pre');players.className='log';players.textContent=d.players.map(p=>`${p.name}: ${p.joins} joins, ${p.leaves} leaves, ${p.deaths} deaths, ${p.chats} chats; last ${p.last_seen||'unknown'}`).join('\n')||'No recorded players';$('v4-players').append(players);
 $('v4-events').textContent=d.events.map(e=>`${e.time} [${e.type}] ${e.player||''} ${e.message}`).join('\n')||'No matching logs recorded yet.';
 }catch(e){for(const id of ['v4-storage','v4-backups','v4-players'])$(id).textContent='Unavailable: '+String(e);}}
$('v4-refresh').addEventListener('click',v4Refresh);
document.querySelectorAll('[data-tab="player-records"]').forEach(b=>b.addEventListener('click',v4Refresh));
$('v4-notes-load').addEventListener('click',async()=>{try{const d=await v4Call('note-read',selection(),$('v4-player').value.trim());$('v4-note').value=d.note||'';$('v4-note-status').textContent='Loaded';}catch(e){$('v4-note-status').textContent=String(e)}});
$('v4-notes-save').addEventListener('click',async()=>{const name=$('v4-player').value.trim(),note=$('v4-note').value;if(!confirm('Save private moderation note for '+name+' on '+selection()+'?'))return;try{const raw=await cockpit.spawn(['/usr/local/libexec/cockpit-minecraft-records','note-save',selection(),name],{superuser:'require',err:'message',input:note});const d=JSON.parse(raw);if(!d.ok)throw Error(d.error);$('v4-note-status').textContent='Saved';}catch(e){$('v4-note-status').textContent=String(e)}});

// Default-port selection: a separate, narrowly-scoped Cockpit helper.
async function portCall(...args){
 const out=await cockpit.spawn(['/usr/local/libexec/cockpit-minecraft-default-port',...args],{superuser:'require',err:'message'});
 let d;try{d=JSON.parse(out);}catch{throw Error('Unexpected port routing response');}
 if(!d.ok)throw Error(d.error||'Routing operation failed');return d.data;
}
function portDisplay(d){
 const ss=d.servers||{};const id=d.selected;const t=id&&ss[id];
 $('default-port-status').textContent=[
  'Mode: '+(d.mode||'unconfigured'),
  'Selected target: '+(t?t.label+' (port '+t.port+')':'None'),
  'Forwarder service: '+(d.proxy_active?'RUNNING':'stopped'),
  'Listener on 25565: '+(d.port_25565_listener?'present':'none'),
  'Connect: your configured host or private network address (when routing is active)',
  d.warning||''
 ].join('\n');
}
$('default-port-refresh').addEventListener('click',async()=>{try{portDisplay(await portCall('status'));}catch(e){$('default-port-status').textContent=String(e)}});
$('default-port-select').addEventListener('click',async()=>{
 const id=selection();const s=servers.find(x=>x.id===id);if(!s)return;
 if(!confirm('Route connections on port 25565 to '+s.label+'?\n\nExisting port-25565 listeners must be stopped. Active player connections through the proxy may disconnect. No Minecraft service will be stopped or restarted.'))return;
 try{portDisplay(await portCall('select',id));message('Default connection target updated.');}
 catch(e){$('default-port-status').textContent='Cannot change default: '+String(e);message(String(e),true)}
});


// Branding Studio v8: scoped to the v7 independent branding target.
let v8RequestToken=0;
const v8El=(id)=>document.getElementById(id);
const v8Colors={'0':'#000000','1':'#0000aa','2':'#00aa00','3':'#00aaaa','4':'#aa0000','5':'#aa00aa','6':'#ffaa00','7':'#aaaaaa','8':'#555555','9':'#5555ff','a':'#55ff55','b':'#55ffff','c':'#ff5555','d':'#ff55ff','e':'#ffff55','f':'#ffffff'};
function v8Draw(){
 const target=v8El('v8-preview');target.replaceChildren();let color='#ffffff',bold=false,italic=false;
 const str=v8El('v8-motd').value;
 for(let i=0;i<str.length;i++){
   if(str[i]==='§'&&i+1<str.length){const code=str[++i].toLowerCase();if(code in v8Colors){color=v8Colors[code];bold=false;italic=false}else if(code==='l')bold=true;else if(code==='o')italic=true;else if(code==='r'){color='#ffffff';bold=false;italic=false}continue;}
   const span=document.createElement('span');span.textContent=str[i];span.style.color=color;span.style.fontWeight=bold?'bold':'normal';span.style.fontStyle=italic?'italic':'normal';target.append(span);
 }
}
async function v8Call(op,id,payload){
 const proc=cockpit.spawn(['/usr/local/libexec/cockpit-minecraft-branding-v8',op,id],{superuser:'require',err:'message'});
 let timer;
 try{
  const timeout=new Promise((_,rej)=>{timer=setTimeout(()=>{try{proc.close('terminated')}catch{}rej(Error('Branding v8 timed out'))},12000)});
  if(payload!==undefined)proc.input(JSON.stringify(payload));
  const raw=await Promise.race([proc,timeout]);const obj=JSON.parse(raw);
  if(!obj.ok)throw Error(obj.error||'Branding backend error');return obj.data;
 }finally{clearTimeout(timer)}
}
async function v8Refresh(){const id=brandingServerId();if(!id)return;const token=++v8RequestToken;v8El('v8-state').textContent='Reading '+id+'…';
 try{const [state,ping]=await Promise.all([v8Call('inspect',id),v8Call('ping',id)]);
 if(token!==v8RequestToken||id!==brandingServerId())return;
 v8El('v8-motd').value=state.motd;v8Draw();
 v8El('v8-client-name').textContent=(state.label||'Minecraft Server')+' (preview; client chooses saved name)';
 v8El('v8-state').textContent=`${id} · ${state.path} · ${state.icon?'Icon present':'No icon'} · MOTD/icon require restart`;
 v8El('v8-ping').textContent=ping.online?`Live server: ${ping.version?.name||'unknown'} · ${ping.players?.online??'?'} players · advertised MOTD may differ until restart`:`Server not reachable on localhost: ${ping.reason||'stopped'}`;
 if(state.icon_b64)v8El('v8-icon').src='data:image/png;base64,'+state.icon_b64;
 else v8El('v8-icon').removeAttribute('src');
 }catch(e){if(token===v8RequestToken)v8El('v8-state').textContent=String(e.message||e)}
}
v8El('v8-motd').addEventListener('input',v8Draw);
v8El('v8-insert').onclick=()=>{const el=v8El('v8-motd'),n=el.selectionStart;el.setRangeText(v8El('v8-color').value,n,el.selectionEnd,'end');v8Draw();el.focus()};
v8El('v8-refresh').onclick=v8Refresh;
v8El('brand-server').addEventListener('change',()=>{++v8RequestToken;v8El('v8-state').textContent='Choose Refresh for new server';v8El('v8-history').replaceChildren()});
v8El('v8-save-motd').onclick=async()=>{const id=brandingServerId(),motd=v8El('v8-motd').value;if(!id||!confirm(`Save colored MOTD for ${id}? Minecraft will not restart.`))return;
 try{const result=await v8Call('motd-save',id,{motd});v8El('v8-feedback').textContent='Saved '+result.path+'. Restart required; no server restarted.'}catch(e){v8El('v8-feedback').textContent='MOTD error: '+e.message}};
v8El('v8-icon-save').onclick=async()=>{const id=brandingServerId(),file=v8El('v8-image').files[0],s=brandingServer();if(!id||!file)return;
 if(file.size>2_500_000)return void(v8El('v8-feedback').textContent='Image must be under 2.5 MB');
 if(s?.state!=='inactive')return void(v8El('v8-feedback').textContent='Stop the selected server before replacing its icon.');
 if(!confirm(`Convert and save server icon at ${s.path}/server-icon.png for ${id}?`))return;
 try{const arr=new Uint8Array(await file.arrayBuffer());let bin='';for(let i=0;i<arr.length;i+=8192)bin+=String.fromCharCode(...arr.subarray(i,i+8192));const image=btoa(bin);
 const result=await v8Call('icon-save',id,{image,mode:v8El('v8-resize').value});v8El('v8-feedback').textContent=`Icon saved: ${result.path}; restart required.`;await v8Refresh();}catch(e){v8El('v8-feedback').textContent='Icon error: '+e.message}};
v8El('v8-preset-save').onclick=async()=>{const id=brandingServerId(),name=v8El('v8-preset-name').value.trim();if(!id||!name)return;try{await v8Call('presets-save',id,{name});v8El('v8-feedback').textContent='Preset saved: '+name;await v8LoadPresets()}catch(e){v8El('v8-feedback').textContent=e.message}};
async function v8LoadPresets(){const id=brandingServerId();if(!id)return;try{const p=await v8Call('presets-list',id);const sel=v8El('v8-presets');sel.replaceChildren();for(const key of Object.keys(p)){const o=document.createElement('option');o.value=key;o.textContent=key;sel.add(o)}}catch(e){v8El('v8-feedback').textContent=e.message}}
v8El('v8-preset-apply').onclick=async()=>{const id=brandingServerId(),name=v8El('v8-presets').value;if(!id||!name||!confirm(`Apply preset ${name} to ${id}? No Minecraft restart.`))return;try{await v8Call('preset-apply',id,{name});v8El('v8-feedback').textContent='Preset applied; restart required.';await v8Refresh()}catch(e){v8El('v8-feedback').textContent=e.message}};
async function v8History(){const id=brandingServerId();if(!id)return;try{const events=await v8Call('history',id),box=v8El('v8-history');box.replaceChildren();for(const event of events){const row=document.createElement('div');row.className='notice';row.textContent=`${event.date} ${event.kind}: ${event.description} `;
 if(['motd','icon'].includes(event.kind)){const b=document.createElement('button');b.className='btn secondary';b.textContent='Restore previous';b.addEventListener('click',async()=>{if(!confirm(`Restore prior ${event.kind} state for ${id}? No automatic restart.`))return;try{await v8Call('restore',id,{history_id:event.id});v8El('v8-feedback').textContent='Restored previous branding; restart required.';await v8History();await v8Refresh()}catch(e){v8El('v8-feedback').textContent=e.message}});row.append(b)}box.append(row)}if(!events.length)box.textContent='No history recorded by v8 yet.'}catch(e){v8El('v8-feedback').textContent=e.message}}
v8El('v8-history-refresh').onclick=v8History;v8El('v8-gallery-refresh').onclick=async()=>{await v8History();v8El('v8-gallery').textContent='Icon versions are stored in history; use Restore previous on icon entries.'};
document.querySelectorAll('[data-tab="advanced"]').forEach(b=>b.addEventListener('click',()=>{setTimeout(()=>{v8Refresh();v8LoadPresets()},0)}));

async function v8Sources(){const box=v8El('v8-copy-source'),previous=box.value;box.replaceChildren();for(const s of servers){const o=document.createElement('option');o.value=s.id;o.textContent=s.label+' ('+s.id+')';box.add(o)}if(servers.some(s=>s.id===previous))box.value=previous}
v8El('v8-copy').onclick=async()=>{const source=v8El('v8-copy-source').value,dest=brandingServerId(),name=v8El('v8-copy-preset').value;if(!source||!dest||!name)return void(v8El('v8-feedback').textContent='Select a preset and source server.');if(source===dest)return void(v8El('v8-feedback').textContent='Choose two different servers.');if(!confirm(`Copy preset named ${name} from ${source} to ${dest}, without applying it?`))return;try{await v8Call('preset-copy',dest,{source,name});v8El('v8-feedback').textContent='Copied preset to '+dest+'; nothing applied.';await v8LoadPresets()}catch(e){v8El('v8-feedback').textContent=e.message}};
document.querySelectorAll('[data-tab="advanced"]').forEach(b=>b.addEventListener('click',v8Sources));

async function v8LoadSourcePresets(){const source=v8El('v8-copy-source').value;if(!source)return;try{const p=await v8Call('presets-list',source),box=v8El('v8-copy-preset');box.replaceChildren();for(const key of Object.keys(p)){const o=document.createElement('option');o.value=key;o.textContent=key;box.add(o)}}catch(e){v8El('v8-feedback').textContent=e.message}}
v8El('v8-copy-source').addEventListener('change',v8LoadSourcePresets);
document.querySelectorAll('[data-tab="advanced"]').forEach(b=>b.addEventListener('click',()=>setTimeout(v8LoadSourcePresets,0)));

// v9 human-readable save feedback v9.1 — independent, per-server controls.
const v9e = id => document.getElementById(id);
function v9err(e){
  const s = [e && e.message,e && e.problem,e && e.exit_status !== undefined ? 'Exit status '+e.exit_status : '',String(e||'')].filter(Boolean).join(' | ');
  return s && s!=='[object Object]' ? s : 'The Cockpit helper did not return an error description; check privileges or Cockpit browser console.';
}
async function v9call(op,id,payload){
  const proc=cockpit.spawn(['/usr/local/libexec/cockpit-minecraft-scheduler-v9',op,id],{superuser:'require',err:'message'});
  if(payload!==undefined)proc.input(JSON.stringify(payload),false);
  let output;
  try{output=await proc;}catch(e){throw Error(op+' for '+id+' could not complete: '+v9err(e));}
  let response;try{response=JSON.parse(output);}catch(_){throw Error('Unexpected helper output (not JSON): '+String(output).slice(0,250));}
  if(!response.ok)throw Error(response.error||'Backend rejected '+op);
  return response.data;
}
function v9server(){return v9e('v9-server').value;}
function v9populate(){const el=v9e('v9-server'),previous=el.value;el.replaceChildren();for(const s of servers){const opt=document.createElement('option');opt.value=s.id;opt.textContent=s.label+' — '+s.id+' ('+s.state+')';el.add(opt)}if(servers.some(s=>s.id===previous))el.value=previous;}
function v9parse(text){
  const raw=String(text||'');if(raw==='Not configured'||!raw.trim())return null;
  const val=key=>{const m=raw.match(new RegExp('^'+key+'=(.*)$','m'));return m?m[1].trim():null};
  const cpu=val('CPUQuota'),mem=val('MemoryMax');
  const xms=raw.match(/(?:^|\s)-Xms(\d+)([GM])/m),xmx=raw.match(/(?:^|\s)-Xmx(\d+)([GM])/m);
  const gib=m=>m?(m[2]==='G'?Number(m[1]):Number(m[1])/1024):0;
  return {cpu:cpu==='infinity'?0:cpu&&cpu.endsWith('%')?Number(cpu.slice(0,-1)):null,
    mem:mem==='infinity'?0:mem&&/^(\d+)G$/.test(mem)?Number(mem.slice(0,-1)):null,
    xms:gib(xms),xmx:gib(xmx),raw};
}
function v9cpu(pct){
  if(pct===0)return 'Unlimited — no CPU quota is imposed by this setting.';
  const cores=pct/100;
  return `${pct}% means up to ${Number.isInteger(cores)?cores:cores.toFixed(2)} logical CPU${cores===1?'':'s'} worth of total processing time. 100% = one logical CPU; 400% = four. This is a cap, not a reservation or CPU affinity.`;
}
function v9statusResource(d){
  const parsed=v9parse(d.resource_override);
  if(!parsed)return 'No persistent CPU or service memory limits have been configured through v9 for this server.';
  const cpu=parsed.cpu===null?'Unknown CPU quota':parsed.cpu===0?'CPU quota: unlimited':`CPU quota: ${parsed.cpu}%`;
  const mem=parsed.mem===null?'Unknown MemoryMax':parsed.mem===0?'MemoryMax: unlimited':`MemoryMax: ${parsed.mem} GiB`;
  return `SAVED SETTINGS — ${d.server}\n${cpu}. ${parsed.cpu!==null?v9cpu(parsed.cpu):''}\n${mem}. This is a cap for the full service (Java heap plus native memory), not its Java heap allocation.\n${parsed.xmx?`Java heap override: Xms ${parsed.xms} GiB, Xmx ${parsed.xmx} GiB.`:'Java heap: unchanged by this v9 resource override.'}\n${d.running?'Service is running. Existing limits may already be effective; stop/start to apply changes to launcher heap.':'Service is stopped. Limits apply on next start.'}`;
}
// v9 live explanations v9.2 — render current proposed values before saving.
function v9Explain(){
  const panel=v9e('v9-explain');if(!panel)return;
  const id=v9server()||'the selected server';
  const raw=n=>v9e(n).value.trim();
  const pct=Number(raw('v9-cpu')),mem=Number(raw('v9-memory'));
  const mn=Number(raw('v9-min')),mx=Number(raw('v9-max'));
  const cp=raw('v9-cpu')===''?'Select a server to load its saved CPU value.':
    !Number.isFinite(pct)||pct<0?'Enter a valid CPU percentage.':v9cpu(pct);
  const mm=raw('v9-memory')===''?'Select a server to load its saved memory limit.':
    !Number.isFinite(mem)||mem<0?'Enter a valid memory limit.':mem===0?
    '0 GiB = no MemoryMax cap from this setting. The server can still be limited by available system RAM.':
    `${mem} GiB is a hard cap for the ENTIRE Minecraft service, including Java heap, mods, and other JVM memory. Hitting it may cause the server to be terminated.`;
  const heap=raw('v9-min')===''||raw('v9-max')===''?'Select a server to load heap settings.':
    mn===0&&mx===0?'Both 0 = leave the current Java heap settings unchanged.':
    mn>0&&mx>=mn?`Xms ${mn} GiB is the initial Java heap; Xmx ${mx} GiB is the maximum Java heap. These are not the total RAM used by Minecraft.`:
    'Enter BOTH JVM Xms and Xmx, with Xms greater than 0 and no greater than Xmx.';
  const restart=v9e('v9-enabled').checked?
    `Automatic restarts requested every ${v9e('v9-hours').value} hours, with a ${v9e('v9-warn').value}-minute advance warning. Changes are not saved until you click Save.`:
    'Automatic restarts are disabled in the form. Changes are not saved until you click Save.';
  const text=[`EXPLAINING THE VALUES FOR ${id} — PREVIEW ONLY`,
    'CPU quota: '+cp,
    'EXAMPLES: 100% = up to one logical CPU worth of compute time; 200% = two; 400% = four. Minecraft can still use more than four different cores over time. A quota LIMITS total CPU time; it does not reserve cores or boost performance.',
    'Service memory (MemoryMax): '+mm,
    'JVM heap: '+heap,
    'NOTE: CPU and MemoryMax policies persist across reboots. The Java heap only changes if launcher-specific configuration is supported and both heap values are provided. This panel currently uses the separate existing NeoForge tool to change NeoForge heap.',
    'Restart schedule: '+restart,
    'Editing these values does NOT change Minecraft. Saving resource settings requires the server to be stopped; no restart is triggered automatically.'];
  panel.textContent=text.join('\n\n');
}
function v9ExplainInit(){
  const anchor=v9e('v9-save-resources');if(!anchor||v9e('v9-explain'))return;
  const panel=document.createElement('div');panel.id='v9-explain';
  panel.style.cssText='white-space:pre-line;line-height:1.5;padding:14px;margin:12px 0;border:1px solid #52657c;border-radius:8px;background:rgba(128,145,165,.10);font-size:13px';
  panel.setAttribute('aria-live','polite');
  anchor.parentNode.insertBefore(panel,anchor);
  for(const id of ['v9-cpu','v9-memory','v9-min','v9-max','v9-hours','v9-warn','v9-enabled']){
    v9e(id).addEventListener('input',v9Explain);
    v9e(id).addEventListener('change',v9Explain);
  }
  v9Explain();
}
function v9fill(d){
  if(d.server!==v9server())return;
  v9e('v9-enabled').checked=!!d.enabled;v9e('v9-hours').value=d.interval_hours;v9e('v9-warn').value=d.warn_minutes;
  v9e('v9-state').textContent=d.service+' — '+(d.running?'RUNNING':'STOPPED');
  v9e('v9-schedule-status').textContent=(d.enabled?'Enabled':'Disabled')+' · '+(d.due?'next due '+new Date(d.due*1000).toLocaleString():'no restart scheduled')+(d.last_error?' · Last failure: '+d.last_error:'');
  const parsed=v9parse(d.resource_override);
  v9e('v9-cpu').value=parsed&&parsed.cpu!==null?parsed.cpu:0;
  v9e('v9-memory').value=parsed&&parsed.mem!==null?parsed.mem:0;
  v9e('v9-min').value=parsed?parsed.xms:0;v9e('v9-max').value=parsed?parsed.xmx:0;
  const el=v9e('v9-resource-status');el.style.whiteSpace='pre-line';el.textContent=v9statusResource(d);
  v9Explain();
}
async function v9load(){
  const id=v9server();if(!id)return;
  v9e('v9-state').textContent='Reading saved settings for '+id+'...';
  v9e('v9-resource-status').textContent='Loading saved CPU and RAM policy for '+id+'…';
  v9e('v9-schedule-status').textContent='Loading restart schedule for '+id+'…';
  for(const field of ['v9-cpu','v9-memory','v9-min','v9-max'])v9e(field).value='';
  v9Explain();
  try{const d=await v9call('status',id);v9fill(d);v9Explain();}catch(e){if(id===v9server()){
    v9e('v9-state').textContent='Unable to load '+id+': '+v9err(e);
    v9e('v9-resource-status').textContent='Cannot verify settings for '+id+'. No settings changed.';
    v9e('v9-schedule-status').textContent='Cannot verify restart schedule for '+id+'.';
  }}
}
function v9set(which,msg,id){if(id===v9server()){const el=v9e(which);el.style.whiteSpace='pre-line';el.textContent=msg;}}
v9e('v9-server').addEventListener('change',v9load);v9e('v9-reload').onclick=v9load;
v9e('v9-save-schedule').onclick=async()=>{
  const id=v9server();if(!id)return;
  const config={enabled:v9e('v9-enabled').checked,interval_hours:Number(v9e('v9-hours').value),warn_minutes:Number(v9e('v9-warn').value)};
  if(!confirm((config.enabled?'ENABLE':'DISABLE')+' scheduled restarts for '+id+' every '+config.interval_hours+' hours?'))return;
  let error=null;try{await v9call('schedule',id,config);}catch(e){error=e;}
  try{const verified=await v9call('status',id);const match=verified.enabled===config.enabled&&Number(verified.interval_hours)===config.interval_hours&&Number(verified.warn_minutes)===config.warn_minutes;
    if(match){v9fill(verified);v9set('v9-schedule-status',`Saved and verified for ${id}.\nAutomatic restarts: ${verified.enabled?'enabled':'disabled'}. Interval: ${verified.interval_hours} hours. Warning: ${verified.warn_minutes} minutes.\n${verified.due?'Next scheduled restart: '+new Date(verified.due*1000).toLocaleString():'No automatic restart is scheduled.'}`,id);}
    else v9set('v9-schedule-status','Save could not be verified for '+id+'. '+(error?v9err(error):'Readback differs from requested values.'),id);
  }catch(e){v9set('v9-schedule-status','Unable to verify restart schedule for '+id+'. '+(error?v9err(error)+'; ':'')+v9err(e),id);}
};
v9e('v9-save-resources').onclick=async()=>{
  const id=v9server();if(!id)return;
  const config={cpu_percent:Number(v9e('v9-cpu').value),memory_max_gib:Number(v9e('v9-memory').value),heap_min_gib:Number(v9e('v9-min').value),heap_max_gib:Number(v9e('v9-max').value)};
  if(!confirm(`Save persistent resource limits for ${id}?\nCPU: ${config.cpu_percent}%\nMemoryMax: ${config.memory_max_gib||'unlimited'} GiB\nJVM heap: ${config.heap_min_gib||'unchanged'} / ${config.heap_max_gib||'unchanged'} GiB\nThe server must be stopped; it will NOT be restarted automatically.`))return;
  let before=null;try{before=await v9call('status',id);}catch(_){/* independent verification still follows */}
  let saveError=null;try{await v9call('resources',id,config);}catch(e){saveError=e;}
  try{
    const after=await v9call('status',id),actual=v9parse(after.resource_override);
    const matched=actual&&actual.cpu===config.cpu_percent&&actual.mem===config.memory_max_gib&&
      (!config.heap_min_gib&&!config.heap_max_gib || actual.xms===config.heap_min_gib&&actual.xmx===config.heap_max_gib);
    if(matched){
      const prior=v9parse(before?.resource_override);
      const oldCpu=prior&&prior.cpu!==null?prior.cpu+'%':'not configured',oldMem=prior&&prior.mem!==null?(prior.mem?prior.mem+' GiB':'unlimited'):'not configured';
      v9fill(after);
      v9set('v9-resource-status',`SAVED AND VERIFIED — ${id}\nCPU quota: ${oldCpu} → ${config.cpu_percent?config.cpu_percent+'%':'unlimited'}\n${v9cpu(config.cpu_percent)}\nService memory limit: ${oldMem} → ${config.memory_max_gib?config.memory_max_gib+' GiB':'unlimited'}\nMemoryMax caps the whole Minecraft service, not just Java heap.\nJVM heap: ${config.heap_max_gib?'Xms '+config.heap_min_gib+' GiB / Xmx '+config.heap_max_gib+' GiB':'unchanged'}\n${after.running?'Review live settings; launcher heap changes require a restart.':'Server remains stopped; changes will apply when you next start it.'}`,id);
    }else{
      v9set('v9-resource-status',`Not verified for ${id}.\n${saveError?'The helper reported: '+v9err(saveError)+'\n':''}Requested CPU ${config.cpu_percent}%, MemoryMax ${config.memory_max_gib} GiB; readback did not match.\n${v9statusResource(after)}`,id);
    }
  }catch(e){v9set('v9-resource-status',`Unable to confirm resource settings for ${id}.\n${saveError?'Save reported: '+v9err(saveError)+'\n':''}Readback reported: ${v9err(e)}\nNo restart was requested.`,id);}
};
v9ExplainInit();
document.querySelectorAll('[data-tab="automation"]').forEach(b=>b.addEventListener('click',()=>{v9populate();v9load()}));

// v9 resource queue v9.3 — server-specific deferred apply, no service restarts.
const v93Backend='/usr/local/libexec/cockpit-minecraft-resource-queue';
async function v93Call(op,id,payload){
 const proc=cockpit.spawn([v93Backend,op,id],{superuser:'require',err:'message'});
 if(payload!==undefined)proc.input(JSON.stringify(payload),false);
 let out;
 try{out=await proc;}catch(e){throw Error(v9err(e));}
 const res=JSON.parse(out);
 if(!res.ok)throw Error(res.error||'Deferred resource request failed');
 return res.data;
}
function v93Config(){return {cpu_percent:Number(v9e('v9-cpu').value),memory_max_gib:Number(v9e('v9-memory').value),heap_min_gib:Number(v9e('v9-min').value),heap_max_gib:Number(v9e('v9-max').value)};}
function v93Summary(c){return `CPU: ${c.cpu_percent?c.cpu_percent+'%':'unlimited'} (${c.cpu_percent?c.cpu_percent/100+' logical CPUs worth of shared processing time':'no quota'}).\nService RAM ceiling: ${c.memory_max_gib?c.memory_max_gib+' GiB':'unlimited'} (this is not JVM heap).\nJava heap: ${c.heap_max_gib?'Xms '+c.heap_min_gib+' GiB, Xmx '+c.heap_max_gib+' GiB':'unchanged'}.`}
async function v93Refresh(id){
 if(!id||id!==v9server())return;
 const view=v9e('v93-pending');view.textContent='Loading queued changes for '+id+'…';
 try{const d=await v93Call('status',id);if(id!==v9server())return;
  const q=d.pending;const last=d.last;
  if(q){view.textContent=(q.state==='failed'?'FAILED — needs attention':'QUEUED — waiting until server stops')+' — '+id+'\n'+v93Summary(q.config)+'\n'+(q.error?'Reason: '+q.error:'No automatic stop or restart will occur. Changes are checked once per minute.');}
  else if(last){view.textContent=(last.state==='applied'?'APPLIED AND VERIFIED':'CANCELLED')+' — '+id+'\n'+v93Summary(last.config);}
  else view.textContent='No pending resource changes for '+id+'.';
 }catch(e){if(id===v9server())view.textContent='Cannot read queued changes for '+id+': '+v9err(e);}
}
(function v93Init(){
 const save=v9e('v9-save-resources');if(!save)return;
 const panel=document.createElement('div');panel.id='v93-panel';panel.style.cssText='border:1px solid #52657c;border-radius:8px;padding:12px;margin:12px 0;white-space:pre-line';
 const title=document.createElement('strong');title.textContent='Apply resource changes when the server stops';
 const help=document.createElement('p');help.textContent='Queue CPU/RAM settings now without disconnecting players. They are applied automatically after the selected service becomes inactive (usually within one minute). This does not stop, start, or restart Minecraft. A failed request stays visible until you correct or cancel it.';
 const queue=document.createElement('button');queue.type='button';queue.textContent='Queue for when server stops';queue.style.marginRight='8px';
 const cancel=document.createElement('button');cancel.type='button';cancel.textContent='Cancel pending change';
 const refresh=document.createElement('button');refresh.type='button';refresh.textContent='Refresh queue status';refresh.style.marginLeft='8px';
 const result=document.createElement('div');result.id='v93-pending';result.style.cssText='white-space:pre-line;margin:12px 0;font-size:13px';
 panel.append(title,help,queue,cancel,refresh,result);save.parentNode.insertBefore(panel,save.nextSibling);
 queue.onclick=async()=>{const id=v9server();if(!id)return;const c=v93Config();
  if(!confirm('Queue resource changes for '+id+'?\n'+v93Summary(c)+'\nNothing is stopped or restarted automatically.'))return;
  result.textContent='Saving pending settings for '+id+'…';
  try{await v93Call('queue',id,c);await v93Refresh(id);}catch(e){if(id===v9server())result.textContent='Unable to queue for '+id+': '+v9err(e);}
 };
 cancel.onclick=async()=>{const id=v9server();if(!id||!confirm('Cancel pending resource settings for '+id+'? This does not undo changes already applied.'))return;
  try{await v93Call('cancel',id);await v93Refresh(id);}catch(e){if(id===v9server())result.textContent='Cancellation failed: '+v9err(e);}
 };
 refresh.onclick=()=>v93Refresh(v9server());
 const oldLoad=v9load;
 v9load=async function(){const id=v9server();if(id)result.textContent='Switching to '+id+'…';await Promise.all([oldLoad(),v93Refresh(id)]);};
 // Show a clear running-server warning before the existing Save handler.
 const oldSave=save.onclick;
 save.onclick=async()=>{const id=v9server();if(!id)return;
  try{const d=await v9call('status',id);if(id!==v9server())return;
   if(d.running){const c=v93Config();
     if(confirm(id+' is RUNNING. The direct save cannot be applied while players are connected.\n\nClick OK to QUEUE the settings for when this server stops. Click Cancel to leave everything unchanged.\n\n'+v93Summary(c))){
       try{await v93Call('queue',id,c);await v93Refresh(id);v9set('v9-resource-status','QUEUED — '+id+' is still running. No changes were applied yet. This will be applied when the server stops.',id);}catch(e){v9set('v9-resource-status','Could not queue for '+id+': '+v9err(e),id);}
     }
     return;
   }
  }catch(e){v9set('v9-resource-status','Unable to check whether '+id+' is running: '+v9err(e),id);return;}
  await oldSave();await v93Refresh(id);
 };
 v9e('v9-server').addEventListener('change',()=>{result.textContent='Switching servers…';});
 document.querySelectorAll('[data-tab="automation"]').forEach(b=>b.addEventListener('click',()=>setTimeout(()=>v93Refresh(v9server()),0)));
})();



// Version Manager v1: isolated UI; all other existing dashboard actions preserved.
function upgradeSelected(){return servers.find(s=>s.id===selection());}
function upgradeInspect(){const s=upgradeSelected();$('upgrade-current').textContent=s?`${s.label} | ${s.unit} | ${s.state} | ${s.path}`:'No server selected';$('upgrade-run').disabled=!s||s.id==='neoforge'||!s.label.startsWith('Vanilla ')||s.state!=='inactive';}
$('upgrade-inspect').onclick=upgradeInspect;
$('upgrade-load').onclick=()=>action('Load official releases',async()=>{const versions=await api('versions');const el=$('upgrade-version');el.replaceChildren();for(const version of versions){const o=document.createElement('option');o.value=version;o.textContent=version;el.add(o);}upgradeInspect();});
$('upgrade-run').onclick=()=>{const s=upgradeSelected(),version=$('upgrade-version').value;if(!s||!version)return message('Select a server and target version.',true);if(s.id==='neoforge'||!s.label.startsWith('Vanilla ')||s.state!=='inactive')return message('Only stopped managed Vanilla servers can be upgraded.',true);if(!confirm(`Upgrade ${s.id} to Vanilla ${version}?\n\nThe previous jar is preserved. Minecraft world data is NOT backed up. The server stays stopped. Please make a world backup before first launch of a new Minecraft version.`))return;action('Upgrade Vanilla server',async()=>{const result=await api('upgrade-vanilla',s.id,version);$('upgrade-result').textContent=JSON.stringify(result,null,2);await refresh();upgradeInspect();});};
