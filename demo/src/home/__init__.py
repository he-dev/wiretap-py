import os

import pathlib
import sys

import yaml

# project_root = pathlib.Path(__file__).resolve().parents[3]
# wiretap_src = project_root / "wiretap" / "src"
# sys.path.insert(0, str(wiretap_src))

import wiretap  # pip install -e ./wiretap
from use_cases import *

#print(wiretap.__file__)
#print(*sys.path, sep="\n")


if __name__ == "__main__":
    # asyncio.run(main())
    # main_proc()

    os.environ["app_id"] = "demo-app"
    app_root = pathlib.Path(__file__).resolve().parent

    with open(r"..\..\cfg\wiretap.yml", "r") as file:
        config = yaml.safe_load(file)
        # config["handlers"]["elastic_file"]["filename"] = rf"c:\temp\elastic-v8.0.0-{datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')}.log"

        wiretap.configure(config)

    # demo()
    log_v13()
