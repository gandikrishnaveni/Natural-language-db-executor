import re
from pymongo import MongoClient

# Create MongoDB connection (once)
client = MongoClient("mongodb://localhost:27017/")
db = client.LegalBrain
collection = db.user_roles


def get_user_permissions(emp_id):
    """
    Fetch permissions list for given employee ID.
    """
    user = collection.find_one({"emp_id": emp_id})

    if user:
        return user.get("permissions", [])

    return []


def remove_sql_comments(query):
    """
    Remove SQL single-line and multi-line comments.
    """
    # Remove -- comments
    query = re.sub(r'--.*', '', query)

    # Remove /* */ comments
    query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)

    return query


def extract_sql_keywords(query):
    """
    Extract SQL command keywords as whole words.
    """
    # Match SQL keywords as whole words only
    keywords = re.findall(r'\b(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE)\b',
                          query,
                          flags=re.IGNORECASE)
    return [k.upper() for k in keywords]


def is_authorized(emp_id, sql_query):

    user = collection.find_one({"emp_id": emp_id})

    if not user:
        return False

    permissions = user.get("permissions", [])
    role = user.get("role", "").upper()

    # 🔓 Admin Fast-Track
    if role == "ADMIN":
        return True

    # Remove comments
    cleaned_query = remove_sql_comments(sql_query)

    # Extract SQL keywords
    found_keywords = extract_sql_keywords(cleaned_query)

    if not found_keywords:
        return False

    # Check all keywords
    for keyword in found_keywords:
        if keyword not in permissions:
            return False

    return True
