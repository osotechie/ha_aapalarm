<div align="center">

<img src="https://avatars.githubusercontent.com/u/34251619?v=4" align="center" width="144px" height="144px"/>

### Home Assistant - Custom Integration - Arrowhead Alarm System

</div>

---

## 📖 Overview

This is a HACS integration for Arrowhead Alarm Systems, allowing you to integrate your AAP alarm into Home Assistant, giving you access to control your alarm panel, outputs and use zone sensors in your home automations.

To use this integration with Home Assistant you must have an AAP alarm with one of the following modules to allow this integration to communicate with your alarm:

- AAP Elite ESL-2 based PCB
- AAP Elite ESL-2 IoT / APP POD [link](https://www.aap.co.nz/shop/Alarm+Systems/Modules/ESL-2+IoT.html), or
- AAP RS232-BD [link](https://www.aap.co.nz/shop/Alarm+Systems/Modules/RS232-BD.html)

<br>

> [!NOTE]
> The firmware for the APP Elite ESL-2 IOT / APP module needs to be `Ver 2.10.3628 2017 Oct 20 09:48:43`. Contact AAP Support to request exact firmware version [email](mailto:tech@aap.co.nz)

<br>

> [!WARNING]
> *This integration has not yet been tested with any newer Arrowhead Alarm System units like those powered by the EliteControl. It may work with the [EC-i RS232](https://www.aap.co.nz/shop/Alarm+Systems/Modules/EC-i+RS232.html) module.*

This is a custom component for Arrowhead Home Alarm System using the IP / Serial module to integrate with Home Assistant.


## 💽 Installation

### HACS Based Install

If you are using HACS to manage custom components in your Home Assistant installation you can easily add this repo as a custom repo in HACS.

  1. Navigate to the **HACS** console within **Home Assistant**
  2. Click the **3 dots** in the upper right corner
  3. Select **Custom repositories**
  4. Use the below information to add this repo to HACS
   
      - Repository:   `https://github.com/osotechie/ha_aapalarm`
      - Type:         `integration`
  
  5. Restart Home Assistant
  
### Manual Install

  1. Create custom_components folder if it does not exist to get following structure\
     `config/custom_components`

  2. Create `aaplarm` folder inside the **custom_components** folder
     `config/custom_components/aapalarm`

  3. Download a copy of this repo, and copy all files from [custom_components/aapalarm/](custom_components/aapalarm/) into the previously created folder
  
  4. Restart Home Assistant 

<br>

## 🗒️Configuration

Below is an example of the configuration you need to add to your Home Assistant `Configuration.yaml` file.

```
aapalarm:
  
  # CONFIGURATION TO CONNECT TO YOUR SYSTEM USING IP / SERIAL MODULE
  connectiontype: '<type>'                                      # STRING: Set to either 'ip' or 'serial' 
  host: xxx.xxx.xxx.xxx                                         # STRING: AAP IP Module IP Address, only include if connection type 'ip'
  port: '<5002>' or '<serial port>;                             # STRING: IP Port, or Serial Port (DEFAULT: 5002)
  keepalive_interval: 60
  timeout: 20
  
  # CONFIGURATION FOR AREAS USED BY YOUR SYSTEM
  areas:                                                        # Include only the areas used by your system
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
  zones:                                                        # Include only the Zones used by your system
    1:
      name: 'Entrance'                                          # STRING: Update based on your system
      type: 'motion'                                            # STRING: Set to zone sensor type (supported types are motion, door, window,smoke)
    2:
      ...
```

There is also sample configuration files included in this repo for additional help configuring this integration.
- [sample_configuration_ip.yaml](sample_configuration_ip.yaml)
- [sample_configuration_serial.yaml](sample_configuration_serial.yaml)

<br>

## 🙌 Acknowledgements

The source code for this integration is based on the amazing work of [febalci](https://github.com/febalci), and has been adapted to more closely align with the ArrowHead Alarm System, and support both the IP and Serial modules for communicating with the alarm. Make sure to check out more of [febalci](https://github.com/febalci) work, including:

- [ha_pycrowipmodule](https://github.com/febalci/ha_pycrowipmodule) - the inspiriation for this Custom Integration for Home Assistant, using the pycrowipmodule to allow you to integrate Crow / AAP systems using the IP module
- [pycrowipmodule](https://github.com/febalci/pycrowipmodule) - the underlying python module for the ha_pycrowipmodule, allowing communication with Crow / AAP systems using the IP module