# How to Get Your Correct Supabase Connection String

## Steps to Find Your Database Connection String:

1. **Go to your Supabase Dashboard**
   - Visit: https://app.supabase.com/project/quprtbkdpujtjadpathz

2. **Navigate to Settings → Database**
   - Click on "Settings" in the left sidebar
   - Then click on "Database"

3. **Find the Connection String**
   - Look for "Connection string" section
   - You'll see a dropdown with options:
     - URI (Session mode)
     - URI (Transaction mode) - This is for pooled connections
     - PSQL
     - .NET
     - etc.

4. **Copy the Correct URLs**
   
   For **Direct Connection** (Session mode):
   - Select "URI" from the dropdown
   - Copy the string that looks like:
     ```
     postgresql://postgres.[your-project-ref]:[your-password]@aws-0-[region].pooler.supabase.com:5432/postgres
     ```
   
   For **Pooled Connection** (Transaction mode):
   - Select "URI (Transaction mode)" from the dropdown  
   - Copy the string that looks like:
     ```
     postgresql://postgres.[your-project-ref]:[your-password]@aws-0-[region].pooler.supabase.com:6543/postgres?pgbouncer=true
     ```

## Common Hostname Patterns:

Supabase recently changed their hostname format. Your connection string should look like one of these:

### New Format (AWS-based):
```
aws-0-[region].pooler.supabase.com
```
Example: `aws-0-us-east-1.pooler.supabase.com`

### Old Format (might still work):
```
db.[project-ref].supabase.co
```

## What Your .env Should Look Like:

```env
# Direct connection (port 5432)
DATABASE_URL=postgresql://postgres.[your-project-ref]:[your-password]@aws-0-[region].pooler.supabase.com:5432/postgres

# Pooled connection (port 6543)
DATABASE_POOL_URL=postgresql://postgres.[your-project-ref]:[your-password]@aws-0-[region].pooler.supabase.com:6543/postgres?pgbouncer=true
```

## Alternative: Using Supabase Client

If you're having trouble with direct PostgreSQL connections, you can also use the Supabase JavaScript/Python client which uses the REST API:

```python
from supabase import create_client

url = "https://quprtbkdpujtjadpathz.supabase.co"
key = "your-service-key"
supabase = create_client(url, key)
```

## Troubleshooting:

1. **Check if your IP is allowed**:
   - In Supabase Dashboard → Settings → Database
   - Look for "Connection pooling" section
   - Make sure "Allow all incoming connections" is enabled
   - Or add your IP address to the allow list

2. **Verify the password**:
   - The password in the connection string might have changed
   - You can reset it in Settings → Database → Database password

3. **Check project status**:
   - Make sure your project is not paused (free tier projects pause after 7 days of inactivity)