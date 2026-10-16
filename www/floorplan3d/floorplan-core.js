/* Shared, dependency-free colour and camera calculations. */
(() => {
  const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
  const rgb = value => Array.isArray(value) && value.length >= 3 && value.slice(0, 3).every(Number.isFinite)
    ? value.slice(0, 3).map(v => Math.round(clamp(v, 0, 255))) : null;
  function kelvin(value) {
    const t = clamp(value, 1000, 40000) / 100;
    return [t <= 66 ? 255 : 329.698727 * (t - 60) ** -.13320476,
      t <= 66 ? 99.4708026 * Math.log(t) - 161.119568 : 288.122169 * (t - 60) ** -.07551485,
      t >= 66 ? 255 : t <= 19 ? 0 : 138.517731 * Math.log(t - 10) - 305.044793]
      .map(v => Math.round(clamp(v, 0, 255)));
  }
  function hs(value) {
    const h = ((value[0] % 360) + 360) % 360 / 60, s = clamp(value[1] / 100, 0, 1);
    const c = s, x = c * (1 - Math.abs(h % 2 - 1));
    const channels = h < 1 ? [c,x,0] : h < 2 ? [x,c,0] : h < 3 ? [0,c,x] : h < 4 ? [0,x,c] : h < 5 ? [x,0,c] : [c,0,x];
    return channels.map(v => Math.round((v + 1 - c) * 255));
  }
  function lightColor(state) {
    const a = state?.attributes || {}, mode = a.color_mode;
    // Colour-temperature/white modes must not use stale RGB attributes.
    if (mode === 'color_temp') {
      const k = a.color_temp_kelvin || (a.color_temp ? 1000000 / a.color_temp : 3000);
      return kelvin(k);
    }
    if (['white', 'onoff', 'brightness'].includes(mode)) return [255, 244, 226];
    const color = rgb(a.rgb_color); // HA exposes converted RGB for HS/XY/RGBW modes too.
    if (color) return color;
    if (Array.isArray(a.hs_color) && a.hs_color.slice(0, 2).every(Number.isFinite)) return hs(a.hs_color);
    if (a.color_temp_kelvin) return kelvin(a.color_temp_kelvin);
    return [255, 244, 226];
  }
  function roomLights(room, states = {}) {
    const configured = room.lights || [], group = states[configured[0]];
    const declared = Array.isArray(group?.attributes?.entity_id) ? group.attributes.entity_id.filter(id => id.startsWith('light.')) : configured.slice(1);
    const leaves = new Set();
    function expand(id, seen = new Set()) {
      if (seen.has(id)) return;
      const next = new Set(seen).add(id), children = states[id]?.attributes?.entity_id;
      if (Array.isArray(children) && children.length) children.filter(x => x.startsWith('light.')).forEach(x => expand(x, next));
      else leaves.add(id);
    }
    declared.forEach(id => expand(id));
    let ids = [...leaves], aggregate = false;
    if (!ids.length || !ids.some(id => states[id])) { ids = configured.length ? [configured[0]] : []; aggregate = true; }
    const active = ids.filter(id => states[id]?.state === 'on').map(id => {
      const state = states[id], color = lightColor(state);
      const brightness = Number.isFinite(state.attributes?.brightness) ? clamp(state.attributes.brightness / 255, 0, 1) : 1;
      return { id, color, brightness: brightness * Math.max(...color) / 255, name: state.attributes?.friendly_name || id };
    });
    const palette = [];
    for (const light of active) {
      if (!palette.some(c => Math.hypot(...c.map((v,i) => v-light.color[i])) < 45)) palette.push(light.color);
    }
    const unknown = ids.filter(id => !states[id] || ['unknown', 'unavailable'].includes(states[id].state)).length;
    return { ids, active, palette, aggregate, unknown,
      brightness: active.length ? active.reduce((n,l) => n + l.brightness, 0) / active.length : 0,
      mixed: palette.length > 1 };
  }
  function summary(room, states) {
    if (!room.lights?.length) return 'Room controls';
    const s = roomLights(room, states);
    if (!s.active.length) return s.unknown ? 'Light status unavailable' : 'Lights off';
    const text = s.aggregate ? 'Lights on' : `${s.active.length} light${s.active.length === 1 ? '' : 's'} on`;
    return text + (s.mixed ? ' · Mixed colours' : '') + (s.unknown ? ' · Some unavailable' : '');
  }
  function imageRect(width, height, ratio = 1.2) {
    const w = Math.min(width, height * ratio), h = w / ratio;
    return { width: w, height: h, left: (width-w)/2, top: (height-h)/2 };
  }
  function constrain(camera, width, height, rect) {
    const s = clamp(camera.scale, 1, 4);
    const axis = (value, viewport, offset, image) => {
      const lo = viewport-offset-image*s, hi = -offset;
      return lo > hi ? (viewport-image*s)/2-offset : clamp(value,lo,hi);
    };
    return { scale: s, x: axis(camera.x,width,rect.left,rect.width), y: axis(camera.y,height,rect.top,rect.height) };
  }
  function focusRoom(bounds, width, height, rect) {
    const [x0,y0,x1,y1] = bounds;
    const s = clamp(Math.min(width/(rect.width*(x1-x0+.11)), height/(rect.height*(y1-y0+.16))),1.4,3.6);
    return constrain({ scale:s, x:width/2-rect.left-s*rect.width*(x0+x1)/2,
      y:height/2-rect.top-s*rect.height*((y0+y1)/2-.025) },width,height,rect);
  }
  globalThis.FloorplanCore = Object.freeze({ clamp, kelvin, hs, lightColor, roomLights, summary, imageRect, constrain, focusRoom });
})();
