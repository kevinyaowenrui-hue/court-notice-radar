import os
import zipfile

def package_zip():
    dist_dir = os.path.join('dist', '法拍雷达')
    out_zip = os.path.join('dist', '法拍雷达-最新版-Windows.zip')
    print(f"Compressing {dist_dir} -> {out_zip} ...")
    count = 0
    with zipfile.ZipFile(out_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(dist_dir):
            for file in files:
                p = os.path.join(root, file)
                arcname = os.path.relpath(p, 'dist')
                zf.write(p, arcname)
                count += 1
    size_mb = round(os.path.getsize(out_zip) / (1024 * 1024), 2)
    print(f"Done! Compressed {count} files. Zip size: {size_mb} MB")

if __name__ == '__main__':
    package_zip()
