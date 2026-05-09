import os

file_path = r"c:\Users\USER\Desktop\BOT-SVSU\BOT_BACKEND\api_server.py"
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

new_routes = """@app.get("/login")
async def login_page():
    return RedirectResponse(url="/admin_panel/admin_login.html")

@app.get("/dashboard")
async def dashboard_redirect():
    return RedirectResponse(url="/admin_panel/admin.html")

@app.get("/admin")"""

content = content.replace('@app.get("/admin")', new_routes)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Applied!")
