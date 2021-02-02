# HA Flexispot Standing Desk

This is an integration of a standing desk from Flexispot into home assistant in micropython. The height is read out from the desk's controller and it gets pushed to Home Assistant via MQTT. After querying the height my ESP32 goes to deep sleep for 3 minutes (you can also change this, see `main.py`).

Also remote controlling the desk is possible, but I have only implemented the basic commands so far since this is not a real use case for me. I just want to have some statistics about how much I'm sitting and standing while working and get notified automatically if I was sitting for a too long time. 

The desk controller has two RJ45 ports, one is used by the default remote of the table and the other one is unused. Both can be used to control the desk. 

## Usage and installation
I took an ESP32 and an old ethernet cable, cut it and soldered dupont wires with a female end to the Pins 4, 5, 6, 7 and 8. Pins 7 and 8 go to VIN and GND, connect 4 to `D18` of your ESP32, RX and TX to RX2/TX2.

Installation of Micropython on ESP32 is explained on this site: http://docs.micropython.org/en/latest/esp32/tutorial/intro.html#esp32-intro

For uploading the files I used [ampy](https://learn.adafruit.com/micropython-basics-load-files-and-run-code/install-ampy).

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

## PIN Assignment
Thanks to [stan](https://www.mikrocontroller.net/user/show/stan) from this [topic](https://www.mikrocontroller.net/topic/493524). 

| PIN | Color  | Description                                                     |
|-----|--------|-----------------------------------------------------------------|
| 1   | brown  | Reset of µC                                                     |
| 2   | white  | SWIN of µC                                                      |
| 3   | purple | unused                                                          |
| 4   | red    | needs to be set to `HIGH` if you want to talk to the controller |
| 5   | green  | RX (of remote)                                                  |
| 6   | black  | TX (of remote)                                                  |
| 7   | blue   | GND                                                             |
| 8   | yellow | VDD (5V)                                                        |

## Protocol
Again thanks [stan](https://www.mikrocontroller.net/user/show/stan) and _minifloat_ from this [topic](https://www.mikrocontroller.net/topic/493524). 

Each message starts with `0x9b` and ends with `0x9d`. The second byte is the message's length and the third one is the message identifier. The last two bytes before message end `0x9d` is a 16bit Modbus-CRC16 Checksum.

| 0    | 1    | 2    | 3    | 4    | 5    | 6    | 7    | 8    | Direction   | Command           |
|------|------|------|------|------|------|------|------|------|-------------|-------------------|
| `9b` | `06` | `02` | `00` | `00` | `6c` | `6c` | `a1` |      | `Tx`        | no button pressed |
| `9b` | `06` | `02` | `01` | `00` | `6c` | `fc` | `a0` |      | `Tx`        | up                |
| `9b` | `06` | `02` | `02` | `00` | `6c` | `0c` | `a0` |      | `Tx`        | down              |
| `9b` | `06` | `02` | `04` | `00` | `6c` | `ac` | `a3` |      | `Tx`        | Pos. 1            |
| `9b` | `06` | `02` | `08` | `00` | `6c` | `ac` | `a6` |      | `Tx`        | Pos. 2            |
| `9b` | `06` | `02` | `10` | `00` | `6c` | `ac` | `ac` |      | `Tx`        | Pos. 3            |
| `9b` | `06` | `02` | `20` | `00` | `6c` | `ac` | `b8` |      | `Tx`        | M                 |
| `9b` | `07` | `12` | `xx` | `xx` | `xx` | `yy` | `yy` | `9b` | `Rx`        | Height            |
tbc

### Height
If you want to query the height you have to send the "no button pressed"-command first. After that the controller will transmit the encoded height.

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

## Todos and known bugs
- [ ] As I said before I haven't implemented remote controlling from home assistant so far. Feel free to do it.
- [ ] Right now I'm querying the height 3 times in a row in `main.py`. If I only query it once the message gets probably lost. I guess this is because of the following deep sleep and the publishing of mqtt messages which is not blocking.
- [ ] The desk controller goes into some kind of sleep after some time (just like your normal control panel). Maybe we should implement some kind of timer which sets the read pin to low and high again.