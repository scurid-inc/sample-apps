from pathlib import Path
import os
import yaml

def get_config_path():
    env_path = os.environ.get("SCURID_CONFIG")
    if env_path:
        return Path(env_path)

    project_root = Path(__file__).resolve()
    for parent in project_root.parents:
        if (parent / "agent" / "store" / "config.yaml").exists():
            return parent / "agent" / "store" / "config.yaml"

    return None


def load_did():
    try:
        config_path = get_config_path()
        if config_path is None or not config_path.exists():
            return None

        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        if not isinstance(config, dict):
            return None

        did = config.get("DID")
        if not did:
            return None

        return did

    except Exception as e:
        print("Could not load DID:", e)
        return None