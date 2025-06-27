# Pydantic V2 Migration Explanation

## What We Changed

We successfully migrated from Pydantic V1-style validators to V2-style validators to ensure our code is future-proof and follows current best practices.

## Key Changes Made

### 1. Import Changes
**Before (V1):**
```python
from pydantic import BaseModel, Field, validator
```

**After (V2):**
```python
from pydantic import BaseModel, Field, field_validator, ValidationInfo
```

### 2. Decorator Changes
**Before (V1):**
```python
@validator("field_name")
def validate_field(cls, v, field):
    # Access field name via field.name
    return v
```

**After (V2):**
```python
@field_validator("field_name")
def validate_field(cls, v, info):
    # Access field name via info.field_name
    return v
```

### 3. Accessing Field Information
**Before (V1):**
- `field.name` - Get the field name
- `values` - Dictionary of other field values

**After (V2):**
- `info.field_name` - Get the field name  
- `info.data` - Dictionary of other field values (when needed)

## Why This Migration Matters

### 1. **Future Compatibility**
Pydantic V1-style validators are deprecated in V2 and will be completely removed in V3. By migrating now, we avoid breaking changes later.

### 2. **Performance**
Pydantic V2 is significantly faster than V1, with performance improvements of 5-50x in many cases.

### 3. **Better Error Messages**
V2 provides clearer, more helpful validation error messages out of the box.

### 4. **Type Safety**
V2 has better type inference and stricter type checking, catching more errors at development time.

## Common Migration Patterns

### Simple Field Validation
```python
# V1
@validator("api_key")
def validate_api_key(cls, v):
    if len(v) < 20:
        raise ValueError("API key too short")
    return v

# V2
@field_validator("api_key")
def validate_api_key(cls, v):
    if len(v) < 20:
        raise ValueError("API key too short")
    return v
```

### Accessing Field Name
```python
# V1
@validator("api_key")
def validate_api_key(cls, v, field):
    if not v:
        raise ValueError(f"{field.name} is required")
    return v

# V2
@field_validator("api_key")
def validate_api_key(cls, v, info):
    if not v:
        raise ValueError(f"{info.field_name} is required")
    return v
```

### Multiple Field Validation
```python
# V1
@validator("field1", "field2")
def validate_fields(cls, v, field):
    # Validates both fields
    return v

# V2
@field_validator("field1", "field2")
def validate_fields(cls, v, info):
    # Validates both fields
    return v
```

## Gotchas and Important Notes

### 1. **Can't Modify Other Fields**
In V1, you could modify the `values` dict to set other fields. In V2, validators should only validate and transform their own field.

### 2. **Order of Execution**
Field validators run in the order fields are defined in the model, not the order validators are defined.

### 3. **Mode Parameter**
V2 introduces validation modes (`before`, `after`, `wrap`). We use the default `after` mode which validates after Pydantic's built-in validation.

### 4. **Return Value**
Always return the validated/transformed value. Returning `None` will set the field to `None`.

## Testing Considerations

When testing V2 validators:
1. Use `_env_file=None` when creating config instances to prevent loading .env files
2. Mock environment variables with `monkeypatch.setenv()`
3. Check specific error messages and field names in validation errors

## Benefits We Gained

1. **No More Deprecation Warnings**: Clean output when running the application
2. **Better IDE Support**: V2 has better type hints and autocomplete
3. **Improved Performance**: Faster startup and validation
4. **Future-Proof**: Ready for Pydantic V3 when it releases

## Resources for Learning More

- [Pydantic V2 Migration Guide](https://docs.pydantic.dev/latest/migration/)
- [Pydantic V2 Validators Documentation](https://docs.pydantic.dev/latest/concepts/validators/)
- [Pydantic V2 Performance](https://docs.pydantic.dev/latest/concepts/performance/)

What questions do you have about the migration, Finn?