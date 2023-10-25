# curb_energy for Home Assistant

A [Home Assistant](https://www.home-assistant.io/) component for [Curb Energy monitoring](https://www.poweredbyelevation.com/curb-energy-monitoring)

It loads all circuits from your Curb account into their own entities and updates them every 5 minutes.  Handles authentication and refreshing data.

Right now, we're using the aggregate call from the api so it will give you the average over the last 5 minutes each time it's called.

## To Use:
* Download or clone the repo into your Home Assistant config/custom_component folder.
* Add entries to your configuration.yaml file as follows:

```yaml
sensor:
  - platform: curb_energy
    username: {Your Curb Login}
    password: {Your Curb Password}
```

* Restart your Home Assistant

All your defined Curb circuits should show up in your Home assistant prefixed with the curb_energy domain.  Note that any names will be stripped of special characters and spaces will be replaced with underscores

For example, your "Main" circuit should show up in Home Assistant as curb_assistant.main.

## Todo:
* Handle more than one location
* Error handling
* Correct for longer/shorter periods between calls