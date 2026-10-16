import './room-config.js?v=3';
import './floorplan-core.js?v=3';
import './room-view.js?v=5';

// Native HA cards handle authentication, supported controls and service errors.
// Selecting a room and receiving state updates never calls a service.
class Floorplan3DCard extends HTMLElement {
  constructor() { super(); this.attachShadow({mode:'open'}); this.cards=[]; this.revision=0; }
  setConfig(config) {
    this.config=config; this.revision++; this.cards=[];
    const rooms=globalThis.FloorplanRoomConfig.rooms.map(room=>({...room,...(config.rooms?.[room.id]||{}),id:room.id,polygon:room.polygon,anchor:room.anchor,bounds:room.bounds,mask:room.mask}));
    for(const room of rooms)for(const key of ['lights','covers','media','scenes']) {
      if(!Array.isArray(room[key]) || !room[key].every(id=>typeof id==='string' && id.includes('.')))throw new Error(`${room.id}.${key} must be a list of entity IDs`);
    }
    this.shadowRoot.innerHTML='<style>:host{display:block}ha-card{display:block;overflow:hidden}floorplan-room-view{display:block}</style><ha-card><floorplan-room-view></floorplan-room-view></ha-card>';
    this.view=this.shadowRoot.querySelector('floorplan-room-view');
    this.view.configure({assetBase:new URL('.',import.meta.url),rooms,mode:'live'});
    this.view.colours=config.show_colours!==false; this.view.labels=config.show_labels!==false;
    this.view.states=this._hass?.states;
    this.view.addEventListener('room-select',e=>this.renderControls(e.detail.room));
  }
  set hass(hass) {
    this._hass=hass; if(this.view)this.view.states=hass.states;
    for(const card of this.cards)card.hass=hass;
    if(this.waitingForHass && this.view?.selectedRoom){this.waitingForHass=false;this.renderControls(this.view.selectedRoom);}
  }
  getCardSize() { return 10; }
  getGridOptions() { return {columns:24,min_columns:12,rows:12,min_rows:7}; }
  async renderControls(room) {
    const revision=++this.revision, host=this.view.controlHost; host.replaceChildren(); this.cards=[];
    if(!room)return;
    this.waitingForHass=!this._hass;
    const node=(tag,text,cls)=>{const n=document.createElement(tag); if(text)n.textContent=text;if(cls)n.className=cls;return n;};
    host.append(node('p','Tap a light card for its colour picker and full controls.','notice'));
    try {
      if(!window.loadCardHelpers)throw new Error('Open this card inside a Home Assistant dashboard.');
      const helpers=await window.loadCardHelpers();
      if(revision!==this.revision)return;
      const make=(config,parent)=>{ const card=helpers.createCardElement(config); card.hass=this._hass; parent.append(card);this.cards.push(card);return card; };
      const group=label=>{const div=node('section',null,'control-group');div.append(node('h3',label));host.append(div);return div;};
      const details=(label,parent)=>{const d=node('details');d.append(node('summary',label));parent.append(d);return d;};
      const light=id=>{
        const a=this._hass?.states[id]?.attributes||{};
        const dimmable=a.brightness!==undefined || a.supported_color_modes?.some(mode=>mode!=='onoff');
        return {type:'tile',entity:id,tap_action:{action:'more-info'},icon_tap_action:{action:'toggle'},features:dimmable?[{type:'light-brightness'}]:[]};
      };
      if(room.lights.length) {
        const g=group('Lighting'); make(light(room.lights[0]),g);
        const children=globalThis.FloorplanCore.roomLights(room,this._hass?.states).ids.filter(id=>id!==room.lights[0]);
        if(children.length){const d=details('Individual lights · '+children.length,g);children.forEach(id=>make(light(id),d));}
      }
      if(room.covers.length) {
        const g=group('Roller blinds');
        const cover=id=>{const features=[{type:'cover-open-close'}];if((this._hass?.states[id]?.attributes?.supported_features||0)&4)features.push({type:'cover-position'});return{type:'tile',entity:id,features};};
        make(cover(room.covers[0]),g);
        if(room.covers.length>1){const d=details('Individual blinds',g);room.covers.slice(1).forEach(id=>make(cover(id),d));}
      }
      if(room.media.length) {const g=group('Speakers & TV');room.media.forEach(id=>make({type:'media-control',entity:id},g));}
      if(room.scenes.length) {const d=details('Scenes',host);make({type:'entities',entities:room.scenes,show_header_toggle:false},d);}
      if(![...room.lights,...room.covers,...room.media,...room.scenes].length)host.append(node('p','No devices are mapped to this room yet.','notice'));
    } catch(error) {
      if(revision!==this.revision)return;
      host.append(node('p',`Controls could not load. ${error.message}`,'notice'));
    }
    if(revision!==this.revision)return;
    if(room.route?.startsWith('/')){const a=node('a','Open existing room dashboard ↗','room-link');a.href=room.route;host.append(a);}
  }
}
if(!customElements.get('floorplan-3d-card'))customElements.define('floorplan-3d-card',Floorplan3DCard);
window.customCards=window.customCards||[];
if(!window.customCards.some(c=>c.type==='floorplan-3d-card'))window.customCards.push({type:'floorplan-3d-card',name:'Floorplan 3D',description:'Tap rooms to zoom, see live light colours and open device controls.',preview:false});
