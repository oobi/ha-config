/* Shared presentation layer. It never calls Home Assistant services. */
(() => {
  const C = globalThis.FloorplanCore;
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text) n.textContent = text; return n; };
  class FloorplanRoomView extends HTMLElement {
    constructor() {
      super(); this.attachShadow({mode:'open'}); this._states = {}; this.rooms = []; this.camera = {scale:1,x:0,y:0}; this.pointers = new Map(); this.mode = 'demo';
    }
    configure({assetBase, rooms, mode='demo'}) {
      this.assetBase = new URL(assetBase, document.baseURI); this.rooms = rooms; this.mode = mode;
      this.shadowRoot.replaceChildren();
      const css = el('link'); css.rel = 'stylesheet'; css.href = new URL('room-view.css?v=5',this.assetBase); this.shadowRoot.append(css);
      this.shadowRoot.innerHTML += `<div class="layout">
        <div class="map-column"><div class="map-toolbar"><button class="back" type="button" disabled>← Whole home</button><label class="room-picker"><span class="sr-only">Choose a room</span><select aria-label="Choose a room"><option value="">Explore a room…</option></select></label></div>
          <div class="map" tabindex="0" aria-label="Floorplan. Select a room, or use plus, minus and arrow keys to explore. Escape returns to the whole home.">
            <div class="world"><img class="render" alt="Isometric cutaway floorplan of the upper floor" draggable="false"><div class="glows"></div><svg class="regions" viewBox="0 0 1000 1000" preserveAspectRatio="none" aria-hidden="true"></svg><div class="labels"></div></div>
            <div class="map-note"><span class="mode-badge"></span><span class="map-hint">Touch a room to explore</span></div>
            <div class="zoom"><button type="button" data-zoom="out" aria-label="Zoom out">−</button><button type="button" data-zoom="fit" aria-label="Fit selected room or whole home">Fit</button><button type="button" data-zoom="in" aria-label="Zoom in">+</button></div>
          </div>
        </div>
        <aside class="panel" hidden aria-label="Room controls"><div class="panel-heading"><p class="eyebrow">ROOM CONTROLS</p><button class="close" type="button" aria-label="Close room controls">×</button><h2></h2><p class="room-status" role="status"></p><div class="swatches" aria-label="Active light colours"></div><p class="palette-note"></p></div><div class="controls"></div></aside>
      </div>`;
      this.$ = s => this.shadowRoot.querySelector(s);
      this.world = this.$('.world'); this.viewport = this.$('.map'); this.controlHost = this.$('.controls');
      this.$('.render').src = new URL('upper.png',this.assetBase);
      this.$('.mode-badge').textContent = mode === 'demo' ? 'DEMO · SAMPLE STATES' : 'HOME ASSISTANT';
      this.nodes = new Map();
      for (const room of rooms) {
        const option = el('option',null,room.label); option.value=room.id; this.$('select').append(option);
        const path = document.createElementNS('http://www.w3.org/2000/svg','polygon');
        path.setAttribute('points',room.polygon.map(p=>p.map(v=>v*1000).join(',')).join(' ')); path.dataset.room=room.id; this.$('.regions').append(path);
        const label = el('button','room-label'); label.type='button'; label.dataset.room=room.id; label.style.left=room.anchor[0]*100+'%'; label.style.top=room.anchor[1]*100+'%';
        label.append(el('span','light-dot'),el('span','room-name',room.label)); label.addEventListener('click',()=>this.selectRoom(room.id)); this.$('.labels').append(label);
        const glow = el('div','glow'), paint=el('div','paint'); glow.style.maskImage=`url("${new URL(room.mask,this.assetBase)}")`; glow.style.webkitMaskImage=glow.style.maskImage;
        const [x0,y0,x1,y1]=room.bounds; Object.assign(paint.style,{left:x0*100+'%',top:y0*100+'%',width:(x1-x0)*100+'%',height:(y1-y0)*100+'%'}); glow.append(paint); this.$('.glows').append(glow);
        this.nodes.set(room.id,{label,path,glow,paint});
      }
      this.$('select').addEventListener('change',e=>this.selectRoom(e.target.value));
      this.$('.back').addEventListener('click',()=>this.selectRoom(''));
      this.$('.close').addEventListener('click',()=>{this.selectRoom(''); this.$('select').focus();});
      this.$('.zoom').addEventListener('click',e=>{ const action=e.target.dataset.zoom; if(action==='fit')this.fit(); else if(action)this.zoom(action==='in'?1.25:.8); });
      this.bindGestures(); this.updateStates(); this.observe();
    }
    connectedCallback() { if(this.viewport)this.observe(); }
    disconnectedCallback() { this.observer?.disconnect(); }
    observe() { this.observer?.disconnect(); this.observer = new ResizeObserver(()=>this.fit()); this.observer.observe(this.viewport); }
    set states(value) { this._states=value||{}; if(this.nodes)this.updateStates(); }
    get selectedRoom() { return this.rooms.find(r=>r.id===this.selected); }
    set colours(value) { this.toggleAttribute('hide-colours',!value); }
    set labels(value) { this.toggleAttribute('hide-labels',!value); }
    set scene(value) {
      this._scene=value; this.toggleAttribute('outside',value==='outside'); this.selectRoom('');
      this.$('.render').src=new URL(value==='outside'?'outside.png':'upper.png',this.assetBase);
      this.$('.render').alt=value==='outside'?'Isometric site study with house, pool, garden and driveway':'Isometric cutaway floorplan of the upper floor';
      this.$('select').disabled=value==='outside'; this.$('.map-hint').textContent=value==='outside'?'Outside · massing study':'Touch a room to explore';
    }
    selectRoom(id) {
      if(id && !this.rooms.some(r=>r.id===id))return;
      this.selected=id||''; this.$('select').value=this.selected; this.$('.panel').hidden=!id; this.$('.back').disabled=!id;
      this.$('.layout').classList.toggle('selected',!!id);
      for(const [key,n] of this.nodes) { n.label.setAttribute('aria-pressed',String(key===id)); n.path.classList.toggle('selected',key===id); }
      this.updateDetail(); this.fit();
      this.dispatchEvent(new CustomEvent('room-select',{detail:{room:this.selectedRoom||null},bubbles:true,composed:true}));
    }
    updateStates() {
      for(const room of this.rooms) {
        const s=C.roomLights(room,this._states), n=this.nodes.get(room.id);
        const colors=s.palette.map(c=>`rgb(${c.join(',')})`), background=colors.length>1?`linear-gradient(115deg,${colors.join(',')})`:colors[0]||'transparent';
        n.paint.style.background=background; n.glow.style.opacity=s.active.length?String(.12+s.brightness*.47):'0';
        n.label.querySelector('.light-dot').style.background=colors.length?background:'#a6aaa2';
        n.label.setAttribute('aria-label',`${room.label}. ${C.summary(room,this._states)}. Open controls.`);
      }
      this.updateDetail();
    }
    updateDetail() {
      const room=this.selectedRoom; if(!room)return;
      const s=C.roomLights(room,this._states); this.$('h2').textContent=room.label; this.$('.room-status').textContent=C.summary(room,this._states);
      const swatches=this.$('.swatches'); swatches.replaceChildren();
      for(const light of s.active) {
        const dot=el('span','swatch'); dot.style.background=`rgb(${light.color.join(',')})`; dot.title=`${light.name} · ${Math.round(light.brightness*100)}%`; dot.setAttribute('role','img'); dot.setAttribute('aria-label',dot.title); swatches.append(dot);
      }
      this.$('.palette-note').textContent=s.mixed?'Mixed colours · one swatch per active light':s.active.length?'Active light colours':'';
    }
    measure() { const {width,height}=this.viewport.getBoundingClientRect(); this.size={width,height}; this.rect=C.imageRect(width,height); Object.assign(this.world.style,{width:this.rect.width+'px',height:this.rect.height+'px',left:this.rect.left+'px',top:this.rect.top+'px'}); }
    fit() { if(!this.viewport)return; this.measure(); if(!this.size.width)return; this.camera=this.selectedRoom?C.focusRoom(this.selectedRoom.bounds,this.size.width,this.size.height,this.rect):{scale:1,x:0,y:0}; this.draw(true); }
    draw(animate=false) { this.world.classList.toggle('animate',animate); this.camera=C.constrain(this.camera,this.size.width,this.size.height,this.rect); const {x,y,scale}=this.camera; this.world.style.transform=`translate(${x}px,${y}px) scale(${scale})`; this.world.style.setProperty('--inverse-scale',1/scale); }
    zoom(factor,point) {
      if(!this.rect)return; const p=point||{x:this.size.width/2,y:this.size.height/2}, old=this.camera.scale, scale=C.clamp(old*factor,1,4), k=scale/old;
      this.camera={scale,x:p.x-this.rect.left-k*(p.x-this.rect.left-this.camera.x),y:p.y-this.rect.top-k*(p.y-this.rect.top-this.camera.y)}; this.draw(false);
    }
    bindGestures() {
      const v=this.viewport, local=e=>{const b=v.getBoundingClientRect();return{x:e.clientX-b.left,y:e.clientY-b.top};};
      v.addEventListener('pointerdown',e=>{
        if(e.target.closest('button') || e.button>0)return;
        this.world.classList.remove('animate'); v.setPointerCapture(e.pointerId); this.pointers.set(e.pointerId,local(e));
        this.press={point:local(e),room:e.target.dataset.room,moved:this.pointers.size>1}; this.gesture=null;
      });
      v.addEventListener('pointermove',e=>{
        if(!this.pointers.has(e.pointerId))return; const previous=this.pointers.get(e.pointerId), p=local(e); this.pointers.set(e.pointerId,p);
        if(this.pointers.size===1) { const distance=Math.hypot(p.x-this.press.point.x,p.y-this.press.point.y); if(distance>6)this.press.moved=true; if(this.press.moved){this.camera.x+=p.x-previous.x;this.camera.y+=p.y-previous.y;this.draw();} }
        else { this.press.moved=true; const [a,b]=[...this.pointers.values()], center={x:(a.x+b.x)/2,y:(a.y+b.y)/2}, distance=Math.hypot(a.x-b.x,a.y-b.y);
          if(this.gesture) {this.zoom(distance/Math.max(1,this.gesture.distance),this.gesture.center); this.camera.x+=center.x-this.gesture.center.x;this.camera.y+=center.y-this.gesture.center.y;this.draw();} this.gesture={center,distance}; }
      });
      const finish=(e,cancelled)=>{ if(!this.pointers.has(e.pointerId))return; const tap=!cancelled && !this.press?.moved && this.pointers.size===1, room=this.press?.room; this.pointers.delete(e.pointerId); this.gesture=null; if(tap&&room)this.selectRoom(room); };
      v.addEventListener('pointerup',e=>finish(e,false)); v.addEventListener('pointercancel',e=>finish(e,true)); v.addEventListener('lostpointercapture',e=>finish(e,true));
      v.addEventListener('wheel',e=>{e.preventDefault();this.zoom(Math.exp(-e.deltaY*.0015),local(e));},{passive:false});
      v.addEventListener('keydown',e=>{
        if(e.key==='Escape'){e.preventDefault();this.selectRoom('');this.$('select').focus();return;}
        if(e.target!==v)return;
        if(['+','=','-','0','ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key))e.preventDefault();
        if(e.key==='+'||e.key==='=')this.zoom(1.2); if(e.key==='-')this.zoom(1/1.2); if(e.key==='0')this.fit();
        if(e.key.startsWith('Arrow')){this.camera.x+=e.key==='ArrowLeft'?45:e.key==='ArrowRight'?-45:0;this.camera.y+=e.key==='ArrowUp'?45:e.key==='ArrowDown'?-45:0;this.draw();}
      });
      this.shadowRoot.addEventListener('keydown',e=>{if(e.key==='Escape' && this.selected){this.selectRoom('');this.$('select').focus();}});
    }
  }
  if(!customElements.get('floorplan-room-view'))customElements.define('floorplan-room-view',FloorplanRoomView);
})();
