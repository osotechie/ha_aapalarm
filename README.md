# Home Assistant ArrowHead Alarm System (IP / Serial module) Custom Component

This is a custom component for ArrowHead Home Alarm System using the IP / Serial module to integrate with Home Assistant.

## Requirements:
- Hardware either of thoose are reported working
  - AAP Elite ESL-2 with ESL-2 APP POD
  - AAP Elite ESL-2
- Firmware for Ip Module or APP POD
  - `Ver 2.10.3628 2017 Oct 20 09:48:43`
  Contact AAP Support to request exact Firmware version [email](mailto:tech@aap.co.nz)

## Installation

You will need to install the ha_aapalarm manually.

### Setup
- create custom_components folder if it does not exist to get following structure\
  `config/custom_components`

#### Manual file copy
- create aapalarm folder inside custom_components folder\
  `config/custom_components/aapalarm`
- copy all files from [custom_components/aapalarm/](custom_components/aapalarm/) into the previously created folder

#### Cloning repo
- use Terminal AddOn or ssh to connect to HomeAssistant
- checkout ha_aapalarm into config directory\
  `git clone https://github.com/osotechie/ha_aapalarm`
- cd into config/custom_components folder\
  `cd config/custom_components`
- create symlink for aapalarm\
  `ln -s ../ha_aapalarm/custom_components/aapalarm aapalarm`

### Restart HomeAssistant

### Configuration

you can use the [sample configuration](sample_configuration.yaml) as a starting point

### Restart HomeAssistant

## Configuration Details
```
aapalarm:
  
  # CONFIGURATION TO CONNECT TO YOUR SYSTEM USING IP / SERIAL MODULE
  connectiontype: '<type>'                                      # STRING: Set to either 'ip' or 'serial' 
  host: xxx.xxx.xxx.xxx                                         # STRING: AAP IP Module IP Address, only include if connection type 'ip'
  port: '<5002>' or '<serial port>;                             # STRING: IP Port, or Serial Port (DEFAULT: 5002)
  keepalive_interval: 60
  timeout: 20
  
  # CONFIGURATION FOR AREAS USED BY YOUR SYSTEM
  areas:                                                        *# Include only the areas used by your system*
    1:
      name: 'Home'                                              # STRING: Update based on your system
      code: '1234'                                              # STRING: Code used to Arm / Disarm the area
      code_arm_required: False                                  # BOOLEAN: Code required to arm area (DEFAULT: True)
    2:                                                          
      name: 'Garage                                             # STRING: Update based on your system
      code: '1234'                                              # STRING: Code used to Arm / Disarm the area
      code_arm_required: False                                  # BOOLEAN: Code required to arm area (DEFAULT: True)
  
  # CONFIGURATION FOR OUTPUTS USED BY YOUR SYSTEM
  outputs:                                                      *# Include only the Outputs used by your system*
    1:                          
      name: 'Strobe'                                            # STRING: Update based on your system
    2:
      name: 'Siren'                                             # STRING: Update based on your system
    3:
      ... 
  
  # CONFIGURATION FOR ZONES USED BY YOUR SYSTEM
  zones:                                                        *# Include only the Zones used by your system*
    1:
      name: 'Entrance'                                          # STRING: Update based on your system
      type: 'motion'                                            # STRING: Set to zone sensor type (supported types are motion, door, window,smoke)
    2:
      ...
```


Based on the amazing working of [febalci](https://github.com/febalci), and customised to work more specifically with AAP systems using either the IP module or Serial module from the [pyaapalarmmodule](https://github.com/osotechie/pyaapalarmmodule) another adaptation of [febalci](https://github.com/febalci) original [pycrowipmodule](https://github.com/febalci/pycrowipmodule)