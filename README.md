## fink kn bot

```
                ______________         ______________________________
               /       /     /        /     /                 /     /
              /       /     /        /     /     ____________/     /
             /       /     /  _____ /     /     /_____      /     /
    ________/       /     /__/    _/     /            \    /     /   ______
   /               /     /      _//     /_________     \  /     /   /     /
  /               /           _/ /     /___       \     \/     /___/     /_____
 /               /          _/  /     /    |      /     /                     /
/               /           \  /     /\     \____/     /_________       _ ___/
\              /      /\     \/     /  \              /         /      /
 \____________/______/  \_____\____/    \____________/         /______/
```

clone, cd, and install requiremets:
python3 -m pip install -r requirements.

for now, install as developer - ie.
`python3 -m pip install -e .`

get `fink_credenials.yaml`, `telegram_admin.yaml`, `telegram_users.yaml`
and put them in ./config/ - get either from aidan, or sign up to fink-client.

modify `./config/alert_polling` - perhaps you want to change the topic, or the sleep time between listen events.

add your telegram userID to telegram_users (and optionally telegram_sudoers.)

then do `python3 dk_kn_targets/main.py`

send the `/start` command to dk154-kilonova-bot in telegram.

wait for messages!
