# Chat With Database

## 🎯 Overview
This is a production-ready AI-powered database query assistant that dynamically extracts and uses your PostgreSQL database schema.

## ✨ Key Features

### 1. **Dynamic Schema Extraction**
- Automatically extracts complete database schema at runtime
- No need to manually update schema definitions
- Works with databases of any size

### 2. **Intelligent Caching**
- Schema is cached for 60 minutes (configurable)
- Reduces database load
- Option to force refresh when needed

### 3. **Security First**
- Uses read-only database user
- Only SELECT queries allowed
- Query timeout protection
- Result row limits

### 4. **Production Features**
- Environment-based configuration
- Error handling and logging
- Connection pooling ready
- Session state management

## 📁 Project Structure

```
AI_Database_Engineer/
├── main.py                 # production-ready main application
├── schema_agent.py         # Schema extraction and management agent
├── config.py               # Configuration management
├── .env.example            # Environment variables template
├── .env                    # Your actual credentials (create this)
├── requirements.txt        # Python dependencies
└── README_NEW.md          # This file
```

## 🚀 Setup Instructions

### Step 1: Update Your `.env` File

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:
```env
GEMINI_API_KEY=your_actual_gemini_api_key

DB_HOST=localhost
DB_NAME=your_database_name
DB_USER=your_readonly_user
DB_PASSWORD=your_password
DB_PORT=5432

SCHEMA_CACHE_DURATION_MINUTES=60
```

### Step 2: Create Read-Only PostgreSQL User (IMPORTANT)

Connect to your PostgreSQL as superuser and run:

```sql
-- Create read-only user
CREATE USER readonly_user WITH PASSWORD 'secure_password';

-- Grant connection to database
GRANT CONNECT ON DATABASE your_database_name TO readonly_user;

-- Grant usage on schema
GRANT USAGE ON SCHEMA public TO readonly_user;

-- Grant SELECT on all existing tables
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;

-- Grant SELECT on future tables (important!)
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
GRANT SELECT ON TABLES TO readonly_user;

-- Allow reading table metadata (for schema extraction)
GRANT SELECT ON information_schema.tables TO readonly_user;
GRANT SELECT ON information_schema.columns TO readonly_user;
GRANT SELECT ON information_schema.table_constraints TO readonly_user;
GRANT SELECT ON information_schema.key_column_usage TO readonly_user;
GRANT SELECT ON information_schema.constraint_column_usage TO readonly_user;
```

Update your `.env` file with this user:
```env
DB_USER=readonly_user
DB_PASSWORD=secure_password
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Run the Application

```bash
streamlit run main.py
```

## 🔧 How It Works

### Architecture Flow

```
User Query → Streamlit UI → Schema Agent (extracts schema) → 
Gemini AI (generates SQL) → PostgreSQL (executes) → Results Display
```

### Schema Agent Process

1. **On First Load**: 
   - Connects to PostgreSQL using read-only user
   - Extracts all tables, columns, data types, constraints, foreign keys
   - Generates optimized schema text for LLM
   - Caches result in memory

2. **Subsequent Requests**:
   - Uses cached schema (valid for 60 minutes)
   - No database queries needed
   - Fast response time

3. **Refresh Options**:
   - Automatic refresh after cache expiry
   - Manual refresh button in sidebar
   - Force refresh via API

### Query Processing

1. User enters natural language query
2. Schema + Rules + Memory sent to Gemini AI
3. AI decides mode (SQL or CHAT)
4. For SQL mode:
   - Generates PostgreSQL-compatible query
   - Validates (SELECT only)
   - Executes with timeout protection
   - Returns results with explanation

## 🔒 Security Features

1. **Read-Only Access**: Only SELECT queries allowed
2. **Query Validation**: Blocks INSERT, UPDATE, DELETE, DROP
3. **Timeout Protection**: Queries timeout after 30s (configurable)
4. **Result Limits**: Maximum 1000 rows (configurable)
5. **Environment Variables**: Credentials not in code
6. **SQL Injection Protection**: Using psycopg2 parameterized queries

## ⚙️ Configuration Options

Edit `.env` to customize:

```env
# Schema cache duration (in minutes)
SCHEMA_CACHE_DURATION_MINUTES=60

# Maximum rows to return
MAX_RESULT_ROWS=1000

# Query timeout (in seconds)
QUERY_TIMEOUT_SECONDS=30

# Memory rounds (conversation history)
MAX_MEMORY_ROUNDS=5
```

## 📊 Using the Application

### Sidebar Features
- **Total Tables**: Shows number of tables in database
- **Last Extracted**: Timestamp of schema extraction
- **View Full Schema**: Expandable schema view
- **Refresh Schema**: Force reload from database
- **Save Schema**: Export schema to JSON file

### Query Examples

1. **Simple Query**:
   ```
   Show me all customers created this month
   ```

2. **Complex Query**:
   ```
   Show top 10 customers by lifetime points with their city names
   ```

3. **Analytics Query**:
   ```
   How many rewards were redeemed in the last 30 days?
   ```

4. **Chat Mode**:
   ```
   Hello, what can you help me with?
   ```

## 🐛 Troubleshooting

### Issue: "Permission denied for table"
**Solution**: Make sure read-only user has SELECT permission on all tables (see Step 2)

### Issue: "Schema not loading"
**Solution**: Check database credentials in `.env` and ensure read-only user can access `information_schema`

### Issue: "Query timeout"
**Solution**: Increase `QUERY_TIMEOUT_SECONDS` in `.env` or optimize your query

### Issue: "Too many rows"
**Solution**: Increase `MAX_RESULT_ROWS` or add LIMIT to your query

## 🚀 Migration from Old Version

To migrate from `main.py` to `main_v2.py`:

1. ✅ Create `.env` file with your credentials
2. ✅ Create read-only PostgreSQL user
3. ✅ Test connection: `python -c "from config import Config; Config.validate()"`
4. ✅ Run new version: `streamlit run main_v2.py`
5. ✅ Verify schema extraction works
6. ✅ Test few queries
7. ✅ Rename `main.py` to `main_old.py` (backup)
8. ✅ Rename `main_v2.py` to `main.py` (production)

## 📈 Performance Tips

1. **Large Databases**: Schema extraction takes 2-10 seconds initially, then cached
2. **Cache Duration**: Set to 60+ minutes in production to reduce load
3. **Query Optimization**: AI learns from previous queries in memory
4. **Result Limits**: Lower `MAX_RESULT_ROWS` for faster response

## 🔮 Future Enhancements

- [ ] Table-specific schema loading (for very large DBs)
- [ ] Query history and favorites
- [ ] Export results to CSV/Excel
- [ ] Query performance analytics
- [ ] Multi-database support
- [ ] Custom LLM model selection
- [ ] Real-time schema change detection

## 📝 Notes for Production

1. **Database User**: Always use read-only user in production
2. **API Keys**: Never commit `.env` file to git
3. **Error Logging**: Consider adding proper logging (e.g., loguru)
4. **Monitoring**: Add query performance monitoring
5. **Rate Limiting**: Consider rate limiting for Gemini API
6. **Backup**: Keep `main.py` as backup during transition

## 🤝 Support

If you encounter issues:
1. Check `.env` configuration
2. Verify database user permissions
3. Check Gemini API key validity
4. Review error messages in Streamlit UI

---

**Built with ❤️ by I'mSRJ | Powered by Gemini AI & PostgreSQL**
