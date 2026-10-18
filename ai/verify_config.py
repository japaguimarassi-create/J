import json
from ai.config import ModelConfig, estimate_parameters


def main():
    config = ModelConfig.from_json("ai/config.json")
    count = estimate_parameters(config)
    result = {
        "parameters": count,
        "target": 10046763008,
        "matches_target": count == 10046763008,
        "config": config.to_dict(),
    }
    print(json.dumps(result, indent=2))
    if not result["matches_target"]:
        raise SystemExit("Model parameter count does not match the configured target")


if __name__ == "__main__":
    main()
