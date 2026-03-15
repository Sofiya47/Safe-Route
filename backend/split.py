import re

with open('../frontend/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Extract styles
style_match = re.search(r'<style>(.*?)</style>', html, flags=re.DOTALL)
css_content = style_match.group(1).strip() if style_match else ''

# Extract scripts
# Find all scripts
scripts = re.findall(r'<script.*?</script>', html, flags=re.DOTALL)
# The custom script is the last one
js_content = ""
for script in scripts:
    if "API_BASE" in script or "analyzeRoute" in script:
        content = re.search(r'<script>(.*?)</script>', script, flags=re.DOTALL)
        if content:
            js_content = content.group(1).strip()

# Clean html
html = re.sub(r'<style>.*?</style>', '<link rel="stylesheet" href="style.css" />', html, flags=re.DOTALL)

# Replace the specific script block with an external link
html = re.sub(r'<script>\s*const API_BASE.*?</body>', '<script src="script.js"></script>\n</body>', html, flags=re.DOTALL)

with open('../frontend/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

with open('../frontend/style.css', 'w', encoding='utf-8') as f:
    f.write(css_content)

with open('../frontend/script.js', 'w', encoding='utf-8') as f:
    f.write(js_content)

print("Split complete")
