"""Non-secret runtime identity for IDE installation verification."""
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path


def fingerprint(root, patterns):
    digest = sha256()
    paths = sorted({p for pattern in patterns for p in root.glob(pattern) if p.is_file()})
    for path in paths:
        name = path.relative_to(root).as_posix().encode()
        data = path.read_bytes()
        digest.update(len(name).to_bytes(8, 'big'))
        digest.update(name)
        digest.update(len(data).to_bytes(8, 'big'))
        digest.update(data)
    return digest.hexdigest()


def identity():
    root = Path(__file__).parent
    return {'package_version': version('kobil-sdk-integration'),
            'source_sha256': fingerprint(root, ['*.py', '*.json']),
            'knowledge_sha256': fingerprint(root, ['knowledge/*.json']),
            'mobile_sdk_version': None,
            'backend_contacted': False}
