# test_graph.py — demo for Call Graph visualization

class Database:
    def connect(self):
        self.validate_config()
        log_action("db_connected")

    def validate_config(self):
        sanitize("config")

    def query(self, sql):
        self.connect()
        result = self.execute(sql)
        log_query(sql)
        return result

    def execute(self, sql):
        format_log(sql)

    def close(self):
        log_action("db_closed")


class Cache:
    def get(self, key):
        log_action("cache_hit")

    def set(self, key, value):
        sanitize(key)
        sanitize(value)
        log_action("cache_set")

    def invalidate(self):
        log_action("cache_clear")


class UserService:
    def get_user(self, user_id):
        cache = Cache()
        cached = cache.get(user_id)
        if cached:
            return cached
        db = Database()
        user = db.query("SELECT * FROM users")
        cache.set(user_id, user)
        return user

    def create_user(self, name, email):
        validate_email(email)
        sanitize(name)
        db = Database()
        db.query("INSERT INTO users")
        cache = Cache()
        cache.invalidate()
        notify(email)

    def delete_user(self, user_id):
        self.get_user(user_id)
        db = Database()
        db.query("DELETE FROM users")
        cache = Cache()
        cache.invalidate()
        log_action("user_deleted")

    def list_users(self):
        db = Database()
        return db.query("SELECT * FROM users")


class AuthService:
    def login(self, email, password):
        user_svc = UserService()
        user = user_svc.get_user(email)
        if self.check_password(user, password):
            token = self.generate_token(user)
            log_action("login_success")
            return token
        log_action("login_failed")

    def check_password(self, user, password):
        hashed = hash_password(password)
        return hashed == user

    def generate_token(self, user):
        sanitize(user)
        log_action("token_generated")
        return "token"

    def logout(self, token):
        cache = Cache()
        cache.invalidate()
        log_action("logout")

    def register(self, name, email, password):
        validate_email(email)
        hash_password(password)
        user_svc = UserService()
        user_svc.create_user(name, email)
        self.login(email, password)


class NotificationService:
    def send_email(self, to, subject, body):
        validate_email(to)
        sanitize(body)
        sanitize(subject)
        log_action("email_sent")

    def send_sms(self, phone, message):
        sanitize(message)
        log_action("sms_sent")

    def broadcast(self, users, message):
        for u in users:
            self.send_email(u, "Broadcast", message)
            self.send_sms(u, message)
        log_action("broadcast_done")


class ReportService:
    def generate_report(self):
        user_svc = UserService()
        users = user_svc.list_users()
        data = self.analyze(users)
        self.export(data)
        log_action("report_done")

    def analyze(self, data):
        sanitize(data)
        format_log("analyzing")
        return data

    def export(self, data):
        format_log("exporting")
        notifier = NotificationService()
        notifier.send_email("admin@test.com", "Report", data)

    def schedule(self):
        log_action("report_scheduled")
        self.generate_report()


# ── Standalone functions ──

def validate_email(email):
    sanitize(email)

def sanitize(text):
    pass

def hash_password(password):
    sanitize(password)

def notify(email):
    svc = NotificationService()
    svc.send_email(email, "Welcome", "Hello!")

def log_action(action):
    log_query(action)

def log_query(sql):
    format_log(sql)

def format_log(msg):
    sanitize(msg)

def startup():
    db = Database()
    db.connect()
    cache = Cache()
    cache.invalidate()
    log_action("system_started")

def shutdown():
    db = Database()
    db.close()
    log_action("system_stopped")


def main():
    startup()

    auth = AuthService()
    auth.register("Alice", "alice@test.com", "pass123")
    auth.login("bob@test.com", "secret")

    user_svc = UserService()
    user_svc.create_user("Charlie", "charlie@test.com")
    user_svc.delete_user(1)

    report = ReportService()
    report.schedule()

    notifier = NotificationService()
    notifier.broadcast(["a@test.com", "b@test.com"], "Hello all!")

    shutdown()


main()
