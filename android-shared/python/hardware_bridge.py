"""Public enrollment snapshot serialization; never serialize unlocked material."""
import base64
import hashlib
import json
from vault import VaultError


def describe(settings):
    if settings is None:
        raise VaultError('No YubiKey is enrolled for this account. Enroll it on desktop first, or use your password.')
    public = {k: base64.b64encode(settings[k]).decode() for k in ('credential', 'salt')}
    public.update(id=settings['id'], label=settings['label'])
    # Tie completion to all enrollment fields, including user/wrapped key. Stale
    # operations cannot switch accounts or use a replacement enrollment.
    serialized = {k: base64.b64encode(v).decode() if isinstance(v, bytes) else v for k,v in settings.items()}
    public['snapshot'] = hashlib.sha256(json.dumps(serialized,sort_keys=True).encode()).hexdigest()
    return json.dumps(public,sort_keys=True)


def current_settings(vault, username, request):
    settings = vault.yubikey_settings(username, key_id=json.loads(request).get('id'))
    if json.loads(describe(settings)) != json.loads(request):
        raise VaultError('YubiKey enrollment changed. Start again; vault was kept.')
    return settings


def response(value):
    try:
        result = base64.b64decode(value,validate=True)
        if len(result) != 32: raise ValueError()
        return result
    except Exception as e:
        raise VaultError('Invalid hardware unlocking response.') from e


def choices(vault, username=''):
    return json.dumps([json.loads(describe(s)) for s in vault.yubikey_enrollments(username)])
