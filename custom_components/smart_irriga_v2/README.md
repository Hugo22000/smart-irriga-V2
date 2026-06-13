# Smart Irrigation V2

A **Home Assistant** custom integration for managing irrigation systems with multiple zones and pumps.

## Features
- **Zone Management**: Create and manage irrigation zones.
- **Pump Configuration**: Configure up to 3 pumps per zone with custom flow rates (5-300 ml).
- **Manual Control**: Start irrigation manually via buttons.
- **Volume Tracking**: Track water volume used per zone.

## Installation

### Method 1: Manual Installation
1. Copy the `custom_components/smart_irriga_v2` folder to your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Go to **Settings > Devices & Services > Add Integration** and search for **"Smart Irrigation V2"**.

### Method 2: Via HACS (Custom Repository)
1. Add this repository as a custom repository in HACS:
   ```
   https://github.com/Hugo22000/smart-irriga-V2
   ```
2. Install the integration via HACS.
3. Restart Home Assistant.

## Configuration

1. **Add Integration**:
   - Go to **Settings > Devices & Services > Add Integration**.
   - Select **Smart Irrigation V2**.

2. **Configure Zone**:
   - **Zone Name**: Enter a name for your irrigation zone (e.g., "Garden", "Lawn").
   - **Number of Pumps**: Select how many pumps you want to configure (1-3).

3. **Configure Pumps**:
   For each pump, provide:
   - **Switch Entity**: Select the Home Assistant switch entity that controls the pump (e.g., `switch.pump_1`).
   - **Flow Rate**: Set the water flow rate in milliliters (5-300 ml).

## Entities Created

For each configured zone, the following entities will be created:

### Switches
- **`switch.<zone_name>_pump_<n>`**: Controls each pump individually.

### Buttons
- **`button.<zone_name>_start_irrigation`**: Starts irrigation for all pumps in the zone.

### Sensors
- **`sensor.<zone_name>_water_volume`**: Tracks the total water volume used by the zone.

## Example Configuration

### YAML (if needed for advanced setups)
```yaml
# No YAML configuration required - everything is configured via the UI
```

## Roadmap
- [ ] Add automatic irrigation scheduling
- [ ] Implement soil moisture sensor integration
- [ ] Add water usage history and statistics
- [ ] Support for multiple zones

## Troubleshooting

### Integration Not Loading
- Ensure the `custom_components/smart_irriga_v2` folder is in your Home Assistant `custom_components` directory.
- Check the Home Assistant logs for errors.
- Restart Home Assistant after installation.

### Pump Not Working
- Verify that the switch entity exists and is functional in Home Assistant.
- Check that the flow rate is set to a value between 5 and 300 ml.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
