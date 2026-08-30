# Karpathy Guidelines — Practical Examples

Real-world code examples demonstrating the four principles. Each example shows what LLMs commonly do wrong and how to fix it.

## 1. Think Before Coding

### Example 1: Hidden Assumptions

**User Request:** "Add a feature to export user data"

**Wrong (assumes everything silently):**
```python
def export_users(format='json'):
    """Export all users to a file."""
    users = User.query.all()
    
    if format == 'json':
        with open('users.json', 'w') as f:
            json.dump([u.to_dict() for u in users], f)
    elif format == 'csv':
        with open('users.csv', 'w') as f:
            writer = csv.DictWriter(f, fieldnames=['id', 'email', 'name'])
            writer.writeheader()
            writer.writerows([u.to_dict() for u in users])
    
    return f"Exported {len(users)} users"
```

Problems: Assumed ALL users (privacy?), assumed file location, assumed which fields, assumed CSV fieldnames.

**Right (surface assumptions first):**
```
Before implementing, I need to clarify:

1. **Scope**: Export all users or filtered subset? (privacy implications)
2. **Format**: Download file? Background job? API endpoint?
3. **Fields**: Which user fields? (some might be sensitive)
4. **Volume**: How many users typically? (affects approach)

Simplest approach: Add an API endpoint that returns paginated JSON.
What's your preference?
```

### Example 2: Multiple Interpretations

**User Request:** "Make the search faster"

**Wrong (picks one interpretation silently):**
```python
@lru_cache(maxsize=1000)
async def search(query: str) -> List[Result]:
    # ... 200 lines of optimization code
```

**Right (present options):**
```
"Make the search faster" could mean:

1. **Faster response time** (< 100ms) — add indexes, cache frequent queries
2. **Handle more concurrent searches** — add async, connection pooling
3. **Faster perceived speed** — show partial results immediately

Current search takes ~500ms. Which aspect matters most?
```

## 2. Simplicity First

### Example 1: Over-abstraction

**User Request:** "Add a function to calculate discount"

**Wrong (overengineered):**
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

class DiscountStrategy(ABC):
    @abstractmethod
    def calculate(self, amount: float) -> float:
        pass

class PercentageDiscount(DiscountStrategy):
    def __init__(self, percentage: float):
        self.percentage = percentage
    def calculate(self, amount: float) -> float:
        return amount * (self.percentage / 100)

class FixedDiscount(DiscountStrategy):
    def __init__(self, fixed_amount: float):
        self.fixed_amount = fixed_amount
    def calculate(self, amount: float) -> float:
        return min(self.fixed_amount, amount)

@dataclass
class DiscountConfig:
    strategy: DiscountStrategy
    min_purchase: float = 0.0
    max_discount: float = float('inf')

class DiscountCalculator:
    def __init__(self, config: DiscountConfig):
        self.config = config
    def apply_discount(self, amount: float) -> float:
        if amount < self.config.min_purchase:
            return 0
        discount = self.config.strategy.calculate(amount)
        return min(discount, self.config.max_discount)
```

**Right (simple):**
```python
def calculate_discount(amount: float, percent: float) -> float:
    """Calculate discount amount. percent should be 0-100."""
    return amount * (percent / 100)
```

Add complexity only when you actually need multiple discount types.

### Example 2: Speculative Features

**User Request:** "Save user preferences to database"

**Wrong (unnecessary features):**
```python
class PreferenceManager:
    def __init__(self, db, cache=None, validator=None):
        self.db = db
        self.cache = cache or InMemoryCache()
        self.validator = validator or DefaultValidator()
    
    def save(self, user_id, prefs, merge=True, validate=True, notify=False):
        if validate:
            errors = self.validator.validate(prefs)
            if errors:
                raise ValidationError(errors)
        existing = self.get(user_id) if merge else {}
        if merge:
            existing.update(prefs)
            prefs = existing
        self.db.execute("UPDATE users SET preferences = ? WHERE id = ?",
                        (json.dumps(prefs), user_id))
        if self.cache:
            self.cache.set(f"prefs:{user_id}", prefs)
        if notify:
            self.notify_preference_change(user_id, prefs)
        return True
```

**Right (just what was asked):**
```python
def save_preferences(db, user_id: int, preferences: dict):
    """Save user preferences to database."""
    db.execute("UPDATE users SET preferences = ? WHERE id = ?",
               (json.dumps(preferences), user_id))
```

## 3. Surgical Changes

### Example 1: Drive-by Refactoring

**User Request:** "Fix the bug where empty emails crash the validator"

**Wrong (too much):**
```python
  def validate_user(user_data):
-     # Check email format
-     if not user_data.get('email'):
+     """Validate user data."""
+     email = user_data.get('email', '').strip()
+     if not email:
          raise ValueError("Email required")
-     if '@' not in user_data['email']:
+     if '@' not in email or '.' not in email.split('@')[1]:
          raise ValueError("Invalid email")
-     if not user_data.get('username'):
+     username = user_data.get('username', '').strip()
+     if not username:
          raise ValueError("Username required")
+     if len(username) < 3:
+         raise ValueError("Username too short")
+     if not username.isalnum():
+         raise ValueError("Username must be alphanumeric")
      return True
```

Problems: "Improved" email validation, added username validation nobody asked for, changed comments, added docstring.

**Right (surgical):**
```python
  def validate_user(user_data):
-     if not user_data.get('email'):
+     email = user_data.get('email', '')
+     if not email or not email.strip():
          raise ValueError("Email required")
-     if '@' not in user_data['email']:
+     if '@' not in email:
          raise ValueError("Invalid email")
      if not user_data.get('username'):
          raise ValueError("Username required")
      return True
```

Only changed lines that fix the empty email handling.

### Example 2: Style Drift

**User Request:** "Add logging to the upload function"

**Wrong (reformats everything):**
```python
- def upload_file(file_path, destination):
+ def upload_file(file_path: str, destination: str) -> bool:
+     """Upload file to destination with logging."""
+     logger.info(f"Uploading {file_path} to {destination}")
      try:
-         with open(file_path, 'rb') as f:
-             data = f.read()
-         response = requests.post(destination, files={'file': data})
-         if response.status_code == 200:
-             return True
-         else:
-             return False
+         with open(file_path, "rb") as f:
+             data = f.read()
+         response = requests.post(destination, files={"file": data})
+         success = response.status_code == 200
+         if success:
+             logger.info(f"Upload successful: {file_path}")
+         else:
+             logger.error(f"Upload failed: {file_path}, status={response.status_code}")
+         return success
      except Exception as e:
-         print(f"Error: {e}")
+         logger.exception(f"Upload error for {file_path}: {e}")
          return False
```

Problems: Changed quotes, added type hints, added docstring, reformatted whitespace, changed boolean logic.

**Right (match existing style):**
```python
+ import logging
+ logger = logging.getLogger(__name__)

  def upload_file(file_path, destination):
+     logger.info(f'Starting upload: {file_path}')
      try:
          with open(file_path, 'rb') as f:
              data = f.read()
          response = requests.post(destination, files={'file': data})
          if response.status_code == 200:
+             logger.info(f'Upload successful: {file_path}')
              return True
          else:
+             logger.error(f'Upload failed: {file_path}, status={response.status_code}')
              return False
      except Exception as e:
-         print(f"Error: {e}")
+         logger.exception(f'Upload error: {file_path}')
          return False
```

Matched: Single quotes, no type hints, existing boolean pattern, spacing style.

## 4. Goal-Driven Execution

### Example 1: Vague vs. Verifiable

**User Request:** "Fix the authentication system"

**Wrong (vague approach):**
```
I'll fix the authentication system by:
1. Reviewing the code
2. Identifying issues
3. Making improvements
4. Testing the changes
```

**Right (verifiable goals):**
```
To "fix authentication," I need to define success criteria.
What specific issue are we solving?

If the issue is "users stay logged in after password change":

Plan:
1. Write test: Change password -> verify old session invalidated
   Verify: Test fails (reproduces bug)

2. Implement: Invalidate sessions on password change
   Verify: Test passes

3. Check edge cases: Multiple active sessions, concurrent changes
   Verify: Additional tests pass

4. Verify no regression: Existing auth tests still pass
   Verify: Full test suite green

What's the specific auth issue you're seeing?
```

### Example 2: Incremental with Verification

**User Request:** "Add rate limiting to the API"

**Right approach:**
```
Plan for rate limiting:

1. Add basic in-memory rate limiting (single endpoint)
   Verify:
   - Test: 100 requests -> first 10 succeed, rest get 429
   - Manual: curl endpoint 11 times, see rate limit error

2. Extract to middleware (apply to all endpoints)
   Verify:
   - Test: Rate limits apply to /users and /posts
   - Existing endpoint tests still pass

3. Add Redis backend (for multi-server)
   Verify:
   - Test: Rate limit persists across app restarts
   - Test: Two app instances share rate limit counter

4. Add configuration (rates per endpoint)
   Verify:
   - Test: /search allows 10/min, /users allows 100/min
   - Config file parsed correctly

Each step is independently verifiable and deployable.
Start with step 1?
```

### Example 3: Test-First Verification

**User Request:** "The sorting breaks when there are duplicate scores"

**Wrong (fix without reproducing):**
```python
def sort_scores(scores):
    return sorted(scores, key=lambda x: (-x['score'], x['name']))
```

**Right (reproduce first):**
```python
# 1. First, write a test that reproduces the issue
def test_sort_with_duplicate_scores():
    scores = [
        {'name': 'Alice', 'score': 100},
        {'name': 'Bob', 'score': 100},
        {'name': 'Charlie', 'score': 90},
    ]
    result = sort_scores(scores)
    assert result[0]['score'] == 100
    assert result[1]['score'] == 100
    assert result[2]['score'] == 90

# Verify: Run test 10 times -> fails with inconsistent ordering

# 2. Now fix with stable sort
def sort_scores(scores):
    return sorted(scores, key=lambda x: (-x['score'], x['name']))

# Verify: Test passes consistently
```

---

## Anti-Patterns Summary

| Principle | Anti-Pattern | Fix |
|-----------|-------------|-----|
| Think Before Coding | Silently assumes file format, fields, scope | List assumptions explicitly, ask for clarification |
| Simplicity First | Strategy pattern for single discount calculation | One function until complexity is actually needed |
| Surgical Changes | Reformats quotes, adds type hints while fixing bug | Only change lines that fix the reported issue |
| Goal-Driven | "I'll review and improve the code" | "Write test for bug X -> make it pass -> verify no regressions" |

**Key Insight:** The "overcomplicated" examples follow design patterns and best practices. The problem is timing — they add complexity before it's needed, making code harder to understand, introducing more bugs, and taking longer to implement. Good code solves today's problem simply, not tomorrow's problem prematurely.
