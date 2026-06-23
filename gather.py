import os

exts = ['.html', '.css', '.js', '.py', '.txt', '.yaml']
with open('full_codebase.txt', 'w', encoding='utf-8') as out:
    out.write('--- FULL CODEBASE ---\n\n')
    for f in os.listdir('.'):
        if os.path.isfile(f) and any(f.endswith(e) for e in exts):
            out.write(f'--- {f} ---\n')
            with open(f, 'r', encoding='utf-8') as infile:
                out.write(infile.read())
            out.write('\n\n')
