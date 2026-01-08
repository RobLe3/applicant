from modules.adapters.linkedin import LinkedinAdapter
from modules.adapters.stepstone import StepstoneAdapter
from modules.adapters.rss import RssAdapter


ADAPTERS = {
    "stepstone": StepstoneAdapter,
    "linkedin": LinkedinAdapter,
    "rss": RssAdapter,
}


def get_enabled_adapters(config, logs_dir=None):
    registry = config.get("adapters", {}) or {}
    enabled = []
    for name, adapter_cls in ADAPTERS.items():
        cfg = registry.get(name) or {}
        adapter = adapter_cls(cfg, logs_dir=logs_dir)
        if adapter.enabled():
            enabled.append(adapter)
    return enabled
