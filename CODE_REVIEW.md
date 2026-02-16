# Code Review Summary - Shortcut Robot Bot

**Date**: 2026-02-16
**Reviewer**: Claude Code
**Status**: ⚠️ Requires attention

## Critical Issues to Fix Immediately

### 1. Fix Detached ORM Objects (models.py)
```python
# BEFORE (BROKEN)
def get_shortcuts(telegram_user_id):
    with Session() as session:
        user = session.query(User).filter_by(telegram_user_id=telegram_user_id).first()
        shortcuts = user.shortcuts if user else []
        return shortcuts  # Detached objects!

# AFTER (FIXED)
def get_shortcuts(telegram_user_id):
    with Session() as session:
        shortcuts = session.query(Shortcut).filter_by(
            telegram_user_id=telegram_user_id
        ).all()
        # Detach from session before returning
        session.expunge_all()
        return shortcuts
```

### 2. Fix Inline Handler Exception (bot.py:239-245)
```python
# BEFORE (BROKEN)
try:
    r = get_input_content(shortcut)
except JSONDecodeError as e:
    logging.error(shortcut.content_type)
    logging.error(shortcut.content)
    logging.error(format_exc())
results.append(r)  # r undefined if exception!

# AFTER (FIXED)
try:
    r = get_input_content(shortcut)
    results.append(r)
except JSONDecodeError as e:
    logging.error(f"Failed to process shortcut {shortcut.id}: {format_exc()}")
    # Skip this shortcut
    continue
```

### 3. Fix telegram_id Bug (bot.py:153)
```python
# BEFORE (BROKEN)
context['telegram_id'] = message.from_user.id

# AFTER (FIXED)
context['telegram_user_id'] = message.from_user.id
```

## Security Improvements

### Remove Token from Systemd Service
```bash
# Edit /etc/systemd/system/cardholder.service
# Remove line: Environment="TGTOKEN=..."
# Token should only be in .env file
```

### Add Environment Variable Validation
```python
# Add to bot.py startup
required_vars = ['TGTOKEN', 'LOGPATH', 'DATABASE_URL', 'LOG_CHAT_ID']
missing = [var for var in required_vars if not getenv(var)]
if missing:
    raise ValueError(f"Missing required environment variables: {missing}")
```

## Performance Improvements

### Add Database Connection Pooling
```python
# models.py
engine = create_engine(
    getenv('DATABASE_URL'),
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600    # Recycle connections every hour
)
```

### Add Log Rotation
```python
# bot.py
from logging.handlers import RotatingFileHandler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        RotatingFileHandler(
            log_file_path,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        ),
        logging.StreamHandler()
    ]
)
```

## Code Quality Improvements

### Update Shebang
```python
# bot.py line 1
#!/usr/bin/env python3
# OR
#!/home/admin/envs/shortcut-env/bin/python3
```

### Remove Unused Imports
```python
# bot.py - Remove these:
from time import sleep
from requests import post, get
from random import randint
```

### Fix Escape Sequences
```python
# bot.py:121 - Use raw string
msg = bot.reply_to(
    message=message,
    text=r'''Send me any one message you want. It can be...''',
    parse_mode='MarkdownV2'
)
```

## Testing Recommendations

1. Add unit tests for models.py functions
2. Add integration tests for bot handlers
3. Add test for duplicate shortcut detection
4. Test error handling paths

## Documentation Needs

1. Add README with setup instructions
2. Document all environment variables
3. Add API documentation for models
4. Create troubleshooting guide

## Next Steps

1. ✅ Fix critical bugs (3 issues)
2. ⬜ Implement security improvements
3. ⬜ Add database connection pooling
4. ⬜ Implement log rotation
5. ⬜ Remove unused imports
6. ⬜ Add type hints
7. ⬜ Write unit tests
