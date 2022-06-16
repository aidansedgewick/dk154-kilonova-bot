## fink kn bot

```
                ______________          ______________________________
               /       /     /         /     /                 /     /
              /       /     /         /     /     ____________/     /
             /       /     /  ______ /     /     /_____      /     /
    ________/       /     /__/    _//     /            \    /     /   ______
   /               /     /      _/ /     /_________     \  /     /   /     /
  /    ____       /           _/  /     /___       \     \/     /___/     /____
 /    /   /      /          _/   /     /    |      /     /                    /
/     \__/      /           \   /     /\     \____/     /_________       ____/
\              /      /\     \ /     /  \              /         /      /
 \____________/______/  \_____\_____/    \____________/         /______/
```

clone, cd, and install requiremets:
python3 -m pip install -r requirements.

for now, install as developer - ie.
`python3 -m pip install -e .`

get fink_credenials.yaml, telegram_admin.yaml, telegram_users.yaml
and put them in ./config/

add your telegram userID to telegram_users (and optionally telegram_sudoers.)

then do `python3 dk_kn_targets/main.py`

send the `/start` command to dk154-kilonova-bot in telegram.

wait for messages!
