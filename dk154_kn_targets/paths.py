import os
import sys
from pathlib import Path

base_path = Path(__file__).absolute().parent.parent

config_path = base_path / "config"
plot_path = base_path / "plots"
alertDB_path = base_path / "alertDB"



def config_check():
    important_configs = [
        "fink_credentials.yaml", "telegram_admin.yaml", "telegram_users.yaml"
    ]

    for config in important_configs:
        missing = 0
        tx, ty = os.get_terminal_size()
        if not (config_path / config).exists():
            if missing == 0:
                print(tx * "#")
            print("#" + (tx-2) * " " + "#")
            missing_config_lines = [
                f"there is no config file {config}",
                f"you should add it to 'config/{config}'"
            ]
            missing = missing + 1
            for line in missing_config_lines:
                print("# " + (tx-6-len(line))//2*" " + " " + line+ " " + (tx-6-len(line))//2*" " + " #")
            
            print("#" + (tx-2) * " " + "#")
    if missing > 0:
        print(tx * "#"+"\n")
        print("ask aidan. exiting\n")
        sys.exit()

def create_all_paths():
    plot_path.mkdir(exist_ok=True, parents=True)
    alertDB_path.mkdir(exist_ok=True, parent=True)