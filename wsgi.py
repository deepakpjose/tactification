import os
from manage import app as application

print("wsgi")
if __name__ == "__main__":
    application.run(host="0.0.0.0")
