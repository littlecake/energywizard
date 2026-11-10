"""Inspect and safely replace existing solar sensor scalars in house configuration."""
import re
import yaml

_FIELDS = ('pv_power_w', 'today_kwh')
_ENTITY = re.compile(r'sensor\.[a-z0-9_]+\Z')


def _field_nodes(text):
    try:
        root = yaml.compose(text)
    except yaml.YAMLError as exc:
        raise ValueError("Invalid configuration") from exc
    def child(node, key):
        if not isinstance(node, yaml.MappingNode):
            raise ValueError('Unsupported configuration structure')
        matches = [v for k, v in node.value if isinstance(k, yaml.ScalarNode) and k.value == key]
        if len(matches) != 1:
            raise ValueError('Missing or duplicate configuration field')
        return matches[0]
    solar = child(root, 'solar')
    entities = child(solar, 'entities')
    result = {key: child(entities, key) for key in _FIELDS}
    if any(not isinstance(v, yaml.ScalarNode) or not _ENTITY.fullmatch(v.value) for v in result.values()):
        raise ValueError('Solar configuration does not contain simple sensor IDs')
    return result


def inspect(text):
    return {k: v.value for k, v in _field_nodes(text).items()}


def replace(text, expected, selected):
    nodes = _field_nodes(text)
    if set(expected) != set(_FIELDS) or set(selected) != set(_FIELDS):
        raise ValueError('Both sensor fields are required')
    if any(nodes[k].value != expected[k] for k in _FIELDS):
        raise ValueError('Solar configuration changed')
    if any(not isinstance(selected[k], str) or not _ENTITY.fullmatch(selected[k]) for k in _FIELDS):
        raise ValueError('Invalid sensor entity')
    for node, value in sorted(((nodes[k], selected[k]) for k in _FIELDS), key=lambda x: x[0].start_mark.index, reverse=True):
        text = text[:node.start_mark.index] + value + text[node.end_mark.index:]
    return text
