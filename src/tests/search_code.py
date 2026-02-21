import os

root = r'C:\Users\Nayan\Desktop\DevOpsAgent-cli\.venv\Lib\site-packages\langfuse'
for r, d, f in os.walk(root):
    for file in f:
        if file.endswith('.py'):
            path = os.path.join(r, file)
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f_obj:
                    content = f_obj.read()
                    if 'CallbackHandler' in content:
                        print(f"MATCH: {path}")
            except Exception as e:
                pass
