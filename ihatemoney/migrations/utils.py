from alembic import op

def skip_if_sqlite(func):
    def wrapper(*args, **kwargs):      
        if op.get_bind().engine.dialect.name == 'sqlite':
            return
        else:
            return func(*args, **kwargs)
    return wrapper
