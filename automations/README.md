# Plant Alert Automations

This folder contains modular plant alert automations that turn lights red when plants need water.

## Files

### plant_alerts_activate.yaml
**Trigger:** 7:00 AM daily (local time)

**Purpose:** Morning plant health check. Turns assigned lights red for any plants below moisture or battery thresholds.

**Behavior:**
- Only turns lights red for plants with problems
- Does NOT affect lights for healthy plants
- Sends mobile + persistent notifications if any plants need attention

**Schedule:** Change the trigger time (`at: '07:00:00'`) to run at a different time.

---

### plant_alerts_deactivate.yaml
**Trigger:** Whenever soil moisture rises above 25%

**Purpose:** Automatically turns off alert lights when plants recover.

**Behavior:**
- Monitors all plant moisture sensors continuously
- When a plant recovers (moisture > 25%), checks if ALL plants sharing that light are healthy
- Only turns off the light if every plant mapped to it is above thresholds
- Prevents premature "all recovered" actions

**Schedule:** Runs throughout the day on state changes (no time restriction).

---

### plant_config.yaml
Shared configuration for plant mappings, thresholds, and alert colors.

**Note:** Currently unused but available for future DRY improvements.

---

## Configuration

### Plant Mappings
Each automation includes its own `plants` variable list mapping:
- Plant name
- Light entity
- Moisture sensor
- Battery sensor

**Example:**
```yaml
plants:
  - name: plant_1
    light: light.lounge_1
    moisture_sensor: sensor.plant_1_soil_moisture
    battery_sensor: sensor.plant_1_battery
```

### Thresholds
- **moisture_threshold:** 20 (alert triggers below this)
- **battery_threshold:** 10 (alert triggers below this)
- **Recovery threshold:** 25 (deactivation triggers above this)

### Alert Settings
- **alert_color:** red
- **brightness:** 255 (max)

---

## Customization

### Change Alert Time
Edit `plant_alerts_activate.yaml`:
```yaml
triggers:
- at: '08:30:00'  # Change to desired time
  trigger: time
```

### Change Recovery Behavior
Edit `plant_alerts_deactivate.yaml`:
- To make deactivation run only at specific times, replace the numeric_state trigger with a time trigger
- To disable auto-recovery entirely, disable the automation in HA UI

### Add/Remove Plants
Update the `plants` list in **both** automation files to keep them in sync.

### Change Thresholds
Update `moisture_threshold`, `battery_threshold`, and the `above: 25` recovery trigger value.

---

## Troubleshooting

**Lights not turning red at 7am:**
- Check if plant moisture/battery sensors are returning valid numeric values
- Verify light entity IDs are correct
- Check Home Assistant logs for template errors

**Lights turn off too early:**
- Multiple plants may share one light; check if all plants mapped to that light have recovered
- Verify recovery threshold (25) vs alert threshold (20) hysteresis

**"All plants recovered" notifications:**
- These have been removed from the activate automation
- No notifications are sent on recovery

---

## Home Assistant Configuration

This folder is loaded via `configuration.yaml`:
```yaml
automation: !include_dir_merge_list automations/
```

All `.yaml` files in this directory are automatically loaded as separate automations.
