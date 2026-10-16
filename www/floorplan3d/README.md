# Floorplan 3D

A separate, unfurnished isometric study of the existing floorplan. Nothing in
`www/floorplan`, the dashboard YAML, or the Home Assistant configuration is
changed or replaced.

## View it

Open `index.html` in a browser, or visit **`/local/floorplan3d/index.html`** on
your existing Home Assistant server. It works without internet access, external
fonts, JavaScript libraries, or a build step.

The preview offers tap-to-zoom rooms, a room selector, light colours, individual
bulb swatches, and demo controls for lights, speakers, TV and roller blinds.
Try the living room first: its sample lights use two colours. On phones,
controls sit below the selected room; on larger screens they sit alongside it.
The outside study is also available. Day/dusk render files remain available
separately; the interactive view uses the neutral daylight render.

Scroll or pinch to zoom, drag to pan. Keyboard: focus the image, then use `+`,
`-`, arrow keys, and `0` to fit. Escape or **Whole home** closes the room.
Room buttons and the selector work with a keyboard. Reduced motion is respected.
Small colour dots mark rooms without covering the model. Names appear on hover
or keyboard focus; on touch screens, tap a room or use the room selector. The
selected room's name stays in the control panel. **Room markers** hides the dots
for an unobstructed view; the floor itself remains tappable. The HA card's
`show_labels` option controls these markers.
This is an interactive rendered view, not an orbiting 3D viewer.

**The standalone page uses sample states and local demo controls only.** It has
no HA authentication, service calls or tokens. Reloading resets the demo.

## Assets

| File | Purpose |
| --- | --- |
| `upper.png` | Daylight isometric render, 2400 × 2000 |
| `upper-transparent.png` | Same camera, transparent background |
| `upper-dusk.png` | Same camera, warm illustrative dusk lighting |
| `upper-labels.svg` | Separate, exactly aligned room-name overlay |
| `upper-labelled.png` | Daylight render with room names, ready for an image card |
| `outside.png` | Separate site massing study: pool, spa, house, garden, driveway |
| `upper.blend`, `outside.blend` | Editable Blender scenes, including materials and lights |
| `upper.glb`, `outside.glb` | Portable 3D geometry with basic material colours |
| `model.json` | Traced outlines, explicit walls/openings, room IDs, finishes, and furniture list |
| `reference-trace.svg` | Top-down review of the interpretation of your supplied plan |
| `room-anchors.json` | Projected room anchor positions, as percentages of the full image |
| `build.py` | Reproducible Blender generator |

The procedural timber grain and studio lighting live in the Blender scenes.
GLB exports carry basic material colours, not baked versions of those shaders.

## What is established, and what is a starting point

- Room polygons, stepped bedroom/robe walls and deck/balcony outlines now follow
  the more detailed reference image supplied in chat. The old SVG remains untouched.
- Eight shallow stair treads follow the flight in the reference. Stair rise and
  lower-floor geometry have not been established.
- Door swings, exterior windows, balcony sliders, wardrobe fronts, and internal
  passages are traced approximately. The kitchen/dining passage and ensuite
  entrance are best-effort interpretations of the small plan symbols.
- The model contains 26 wall runs and 26 opening definitions, including the stair
  landing. Each is separately editable in `model.json`. Window sill/head heights,
  door heights, bronze frame profiles and off-white doors are proposed details.
- Pale plaster, oak, limestone tile, and weathered decking are proposed finishes.
- Walls have deliberately different display heights for a readable cutaway.
  Doors and glazing on lowered walls are cut down with them. They do not
  represent measured wall or opening heights.
- Coordinates now use the supplied 930 × 958 reference image with 52 pixels per
  model metre as a convenient working scale. This corrects the earlier SVG's
  bedroom proportions. Source dimension labels remain metadata; exact room sizes
  and opening widths still need measurements rather than scaling a raster plan.
- The site and upper floor are separate studies. Their source shapes and scales
  do not establish a reliable alignment. The site's house and shed are simple
  massing blocks; flat caps do not assert a real roof shape or height.
- Dusk lighting is an appearance preview, unrelated to live light states.

## Furnishing it to match the real house

Yes: this is real, editable geometry, so it can be furnished and re-rendered
consistently. A useful next pass is one room at a time. Give:

1. Which room, and a reference such as “the wall at the top of the original plan.”
2. Corrections to the traced doors/windows, plus actual widths and heights if known.
3. Floor/wall colours and materials; photographs are useful for matching them.
4. Furniture type, approximate width × depth × height, placement, and facing.
5. Distinctive details such as rugs, curtains, artwork, plants, and lighting.

For example: “In the living room, the 2.8 m charcoal sofa is against the bottom
wall of the original plan, facing a timber TV unit on the opposite wall. There
is a cream rug between them and a tall plant in the right-hand corner.”

Photographs and real measurements will get much closer to the actual house.
The `Furniture` collection is currently empty. `model.json` also has an empty
`furniture` array for future objects. The generator supports simple box objects
as placement blockouts; detailed furniture can be modelled in the generator or
added to a separately saved copy of the Blender scene.

## Home Assistant interactive card

`floorplan-card.js` is a custom dashboard card using the same viewer. Home
Assistant passes its existing `hass` object to the card. Actual light states
drive the floor tint and swatches; native Tile, Media Control and Entities cards
provide the device controls. No token should be placed in these assets.

1. In **Settings → Dashboards → Resources**, add
   `/local/floorplan3d/floorplan-card.js?v=5` as a **JavaScript module**. Advanced
   mode may be needed to show Resources. If your resources are managed in YAML,
   register the same URL with `type: module` in your existing resource list.
2. Add a Manual card to a new dashboard/view using
   `interactive-card.example.yaml`. Use a wide card/full-width section; a panel
   view also works well.
3. Select a room. Tap a light card for the native colour picker; its icon toggles
   power. Brightness appears for dimmable lights. Individual bulbs and blinds
   expand below their group. Media controls adapt to each entity. Existing scenes
   appear under **Scenes** and can start your existing lighting/automation flows.

These setup steps have **not** been applied to your Home Assistant configuration
or existing dashboard. The browser demo and core calculations have been checked;
native device controls still need an in-HA check after registration.

The floorplan is the control surface; keep scheduling, presence rules and other
automation logic in Home Assistant so they work with the dashboard closed.

### Room mapping and colour behaviour

- Default entity IDs come from `dashboards/home/rooms/*.yaml`, copied into
  `room-config.js`. Historical bedroom entity names are preserved intentionally.
  Kitchen currently has a speaker but no light in that source mapping.
- `lights` and `covers` list the room group first, then its individual devices.
  A single light may be listed on its own. Override a room's lists via the card's
  `rooms:` option, as shown in the example. Use an actual light group for a room
  with multiple lights. `media` and `scenes` list independent controls.
- For colours, runtime light-group membership takes priority and nested groups
  are expanded. Off/unavailable bulbs do not produce a tint. When only an
  aggregate entity is available, its state is used without inventing bulb detail.
- Mixed colours remain a gradient with a swatch per active light. Brightness
  affects tint strength. Colour-temperature mode uses Kelvin rather than stale
  RGB attributes. The tint indicates the room palette, **not** measured light
  spill or physical bulb positions. Bulb locations can be added later.
- `masks/*.png` are camera-aligned visible-floor masks: walls and joinery obscure
  the tint naturally. `room-interaction.json` contains projected touch regions.
- Receiving state updates and selecting rooms never calls a service. Only an
  explicit action in a native device control operates that device.

Card references: [custom cards](https://developers.home-assistant.io/docs/frontend/custom-ui/custom-card/),
[native card features](https://www.home-assistant.io/dashboards/features/),
[light state attributes](https://developers.home-assistant.io/docs/core/entity/light/).

For a simple static image card, `picture-card.example.yaml` uses the labelled
render. All assets are served under `/local/floorplan3d/`.

The old 2D overlays and icon percentages do **not** align with this camera.
`room-anchors.json` contains the new projected centres. The interactive card uses
`room-config.js` for its matching polygons, masks and entity mappings.

## Rebuild

Requires Blender 5.0 or compatible, tested with Blender 5.0.1. No Python package
installation is needed; the script runs inside Blender's Python.

```sh
/Applications/Blender.app/Contents/MacOS/Blender \
  --background --factory-startup \
  --python /Volumes/config/www/floorplan3d/build.py -- --quality final
```

Use `--quality draft --scene upper --skip-export` for a quick rendering check.
Use `--scene outside` to rebuild only the site. Final mode writes the PNGs and
model files in this folder. The labelled PNG can be regenerated with:

```sh
rsvg-convert upper-labels.svg -o /tmp/floorplan3d-labels.png
magick upper.png /tmp/floorplan3d-labels.png -compose over -composite upper-labelled.png
```

Rebuilding overwrites generated models and images in this folder. Save manual
Blender edits under a different filename before rebuilding. `model.json` and
`build.py` are the source for reproducible changes.

After changing the camera, geometry or room mapping, also regenerate the touch
regions and visible-floor masks (requires Pillow and NumPy for the second step):

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
  --python /Volumes/config/www/floorplan3d/build-interaction.py
python3 /Volumes/config/www/floorplan3d/prepare-interaction.py
node --test /Volumes/config/www/floorplan3d/floorplan-core.test.cjs
```

`build-interaction.py` reads `upper.blend` without saving changes to it. Rebuild
that scene first if the geometry has changed. After changing browser assets,
increment their `?v=` cache versions and refresh the Home Assistant browser.
