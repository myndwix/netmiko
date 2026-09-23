# netmiko

Scripts for pulling show/config output from Cisco and Huawei switches over
SSH via [netmiko](https://github.com/ktbyers/netmiko), in parallel, using
credentials and commands read from YAML config files.

## Install

```bash
git clone https://github.com/myndwix/netmiko.git
cd netmiko
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

Edit `cisco_inventory.yaml` / `huawei_inventory.yaml` with your device list,
and `cisco_tacacs_config.yaml` / `hwtacacs_config.yaml` with credentials and
the commands to run, then:

```bash
python show_cisco_tacacs.py
python show_hwtacacs.py
```

Options (both scripts):

```bash
python show_cisco_tacacs.py --save-dir output
python show_cisco_tacacs.py --inventory hosts.yaml --workers 10
python show_cisco_tacacs.py --config other_creds.yaml
```
