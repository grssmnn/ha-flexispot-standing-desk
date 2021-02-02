# HA Flexispot Standing Desk

This is an integration of a standing desk from Flexispot into home assistant in micropython. The height is read out from the desk's controller and it gets pushed to Home Assistant via MQTT. Also controlling the desk remotely should be possible, but I haven't implemented yet since this is not a real use case for me. I just want to have some statistics about how much I'm sitting and standing while working and get notified automatically if I was sitting for a too long time.

When turning on a discovery message will be sent to the MQTT. Make sure that MQTT [auto discovery](https://www.home-assistant.io/docs/mqtt/discovery/) is turned on in home assistant.

The desk controller has two RJ45 ports, one is used by the default remote of the table and the other one is unused. Both can be used to control the desk. 

## PIN Assignment
Thanks to [stan](https://www.mikrocontroller.net/user/show/stan) from this [topic](https://www.mikrocontroller.net/topic/493524). 

| PIN | Color  | Description                                                   |
|-----|--------|---------------------------------------------------------------|
| 1   | brown  | Reset of µC                                                   |
| 2   | white  | SWIN of µC                                                    |
| 3   | purple | unused                                                        |
| 4   | red    | needs to be set to HIGH if you want to talk to the controller |
| 5   | green  | RX (of remote)                                                |
| 6   | black  | TX (of remote)                                                |
| 7   | blue   | GND                                                           |
| 8   | yellow | VDD (5V)                                                      |

## Protocol
Again thanks [stan](https://www.mikrocontroller.net/user/show/stan) and _minifloat_ from this [topic](https://www.mikrocontroller.net/topic/493524). 

Each message starts with `0x9b` and ends with `0x9d`. The second byte is the message's length and the third one is the message identifier. The last two bytes before message end `0x9d` is a 16bit Modbus-CRC16 Checksum.

| 0    | 1    | 2    | 3    | 4    | 5    | 6    | 7    | 8    | Direction   | Command           |
|------|------|------|------|------|------|------|------|------|-------------|-------------------|
| `9b` | `06` | `02` | `00` | `00` | `6c` | `a1` | `9b` |      | `Tx`        | no button pressed |
| `9b` | `06` | `02` | `02` | `00` | `6c` | `a1` | `9b` |      | `Tx`        | up                |
| `9b` | `06` | `02` | `04` | `00` | `6c` | `a1` | `9b` |      | `Tx`        | down              |
| `9b` | `06` | `02` | `08` | `00` | `6c` | `a1` | `9b` |      | `Tx`        | Pos. 1            |
| `9b` | `06` | `02` | `10` | `00` | `6c` | `a1` | `9b` |      | `Tx`        | Pos. 2            |
| `9b` | `06` | `02` | `20` | `00` | `6c` | `a1` | `9b` |      | `Tx`        | Pos. 3            |
| `9b` | `07` | `12` | `xx` | `xx` | `xx` | `yy` | `yy` | `9b` | `Rx`        | Height            |
tbc

### Height
Message Identifier for the height reported by the controller is `0x12` with three bytes of payload. Every byte represents a digit on the display, every bit of each byte represents one segment of a seven segments display. See method `decode_digit(b)` or following image:

```
  0 0 0
5       1
5       1
5       1
  6 6 6
4       2
4       2
4       2
  3 3 3    77
```

## Home Assistant `configuration.xaml`
These are my custom sensors I've added to my `configuration.yaml`:

```yaml
mqtt:
    broker: <MQTT Broker>
    discovery: true

binary_sensor:
  - platform: template
    sensors:
      standing_at_desk:
        friendly_name: "Standing at desk"
        value_template: >-
            {{states('sensor.standingdesk')|float > 100}}

sensor:
  - platform: history_stats
    sensors:
      standing_today:
        name: Standing today
        entity_id: binary_sensor.standing_at_desk
        state: "on"
        type: time
        start: '{{ now().replace(hour=0, minute=0, second=0) }}'
        end: '{{ now() }}'
```

The binary sensor `standing_at_desk` switches to `on` if the reported height of the desk is higher than 100cm. This is the indicator that I'm standing right now. The sensor `standing_today` counts how long I was standing for today.

## TODO
Right now I'm using an ESP32, a RJ45 Y-adapter and an external power supply. Reading the values is only working if the original control panel is turned on. I didn't manage to read them out so far with the other RJ45 port and without the control panel. Because of that I need to leave the ESP32 powered on 24/7. I would like to develop a "standalone solution" which requests every `x` minutes the current height and goes to deep sleep in the mean time.

Since there's is also a 5V DC power supply on the RJ45 you probably won't need an external power supply. Sadly there's not enough power on one port for both, the control panel and the ESP32.