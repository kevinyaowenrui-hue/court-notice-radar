import os
import zipfile

def package_binary_zip():
    alt_dir = os.path.join('build', 'dist_out', '法拍雷达')
    dist_dir = os.path.join('dist', '法拍雷达')
    src_dir = alt_dir if os.path.exists(alt_dir) else dist_dir
    if os.path.exists(alt_dir):
        import shutil
        for root, dirs, files in os.walk(alt_dir):
            rel_root = os.path.relpath(root, alt_dir)
            target_root = os.path.join(dist_dir, rel_root) if rel_root != '.' else dist_dir
            os.makedirs(target_root, exist_ok=True)
            for f in files:
                s_file = os.path.join(root, f)
                t_file = os.path.join(target_root, f)
                try:
                    shutil.copy2(s_file, t_file)
                except PermissionError:
                    pass
    out_zip = os.path.join('dist', '法拍雷达-最新版-Windows.zip')
    print(f"Compressing {src_dir} -> {out_zip} ...")
    count = 0
    base_parent = os.path.dirname(src_dir)
    with zipfile.ZipFile(out_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                p = os.path.join(root, file)
                arcname = os.path.relpath(p, base_parent)
                zf.write(p, arcname)
                count += 1
    size_mb = round(os.path.getsize(out_zip) / (1024 * 1024), 2)
    print(f"Done! Compressed {count} binary files. Zip size: {size_mb} MB")

def package_source_zip():
    out_zip = os.path.join('dist', '法拍雷达-源码全量-最新版.zip')
    print(f"Compressing source code -> {out_zip} ...")
    count = 0
    ignore_dirs = {'.git', 'node_modules', 'dist', 'build', '__pycache__', '.pytest_cache'}
    with zipfile.ZipFile(out_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk('.'):
            # prune ignored directories
            dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith('.')]
            for file in files:
                if file.endswith(('.pyc', '.pyo', '.log', '.DS_Store')):
                    continue
                p = os.path.join(root, file)
                # normalize path relative to repo root
                rel = os.path.relpath(p, '.')
                if rel.startswith(('dist', 'build', '.git')):
                    continue
                arcname = os.path.join('court-notice-radar', rel)
                zf.write(p, arcname)
                count += 1
    size_mb = round(os.path.getsize(out_zip) / (1024 * 1024), 2)
    print(f"Done! Compressed {count} source files. Source zip size: {size_mb} MB")

if __name__ == '__main__':
    package_binary_zip()
    package_source_zip()
