# PhoneTrack Home Assistant Integration

A Home Assistant custom component that integrates with PhoneTrack to provide device tracking capabilities.
It is inspired by [homeassistant-phonetrack by j1nx](https://github.com/j1nx/homeassistant-phonetrack), but updated and configurable via the Home Assistant UI.

## Installation

### HACS Installation
<br>
Download the integration with:

[![Open Phonetrack on Home Assistant Community Store (HACS).](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=woulve&repository=Phonetrack&category=frontend)

Then set up from the integrations menu.

<br>

### Manual Installation

1. Copy the `phonetrack` folder to your `custom_components` directory
2. Restart Home Assistant

## Configuration

### Getting the API URL from PhoneTrack

Follow these steps to obtain your PhoneTrack API URL:

1. **Open PhoneTrack**: Launch your PhoneTrack web interface
2. **Navigate to Main Tab**: Go to the main tracking view where your devices are listed
3. **Access Share Options**: Click the Share button to open sharing configuration

   ![Click the Share button](./img/step1.png)

4. **Copy API URL**: Locate and copy the whole **API URL (JSON, last positions)** field and the exact device name.

   ![Copy the API URL field and device name](./img/step2.png)


The integration is configured through the Home Assistant UI:

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "PhoneTrack"
4. Fill in the configuration form:

### Configuration Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| **API URL** | Yes | - | Full PhoneTrack API endpoint URL with token (must contain `getlastpositions`) |
| **Device Name** | Yes | - | Name of the device as reported by PhoneTrack |
| **Integration Name** | Yes | PhoneTrack | Friendly name for this integration in Home Assistant |
| **Max GPS Accuracy** | Yes | 100 | Maximum allowed GPS accuracy in meters. Updates with worse accuracy are ignored |
| **Update Interval** | Yes | 60 | How often to poll the PhoneTrack API (in seconds) |
| **Last Update Timeout** | Yes | 0 | Mark device as unavailable after this many minutes without updates. Set to 0 to disable (recommended for devices that only send updates when moving) |

### Important Notes

⚠️ **Last Update Timeout Warning**: The default value for "Last Update Timeout" is **0 (disabled)**. This is recommended when your PhoneTrack app is configured to send updates only when the device moves. If timeout is enabled with movement-based tracking, your device may incorrectly appear as unavailable when stationary. Only enable this timeout if your app sends updates at regular intervals regardless of movement.

## Support

- **Documentation**: [PhoneTrack GitHub](https://github.com/woulve/phonetrack)
- **Issues**: [Report Issues](https://github.com/woulve/phonetrack/issues)
