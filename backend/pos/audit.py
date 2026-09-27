import threading
from .models import AuditLog


_local = threading.local()


def set_current_user(user):
    _local.user = user


def get_current_user():
    return getattr(_local, 'user', None)


def clear_current_user():
    if hasattr(_local, 'user'):
        del _local.user


def log_action(user, action, target_type='', target_id=None, details=None):
    try:
        AuditLog.objects.create(
            user=user if user and user.is_authenticated else None,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details or {},
        )
    except Exception as e:
        print(f'Audit log greška: {e}')