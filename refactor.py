import sys
import re
import glob

def process_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    match = re.search(r'def register_([a-z_]+)_tools\(mcp: FastMCP\) -> None:\n', content)
    if not match:
        print(f"Skipping {filepath}")
        return
        
    start_idx = match.start()
    header = match.group(0)
    
    pre_content = content[:start_idx]
    inside_content = content[match.end():]
    
    lines = inside_content.split('\n')
    funcs = []
    
    new_lines = []
    for line in lines:
        if line.startswith('    @mcp.tool()'):
            continue
        if line.startswith('    async def ') or line.startswith('    def '):
            func_name = line.split('def ')[1].split('(')[0]
            if func_name.startswith('_'):
                new_lines.append(line[4:])
            else:
                funcs.append(func_name)
                new_lines.append(line[4:])
        elif line.startswith('    ') or line == '':
            if line.startswith('    '):
                new_lines.append(line[4:])
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
            
    # Remove trailing newlines from new_lines
    while new_lines and new_lines[-1] == '':
        new_lines.pop()
            
    final_content = pre_content + '\n'.join(new_lines) + '\n\n' + header
    for func in funcs:
        final_content += f"    mcp.add_tool({func})\n"
        
    with open(filepath, 'w') as f:
        f.write(final_content)
    print(f"Refactored {filepath}")

for file in glob.glob('dockhand_mcp/tools/*.py'):
    if not file.endswith('__init__.py'):
        process_file(file)

