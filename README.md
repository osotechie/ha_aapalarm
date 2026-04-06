<div align="center">

<img src="https://avatars.githubusercontent.com/u/34251619?v=4" align="center" width="144px" height="144px"/>

### Home Assistant - Custom Integration - ArrowHead Alarm System

[![HACS Validation](https://github.com/osotechie/ha_aapalarm/actions/workflows/validate.yml/badge.svg)](https://github.com/osotechie/ha_aapalarm/actions/workflows/validate.yml)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

</div>

---

## 📖 Overview

This is a HACS integration for ArrowHead Alarm Systems, allowing you to integrate your AAP alarm into Home Assistant, giving you access to control your alarm panel, outputs and use zone sensors in your home automations.

To use this integration with Home Assistant you must have an AAP alarm with one of the following modules to allow this integration to communicate with your alarm:

- AAP Elite ESL-2 based PCB
- AAP Elite ESL-2 IoT / APP POD [link](https://www.aap.co.nz/shop/Alarm+Systems/Modules/ESL-2+IoT.html), or
- AAP RS232-BD [link](https://www.aap.co.nz/shop/Alarm+Systems/Modules/RS232-BD.html)

<br>

> [!NOTE]
> The firmware for the APP Elite ESL-2 IOT / APP module needs to be `Ver 2.10.3628 2017 Oct 20 09:48:43`. Contact AAP Support to request exact firmware version [email](mailto:tech@aap.co.nz)

<br>

> [!WARNING]
> *This integration has not yet been tested with any newer ArrowHead Alarm System units like those powered by the EliteControl. It may work with the [EC-i RS232](https://www.aap.co.nz/shop/Alarm+Systems/Modules/EC-i+RS232.html) module.*

This is a custom component for ArrowHead Home Alarm System using the IP / Serial module to integrate with Home Assistant.


## 💽 Installation

### HACS Based Install

If you are using HACS to manage custom components in your Home Assistant installation you can easily add this repo as a custom repo in HACS using the My button.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?repository=ha_aapalarm&category=Integration&owner=OSoTechie)

  1. Confirm you wish to add the repo
  2. Click download to install the repo
  3. Restart Home Assistant
  
### Manual Install

  1. Create custom_components folder if it does not exist to get following structure\
     `config/custom_components`

  2. Create `aaplarm` folder inside the **custom_components** folder
     `config/custom_components/aapalarm`

  3. Download a copy of this repo, and copy all files from [custom_components/aapalarm/](custom_components/aapalarm/) into the previously created folder
  
  4. Restart Home Assistant 

<br>

## 🗒️Configuration
> [!NOTE]
> Starting with version 2025.10.05, this integration supports setup through the Home Assistant integrations page. You can configure the integration directly from the UI without manually editing YAML files. If you have a previous version installed you will need to remove any YAML configuration you previously had for your alarm system.

Once installed you can use the following My button to add your Alarm system to Home Assistant.

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=aapalarm)

Follow the setup wizard to configure:
   - Connection settings (IP/Serial)
   - Zones (sensors)
   - Areas (alarm partitions) 
   - Outputs (controllable devices)

<br>

## �🙌 Acknowledgements

The source code for this integration is based on the amazing work of [febalci](https://github.com/febalci), and has been adapted to more closely align with the ArrowHead Alarm System, and support both the IP and Serial modules for communicating with the alarm. Make sure to check out more of [febalci](https://github.com/febalci) work, including:

- [ha_pycrowipmodule](https://github.com/febalci/ha_pycrowipmodule) - the inspiriation for this Custom Integration for Home Assistant, using the pycrowipmodule to allow you to integrate Crow / AAP systems using the IP module
- [pycrowipmodule](https://github.com/febalci/pycrowipmodule) - the underlying python module for the ha_pycrowipmodule, allowing communication with Crow / AAP systems using the IP module