/* Local demo only. No HA connection, tokens, network API calls or live actions. */
(() => {
  const rooms=globalThis.FloorplanRoomConfig.rooms, C=globalThis.FloorplanCore;
  const view=document.querySelector('floorplan-room-view'), states={};
  const set=(id,state,attributes)=>{states[id]={entity_id:id,state,attributes};};
  const name=id=>id.split('.')[1].replaceAll('_',' ').replace(/\b\w/g,c=>c.toUpperCase());
  for(const room of rooms) {
    const on=['living_room','master_bedroom','dining','hallway'].includes(room.id);
    room.lights.forEach((id,i)=>set(id,on?'on':'off',{friendly_name:i?`${room.label} · light ${i}`:`${room.label} lights`,brightness:room.id==='hallway'?100:190,color_mode:'rgb',rgb_color:room.id==='living_room'?(i%2?[255,116,175]:[109,207,255]):room.id==='dining'?[255,190,105]:[255,222,175],...(i===0?{entity_id:room.lights.slice(1)}:{})}));
    room.media.forEach((id,i)=>set(id,room.id==='living_room'&&i===1?'playing':'off',{friendly_name:id.includes('tv')?'Living room TV':name(id),volume_level:.28,device_class:id.includes('tv')?'tv':'speaker'}));
    room.covers.forEach((id,i)=>set(id,'open',{friendly_name:i?`Roller blind ${i}`:'All roller blinds',current_position:65}));
  }
  view.configure({assetBase:new URL('.',document.baseURI),rooms,mode:'demo'});view.states=states;
  const node=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text)n.textContent=text;return n;};
  function group(host,title) {const section=node('section','control-group');section.append(node('h3',null,title));host.append(section);return section;}
  function device(host,title,icon) {const box=node('div','demo-device'),top=node('div','device-top'),label=node('div','device-name');label.append(node('span','device-icon',icon),document.createTextNode(title));top.append(label);box.append(top);host.append(box);return{box,top};}
  function toggle(top,on,fn,labels=['Off','On']) {const b=node('button','toggle',labels[+on]);b.type='button';b.setAttribute('aria-pressed',String(on));b.addEventListener('click',()=>{on=!on;b.setAttribute('aria-pressed',String(on));b.textContent=labels[+on];fn(on);});top.append(b);return b;}
  function slider(box,title,value,fn) {const row=node('label','control-row'),input=node('input'),out=node('output');input.type='range';input.min='0';input.max='100';input.value=value;input.setAttribute('aria-label',title);out.textContent=value+'%';row.append(node('span',null,title),input,out);input.addEventListener('input',()=>{out.textContent=input.value+'%';fn(+input.value);});box.append(row);return input;}
  const rgbHex=rgb=>'#'+rgb.map(v=>v.toString(16).padStart(2,'0')).join('');
  const publish=()=>{view.states=states;};
  function render(room) {
    const host=view.controlHost, expanded=host.querySelector('details')?.open;host.replaceChildren();if(!room)return;
    host.append(node('p','notice','Demo controls · sample states only. No devices are operated.'));
    const lightIds=room.lights.length>1?room.lights.slice(1):room.lights;
    const sync=()=>{
      if(room.lights.length>1)states[room.lights[0]].state=lightIds.some(id=>states[id].state==='on')?'on':'off';
      publish();
    };
    if(room.lights.length) {
      const section=group(host,'Lighting');
      section.addEventListener('change',()=>render(room));
      const buildLight=(id,parent,isGroup)=>{
        const state=states[id],targets=isGroup?lightIds:[id],{box,top}=device(parent,isGroup?'Room lighting':state.attributes.friendly_name,'◉');
        toggle(top,state.state==='on',on=>{targets.forEach(t=>states[t].state=on?'on':'off');sync();render(room);});
        slider(box,'Brightness',Math.round(state.attributes.brightness/255*100),v=>{targets.forEach(t=>{states[t].attributes.brightness=Math.round(v/100*255);states[t].state=v?'on':'off';});if(isGroup)state.attributes.brightness=Math.round(v/100*255);sync();});
        const row=node('label','control-row'),input=node('input');input.type='color';input.value=rgbHex(C.lightColor(state));input.setAttribute('aria-label',`${isGroup?'Room':state.attributes.friendly_name} colour`);row.append(node('span',null,isGroup?'Set all lights to a colour':'Colour'),input);box.append(row);
        input.addEventListener('input',()=>{const color=input.value.slice(1).match(/../g).map(v=>parseInt(v,16));targets.forEach(t=>{states[t].attributes.rgb_color=color;states[t].state='on';});if(isGroup)state.attributes.rgb_color=color;sync();});
      };
      buildLight(room.lights[0],section,true);
      if(lightIds.length>1){const details=node('details');details.open=!!expanded;details.append(node('summary',null,`Individual lights · ${lightIds.length}`));lightIds.forEach(id=>buildLight(id,details,false));section.append(details);}
    }
    if(room.covers.length){const section=group(host,'Roller blinds'),{box,top}=device(section,'All roller blinds','▤');const position=node('span','device-meta');top.append(position);
      const move=v=>{room.covers.forEach(id=>{states[id].attributes.current_position=v;states[id].state=v?'open':'closed';});position.textContent=v===0?'Closed':v===100?'Open':v+'% open';publish();};
      const input=slider(box,'Open',states[room.covers[0]].attributes.current_position,move);move(+input.value);
      const actions=node('div','cover-actions');for(const [title,value] of [['Close',0],['Half',50],['Open',100]]){const b=node('button','small-action',title);b.type='button';b.addEventListener('click',()=>{input.value=value;input.dispatchEvent(new Event('input'));});actions.append(b);}box.append(actions);
    }
    if(room.media.length){const section=group(host,'Speakers & TV');room.media.forEach(id=>{const state=states[id],tv=state.attributes.device_class==='tv',{box,top}=device(section,state.attributes.friendly_name,tv?'▣':'♫');toggle(top,['on','playing'].includes(state.state),on=>{state.state=on?(tv?'on':'playing'):'off';publish();},tv?['Off','On']:['Play','Pause']);slider(box,'Volume',Math.round(state.attributes.volume_level*100),v=>{state.attributes.volume_level=v/100;publish();});});}
    host.append(node('p','notice','In Home Assistant, these become native device controls, with colour pickers, media playback and your existing scenes.'));
  }
  view.addEventListener('room-select',e=>render(e.detail.room));
  document.querySelectorAll('[data-scene]').forEach(b=>b.addEventListener('click',()=>{
    const scene=b.dataset.scene;view.scene=scene;
    document.querySelectorAll('[data-scene]').forEach(n=>n.setAttribute('aria-pressed',String(n===b)));
    for(const [id,ext] of [['download-image','png'],['download-model','blend'],['download-glb','glb']])document.getElementById(id).href=`${scene}.${ext}`;
  }));
  document.getElementById('colours').addEventListener('change',e=>view.colours=e.target.checked);
  document.getElementById('labels').addEventListener('change',e=>view.labels=e.target.checked);
})();
