const test = require('node:test');
const assert = require('node:assert/strict');
require('./floorplan-core.js');
const C=globalThis.FloorplanCore;
const light=(state,attributes={})=>({state,attributes});
test('colour temperature overrides stale RGB, and HS is converted',()=>{
  assert.deepEqual(C.lightColor(light('on',{color_mode:'color_temp',color_temp_kelvin:2700,rgb_color:[0,0,255]})),C.kelvin(2700));
  assert.deepEqual(C.lightColor(light('on',{color_mode:'hs',hs_color:[120,100]})),[0,255,0]);
  assert.deepEqual(C.lightColor(light('on',{color_mode:'white',rgb_color:[0,0,255]})),[255,244,226]);
});
test('individual colours survive aggregation; off and unavailable lights do not glow',()=>{
  const room={lights:['light.group','light.red','light.blue','light.off','light.missing']};
  const states={'light.group':light('on'), 'light.red':light('on',{rgb_color:[255,0,0],brightness:255}), 'light.blue':light('on',{rgb_color:[0,0,255],brightness:127.5}), 'light.off':light('off',{rgb_color:[0,255,0]}),'light.missing':light('unavailable')};
  const s=C.roomLights(room,states);assert.equal(s.active.length,2);assert.equal(s.unknown,1);assert.equal(s.mixed,true);assert.equal(s.brightness,.75);assert.deepEqual(s.palette,[[255,0,0],[0,0,255]]);
  assert.match(C.summary(room,states),/Mixed colours · Some unavailable/);
});
test('runtime nested group membership is authoritative, unique and cycle-safe',()=>{
  const states={'light.group':light('on',{entity_id:['light.nested','light.red']}),'light.nested':light('on',{entity_id:['light.group','light.red']}),'light.red':light('on',{rgb_color:[255,0,0]})};
  assert.deepEqual(C.roomLights({lights:['light.group','light.old']},states).ids,['light.red']);
});
test('only use aggregate colour when child states are not available at all',()=>{
  const room={lights:['light.group','light.child']};
  assert.equal(C.roomLights(room,{'light.group':light('on')}).aggregate,true);
  const s=C.roomLights(room,{'light.group':light('on'),'light.child':light('unavailable')});assert.equal(s.active.length,0);assert.equal(s.unknown,1);assert.equal(s.aggregate,false);
});
test('no configured kitchen light is not reported as off or fabricated',()=>{
  assert.deepEqual(C.roomLights({lights:[]}).active,[]);assert.equal(C.summary({lights:[]},{}),'Room controls');
});
test('room focus and pan constraints remain finite and inside the image on desktop and phone',()=>{
  require('./room-config.js');
  for(const [w,h] of [[1100,740],[360,370],[200,440]]){
    const r=C.imageRect(w,h);assert.ok(r.width<=w+.001&&r.height<=h+.001);
    for(const room of globalThis.FloorplanRoomConfig.rooms){
      const c=C.focusRoom(room.bounds,w,h,r);assert.ok(c.scale>=1.4&&c.scale<=3.6);assert.ok(Object.values(c).every(Number.isFinite));
      for(const [offset,pan,size,viewport] of [[r.left,c.x,r.width,w],[r.top,c.y,r.height,h]]){
        if(size*c.scale>=viewport){assert.ok(offset+pan<=.001);assert.ok(offset+pan+size*c.scale>=viewport-.001);}
        else assert.ok(Math.abs(offset+pan+(size*c.scale)/2-viewport/2)<.001);
      }
    }
    const fit=C.constrain({scale:1,x:999,y:-999},w,h,r);assert.ok(fit.scale===1 && Math.abs(fit.x)<.001 && Math.abs(fit.y)<.001);
  }
});
