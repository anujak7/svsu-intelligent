import os

file_path = 'admin_panel/chatbot.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace relative paths with absolute ones
content = content.replace("url('/assets/", "url('https://chatbot.svsu.ac.in/assets/")
content = content.replace('src="/assets/', 'src="https://chatbot.svsu.ac.in/assets/')
content = content.replace("src='/assets/", "src='https://chatbot.svsu.ac.in/assets/")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Chatbot HTML paths updated to absolute URLs.")
