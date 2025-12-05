"""
Schema Extraction Agent for PostgreSQL Database
Dynamically extracts and manages database schema for large production databases.
"""

import psycopg2
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta


class SchemaAgent:
    """
    Intelligent agent to extract, cache, and manage PostgreSQL database schema.
    Designed for large production databases with read-only access.
    """
    
    def __init__(self, db_config: Dict[str, str], cache_duration_minutes: int = 60):
        """
        Initialize Schema Agent with database configuration.
        
        Args:
            db_config: Dictionary with keys: host, database, user, password, port
            cache_duration_minutes: How long to cache schema before refreshing
        """
        self.db_config = db_config
        self.cache_duration = timedelta(minutes=cache_duration_minutes)
        self.schema_cache = None
        self.cache_timestamp = None
        self.full_schema_text = None
        
    def _is_cache_valid(self) -> bool:
        """Check if cached schema is still valid."""
        if self.schema_cache is None or self.cache_timestamp is None:
            return False
        return datetime.now() - self.cache_timestamp < self.cache_duration
    
    def _connect(self):
        """Create a database connection."""
        return psycopg2.connect(
            host=self.db_config['host'],
            database=self.db_config['database'],
            user=self.db_config['user'],
            password=self.db_config['password'],
            port=self.db_config['port']
        )
    
    def extract_full_schema(self, force_refresh: bool = False) -> Dict:
        """
        Extract complete database schema including tables, columns, types, and relationships.
        
        Args:
            force_refresh: Force refresh even if cache is valid
            
        Returns:
            Dictionary containing complete schema information
        """
        if not force_refresh and self._is_cache_valid():
            return self.schema_cache
        
        conn = self._connect()
        cur = conn.cursor()
        
        schema_info = {
            'tables': {},
            'foreign_keys': [],
            'extracted_at': datetime.now().isoformat()
        }
        
        try:
            # Get all tables in public schema
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name;
            """)
            tables = [row[0] for row in cur.fetchall()]
            
            for table in tables:
                schema_info['tables'][table] = self._extract_table_info(cur, table)
            
            # Extract foreign key relationships
            schema_info['foreign_keys'] = self._extract_foreign_keys(cur)
            
            # Cache the results
            self.schema_cache = schema_info
            self.cache_timestamp = datetime.now()
            self.full_schema_text = self._generate_llm_schema_text(schema_info)
            
        finally:
            cur.close()
            conn.close()
        
        return schema_info
    
    def _extract_table_info(self, cursor, table_name: str) -> Dict:
        """Extract detailed information about a specific table."""
        table_info = {
            'columns': [],
            'primary_keys': [],
            'indexes': []
        }
        
        # Get column information
        cursor.execute("""
            SELECT 
                column_name,
                data_type,
                character_maximum_length,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = 'public' 
            AND table_name = %s
            ORDER BY ordinal_position;
        """, (table_name,))
        
        for row in cursor.fetchall():
            col_name, data_type, max_length, nullable, default = row
            
            # Format data type
            type_str = data_type
            if max_length:
                type_str = f"{data_type}({max_length})"
            
            table_info['columns'].append({
                'name': col_name,
                'type': type_str,
                'nullable': nullable == 'YES',
                'default': default
            })
        
        # Get primary keys
        cursor.execute("""
            SELECT a.attname
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = ('public.' || quote_ident(%s))::regclass
            AND i.indisprimary;
        """, (table_name,))
        
        table_info['primary_keys'] = [row[0] for row in cursor.fetchall()]
        
        # Get indexes
        cursor.execute("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = %s
            AND schemaname = 'public';
        """, (table_name,))
        
        table_info['indexes'] = [{'name': row[0], 'definition': row[1]} for row in cursor.fetchall()]
        
        return table_info
    
    def _extract_foreign_keys(self, cursor) -> List[Dict]:
        """Extract all foreign key relationships."""
        cursor.execute("""
            SELECT
                tc.table_name AS source_table,
                kcu.column_name AS source_column,
                ccu.table_name AS target_table,
                ccu.column_name AS target_column,
                tc.constraint_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_schema = 'public';
        """)
        
        foreign_keys = []
        for row in cursor.fetchall():
            foreign_keys.append({
                'source_table': row[0],
                'source_column': row[1],
                'target_table': row[2],
                'target_column': row[3],
                'constraint_name': row[4]
            })
        
        return foreign_keys
    
    def _generate_llm_schema_text(self, schema_info: Dict) -> str:
        """
        Generate optimized, concise schema description for LLM consumption.
        
        This format is designed to:
        - Minimize token usage for large databases
        - Highlight important relationships
        - Include data type information
        - Note constraints and special columns
        """
        lines = []
        lines.append("=== DATABASE SCHEMA ===\n")
        
        # Generate table descriptions
        for table_name, table_data in sorted(schema_info['tables'].items()):
            # Table header
            pk_cols = table_data['primary_keys']
            pk_str = f" [PK: {', '.join(pk_cols)}]" if pk_cols else ""
            lines.append(f"\n{table_name}{pk_str}:")
            
            # Columns
            for col in table_data['columns']:
                nullable = "" if col['nullable'] else " NOT NULL"
                default = f" DEFAULT {col['default']}" if col['default'] else ""
                pk_marker = " (PK)" if col['name'] in pk_cols else ""
                
                lines.append(f"  - {col['name']}: {col['type']}{nullable}{default}{pk_marker}")
        
        # Foreign key relationships
        if schema_info['foreign_keys']:
            lines.append("\n=== FOREIGN KEY RELATIONSHIPS ===")
            for fk in schema_info['foreign_keys']:
                lines.append(
                    f"{fk['source_table']}.{fk['source_column']} -> "
                    f"{fk['target_table']}.{fk['target_column']}"
                )
        
        lines.append(f"\n=== METADATA ===")
        lines.append(f"Total Tables: {len(schema_info['tables'])}")
        lines.append(f"Extracted At: {schema_info['extracted_at']}")
        
        return "\n".join(lines)
    
    def get_schema_for_llm(self, force_refresh: bool = False) -> str:
        """
        Get schema formatted for LLM consumption.
        
        Args:
            force_refresh: Force schema refresh
            
        Returns:
            Formatted schema string ready for LLM prompts
        """
        if not force_refresh and self.full_schema_text and self._is_cache_valid():
            return self.full_schema_text
        
        schema_info = self.extract_full_schema(force_refresh)
        return self.full_schema_text
    
    def get_relevant_tables(self, query: str) -> List[str]:
        """
        Analyze user query to identify potentially relevant tables.
        This helps reduce schema size sent to LLM for very large databases.
        
        Args:
            query: User's natural language query
            
        Returns:
            List of table names that might be relevant
        """
        if not self.schema_cache:
            self.extract_full_schema()
        
        query_lower = query.lower()
        relevant_tables = []
        
        for table_name in self.schema_cache['tables'].keys():
            # Check if table name appears in query
            if table_name.lower() in query_lower:
                relevant_tables.append(table_name)
                continue
            
            # Check if any column name appears in query
            for col in self.schema_cache['tables'][table_name]['columns']:
                if col['name'].lower() in query_lower:
                    relevant_tables.append(table_name)
                    break
        
        # If no specific tables found, return all (user query is too general)
        return relevant_tables if relevant_tables else list(self.schema_cache['tables'].keys())
    
    def get_partial_schema(self, table_names: List[str]) -> str:
        """
        Generate schema text for only specific tables.
        Useful for very large databases to reduce token usage.
        
        Args:
            table_names: List of table names to include
            
        Returns:
            Formatted schema string for specified tables only
        """
        if not self.schema_cache:
            self.extract_full_schema()
        
        # Create filtered schema
        filtered_schema = {
            'tables': {name: self.schema_cache['tables'][name] 
                      for name in table_names if name in self.schema_cache['tables']},
            'foreign_keys': [fk for fk in self.schema_cache['foreign_keys']
                           if fk['source_table'] in table_names or fk['target_table'] in table_names],
            'extracted_at': self.schema_cache['extracted_at']
        }
        
        return self._generate_llm_schema_text(filtered_schema)
    
    def save_schema_to_file(self, filepath: str = "schema_cache.json"):
        """
        Save extracted schema to JSON file for backup/inspection.
        
        Args:
            filepath: Path to save schema JSON
        """
        if not self.schema_cache:
            self.extract_full_schema()
        
        with open(filepath, 'w') as f:
            json.dump(self.schema_cache, f, indent=2)
    
    def get_table_sample_data(self, table_name: str, limit: int = 5) -> List[tuple]:
        """
        Get sample data from a table to help LLM understand data patterns.
        
        Args:
            table_name: Name of the table
            limit: Number of sample rows
            
        Returns:
            List of sample rows
        """
        conn = self._connect()
        cur = conn.cursor()
        
        try:
            cur.execute(f"SELECT * FROM {table_name} LIMIT %s;", (limit,))
            return cur.fetchall()
        finally:
            cur.close()
            conn.close()
    
    def clear_cache(self):
        """Manually clear the schema cache."""
        self.schema_cache = None
        self.cache_timestamp = None
        self.full_schema_text = None
