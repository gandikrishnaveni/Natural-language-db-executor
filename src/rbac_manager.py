# class RBACManager:

#     def __init__(self, role):
#         self.role = role

#     def check_permission(self, sql_query):
#         sql = sql_query.strip().upper()

#         # Get query type
#         query_type = sql.split()[0]

#         # ----------------------------
#         # STUDENT RULES
#         # ----------------------------
#         if self.role == "Student":
#             if query_type == "SELECT":
#                 return True, "Allowed"
#             else:
#                 return False, "Students can only view data."

#         # ----------------------------
#         # FACULTY RULES
#         # ----------------------------
#         elif self.role == "Faculty":

#             # Allow SELECT
#             if query_type == "SELECT":
#                 return True, "Allowed"

#             # Allow UPDATE only for grade column in takes table
#             if query_type == "UPDATE":
#                 if "TAKES" in sql and "GRADE" in sql:
#                     return True, "Allowed"
#                 else:
#                     return False, "Faculty can only update grades in takes table."

#             return False, "Faculty cannot perform this operation."

#         # ----------------------------
#         # ADMIN RULES
#         # ----------------------------
#         elif self.role == "Admin":
#             return True, "Allowed"

#         # ----------------------------
#         # Unknown role
#         # ----------------------------
#         else:
#             return False, "Invalid role."


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
