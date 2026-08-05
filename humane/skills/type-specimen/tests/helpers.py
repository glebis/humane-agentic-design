from tspec import config


def filled(**over):
    """A starter config with every slot written, so a test isolates one failure."""
    cfg = config.starter(ident="t", title="T")
    cfg["texts"].update({
        "display": "Display",
        "headline": "Headline",
        "weights": "Weights",
        "prose": "One.\nTwo.",
        "caps": "CAPS",
        "rows": "Name :: Value",
        "table": "a :: b :: c",
        "tableHead": "A :: B :: C",
    })
    cfg.update(over)
    return cfg
