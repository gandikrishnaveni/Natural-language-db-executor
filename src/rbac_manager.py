
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


def is_authorized(emp_id, sql_query):
    """
    Check if user has permission to execute this SQL query.
    """
    permissions = get_user_permissions(emp_id)

    if not permissions:
        return False

    # Extract SQL command type
    query_type = sql_query.strip().split()[0].upper()

    return query_type in permissions
