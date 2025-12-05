import streamlit as st
import psycopg2
import pandas as pd
import google.generativeai as genai
from config import Config
from schema_agent import SchemaAgent

# Validate and load configuration
Config.validate()
genai.configure(api_key=Config.GEMINI_API_KEY)

# ----------------------------------------------------
# DATABASE CONNECTION
# ----------------------------------------------------
def connect_db():
    """Create database connection using configuration."""
    return psycopg2.connect(
        host=Config.DB_CONFIG['host'],
        database=Config.DB_CONFIG['database'],
        user=Config.DB_CONFIG['user'],
        password=Config.DB_CONFIG['password'],
        port=Config.DB_CONFIG['port']
    )

# ----------------------------------------------------
# SCHEMA AGENT INITIALIZATION
# ----------------------------------------------------
@st.cache_resource
def get_schema_agent():
    """
    Initialize and cache the Schema Agent.
    This ensures schema is only extracted once per session.
    """
    agent = SchemaAgent(
        db_config=Config.get_db_config(),
        cache_duration_minutes=Config.SCHEMA_CACHE_DURATION_MINUTES
    )
    return agent

# ----------------------------------------------------
# MEMORY MANAGEMENT
# ----------------------------------------------------
if "memory" not in st.session_state:
    st.session_state.memory = []

def add_memory(user, mode, content):
    """Add interaction to conversation memory."""
    st.session_state.memory.append({
        "user": user,
        "mode": mode,
        "content": content
    })
    # Keep only last N rounds
    st.session_state.memory = st.session_state.memory[-Config.MAX_MEMORY_ROUNDS:]

def display_memory():
    """Format memory for display and LLM context."""
    text = ""
    for m in st.session_state.memory:
        text += f"\nUser: {m['user']}\nMode: {m['mode']}\nBot: {m['content']}\n"
    return text

# ----------------------------------------------------
# SAFE TEXT ACCESSOR
# ----------------------------------------------------
def safe_text(resp):
    """Safely extract text from Gemini response."""
    try:
        if (
            resp and resp.candidates and
            resp.candidates[0].content and
            resp.candidates[0].content.parts
        ):
            return resp.text.strip()
        return None
    except:
        return None

# ----------------------------------------------------
# SQL GENERATION RULES
# ----------------------------------------------------
SQL_GENERATION_RULES = """
Rules for SQL Query Generation:
1. CRITICAL: Generate queries for PostgreSQL 15.x or later syntax only
2. IMPORTANT: Understand the database structure from the schema above
3. Tables have foreign key relations - be careful with JOINs
4. Return ONLY raw SQL - NO backticks, NO markdown, NO explanations, NO formatting
5. Do NOT wrap SQL inside ```sql blocks```
6. Output only the SQL query itself

Query Guidelines:
- Only SELECT queries are allowed (read-only access)
- Use LOWER() for case-insensitive string matching
- Use PostgreSQL date arithmetic: CURRENT_DATE - INTERVAL 'X UNIT'
- Never hallucinate columns that don't exist in schema
- Never alter table structure
- Optimize queries for performance
- Learn from previous mistakes in conversation memory

Output Modes:
MODE: SQL   → When user wants to search, query, or analyze data
MODE: CHAT  → When user is greeting, asking general questions

Format your response as:
MODE: SQL
<SQL QUERY>

or

MODE: CHAT
<chat reply>

For CHAT mode:
- Be friendly and helpful
- You are "John", an AI Database Assistant built by I'mSRJ
- Provide natural, conversational responses
"""

# ----------------------------------------------------
# STREAMLIT UI
# ----------------------------------------------------
st.set_page_config(
    page_title=Config.APP_TITLE,
    layout="centered",
    initial_sidebar_state="expanded"
)
st.title(f"🤖 {Config.APP_TITLE}")

# Sidebar for schema information
with st.sidebar:
    st.header("📊 Database Schema")
    
    # Initialize schema agent
    schema_agent = get_schema_agent()
    
    # Schema refresh button
    if st.button("🔄 Refresh Schema", help="Force reload database schema"):
        with st.spinner("Extracting schema from database..."):
            schema_agent.clear_cache()
            schema_text = schema_agent.get_schema_for_llm(force_refresh=True)
            st.success("Schema refreshed!")
    
    # Load schema (cached)
    with st.spinner("Loading database schema..."):
        schema_text = schema_agent.get_schema_for_llm()
    
    # Display schema information
    if schema_agent.schema_cache:
        st.metric("Total Tables", len(schema_agent.schema_cache['tables']))
        
        # Show extraction time
        extracted_at = schema_agent.schema_cache.get('extracted_at', 'Unknown')
        st.caption(f"Last extracted: {extracted_at[:19]}")
    
    # Expandable full schema view
    with st.expander("View Full Schema"):
        st.text(schema_text)
    
    # Save schema option
    if st.button("💾 Save Schema to File"):
        schema_agent.save_schema_to_file("schema_cache.json")
        st.success("Schema saved to schema_cache.json")

# Main interface
with st.expander("💭 Conversation Memory"):
    st.text(display_memory())

user_query = st.text_input("Ask anything about your database:", placeholder="e.g., Show me all customers from last month")

# ----------------------------------------------------
# QUERY PROCESSING
# ----------------------------------------------------
if st.button("Run", type="primary"):
    if not user_query.strip():
        st.warning("Please enter a query!")
        st.stop()
    
    with st.spinner("Thinking..."):
        # Build full prompt with dynamic schema
        full_prompt = f"""
{schema_text}

{SQL_GENERATION_RULES}

Conversation History:
{display_memory()}

User Query: "{user_query}"

Analyze the query and decide the correct mode (SQL or CHAT).
"""

        # Call Gemini
        model = genai.GenerativeModel("gemini-2.5-flash")
        resp = model.generate_content(full_prompt)
        raw = safe_text(resp)

        if raw is None:
            st.error("⚠️ AI returned no content. Please try again.")
            st.stop()

        # Parse response mode
        if raw.startswith("MODE: SQL"):
            mode = "SQL"
            sql_query = raw.split("MODE: SQL")[-1].strip()

            st.subheader("📝 Generated SQL")
            st.code(sql_query, language="sql")

            # Execute SQL with safety checks
            conn = None
            cur = None
            
            try:
                conn = connect_db()
                cur = conn.cursor()
                
                # Security check: only allow SELECT
                if not sql_query.strip().upper().startswith("SELECT"):
                    st.error("❌ Only SELECT queries are allowed for security reasons.")
                    add_memory(user_query, "SQL_ERROR", "Non-SELECT query blocked")
                    st.stop()
                
                # Set query timeout
                cur.execute(f"SET statement_timeout = {Config.QUERY_TIMEOUT_SECONDS * 1000};")
                
                # Execute query
                cur.execute(sql_query)
                
                # Fetch results
                rows = cur.fetchall()
                cols = [d[0] for d in cur.description]
                
                # Check result size
                row_count = len(rows)
                if row_count > Config.MAX_RESULT_ROWS:
                    st.warning(f"⚠️ Results limited to {Config.MAX_RESULT_ROWS} rows (total: {row_count})")
                    rows = rows[:Config.MAX_RESULT_ROWS]
                
                df = pd.DataFrame(rows, columns=cols)
                
                st.subheader("📊 Results")
                st.dataframe(df, use_container_width=True)
                
                # Show row count
                st.caption(f"Returned {len(df)} rows")
                
                # Prepare result for explanation (use actual data, not just row count)
                if len(df) == 1 and len(df.columns) == 1:
                    # Single value result (like COUNT, SUM, etc.)
                    result_display = f"The answer is: {df.iloc[0, 0]}"
                elif len(df) <= 5:
                    # Small result set - show actual data
                    result_display = df.to_string()
                else:
                    # Large result set - show summary
                    result_display = f"Found {len(df)} records. First few:\n{df.head(3).to_string()}"

            except psycopg2.Error as e:
                st.error(f"❌ Database Error: {e}")
                add_memory(user_query, "SQL_ERROR", str(e))
                st.stop()
                
            except Exception as e:
                st.error(f"❌ Error: {e}")
                add_memory(user_query, "ERROR", str(e))
                st.stop()
                
            finally:
                if cur:
                    cur.close()
                if conn:
                    conn.close()

            # Add to memory
            add_memory(user_query, "SQL", result_display)

            # Generate explanation
            explain_prompt = f"""
You are John, a friendly AI assistant helping users understand their data.

The user asked: "{user_query}"

The database returned this result:
{result_display}

Instructions:
1. Answer the user's question directly in simple, everyday language
2. DO NOT talk about "rows", "queries", or technical database terms
3. Focus on the actual answer to their question
4. Be conversational and helpful
5. If it's a count/number, just say "You have X products" (for example)
6. If it's data, summarize what was found in plain English

Provide a clear, friendly answer that directly addresses what they asked:
"""

            resp2 = model.generate_content(explain_prompt)
            explanation = safe_text(resp2) or "Query executed successfully."
            
            st.subheader("💡 AI Explanation")
            st.write(explanation)

        # Chat mode
        elif raw.startswith("MODE: CHAT"):
            mode = "CHAT"
            chat_reply = raw.split("MODE: CHAT")[-1].strip()

            st.subheader("💬 Response")
            st.write(chat_reply)

            add_memory(user_query, "CHAT", chat_reply)

        else:
            st.error("⚠️ AI output format not recognized. Please try again.")

# Footer
st.divider()
st.caption("🔒 Using read-only database access • 🤖 Powered by Gemini AI • 💾 Schema auto-cached")
