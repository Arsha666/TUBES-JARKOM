import socket
import threading
import os
import time

PROXY_PORT = 8080
SERVER_HOST = '127.0.0.1'  
SERVER_PORT = 8000
CACHE_DIR = "proxy_cache"
TEMPLATE_DIR = "templates" # Mengarah ke folder templates untuk halaman error lokal

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def get_cache_filename(path):
    if path == '/' or path == '':
        return os.path.join(CACHE_DIR, "index.html")
    
    safe_name = path.lstrip('/').replace('/', '_')
    if not safe_name.endswith('.html') and not safe_name.endswith('.css') and not '.' in safe_name:
        safe_name += '.html'
    return os.path.join(CACHE_DIR, safe_name)

def serve_local_error(client_socket, status_code, html_file):
    content = b""
    # Cari file error di dalam folder templates
    target_path = os.path.join(TEMPLATE_DIR, html_file)
    if os.path.exists(target_path):
        with open(target_path, 'rb') as f:
            content = f.read()
    else:
        content = f"<h1>{status_code}</h1><p>Halaman error {html_file} tidak ditemukan di folder templates.</p>".encode('utf-8')
        
    response = (
        f"HTTP/1.1 {status_code}\r\n"
        f"Content-Type: text/html\r\n"
        f"Content-Length: {len(content)}\r\n"
        f"Connection: close\r\n\r\n"
    ).encode('utf-8') + content
    client_socket.sendall(response)

def handle_client(client_socket, client_address):
    try:
        request_data = client_socket.recv(4096)
        if not request_data:
            return
            
        request_text = request_data.decode('utf-8', errors='ignore')
        lines = request_text.split('\r\n')
        if len(lines) == 0 or not lines[0]:
            return
            
        parts = lines[0].split()
        if len(parts) < 2:
            return
            
        method, path = parts[0], parts[1]
        cache_file = get_cache_filename(path)
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')

        # 1. MEKANISME CACHE HIT
        if os.path.exists(cache_file) and method == "GET":
            print(f"[{timestamp}] Proxy LOG - Client: {client_address[0]} | Request: {path} | CACHE: HIT")
            with open(cache_file, 'rb') as f:
                cached_content = f.read()
                
            content_type = 'text/css' if path.endswith('.css') else 'text/html'
            
            response_header = (
                f"HTTP/1.1 200 OK\r\n"
                f"Content-Type: {content_type}\r\n"
                f"Content-Length: {len(cached_content)}\r\n"
                f"Connection: close\r\n\r\n"
            ).encode('utf-8')
            
            client_socket.sendall(response_header + cached_content)
            
        # 2. MEKANISME CACHE MISS
        else:
            print(f"[{timestamp}] Proxy LOG - Client: {client_address[0]} | Request: {path} | CACHE: MISS")
            
            try:
                server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server_socket.settimeout(3.0)  
                server_socket.connect((SERVER_HOST, SERVER_PORT))
                server_socket.sendall(request_data)
                
                response_data = b""
                while True:
                    chunk = server_socket.recv(4096)
                    if not chunk:
                        break
                    response_data += chunk
                server_socket.close()
                
                if b"200 OK" in response_data:
                    header_body = response_data.split(b"\r\n\r\n", 1)
                    if len(header_body) == 2:
                        body_content = header_body[1]
                        with open(cache_file, 'wb') as f:
                            f.write(body_content)
                
                client_socket.sendall(response_data)
                
            except socket.timeout:
                serve_local_error(client_socket, "504 Gateway Timeout", "504.html")
            except socket.error:
                serve_local_error(client_socket, "502 Bad Gateway", "502.html")

    except Exception as e:
        print(f"[-] Error pada penanganan proxy: {e}")
    finally:
        client_socket.close()

def start_proxy():
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    proxy_socket.bind(('0.0.0.0', PROXY_PORT))
    proxy_socket.listen(50)
    print(f"[*] Proxy Server berjalan di port {PROXY_PORT}...")
    
    while True:
        client_socket, client_address = proxy_socket.accept()
        threading.Thread(target=handle_client, args=(client_socket, client_address), daemon=True).start()

if __name__ == '__main__':
    start_proxy()