from flask_login import UserMixin
 
class User(UserMixin):
    def __init__(self, user_dict: dict):
        self.id        = user_dict["id"]
        self.name      = user_dict["name"]
        self.email     = user_dict["email"]
        self.picture   = user_dict.get("picture") or ""
        self.auth_type = user_dict.get("auth_type", "google")
        self.joined    = str(user_dict.get("created_at", ""))[:10]
 
    def get_id(self):
        return str(self.id)
 