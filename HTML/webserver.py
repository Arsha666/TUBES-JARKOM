import socket
import threading
import os
import time

# Konfigurasi Port
TCP_PORT = 8000
UDP_PORT = 9000
HOST = '0.0.0.0' # Bind ke semua interface agar bisa diakses dalam LAN

def get_content_type(filepath):
    if filepath.endswith('.html'): return 'text/html'
    if filepath.endswith('.css'): return 'text/css'
    if filepath.endswith('.png'): return 'image/png'
    if filepath.endswith('.jpg') or filepath.endswith('.jpeg'): return 'image/jpeg'
    return 'application/octet-stream'

# Handler untuk setiap koneksi HTTP (TCP)
def handle_tcp_client(client_socket, client_address):
    try:
        request = client_socket.recv(4096).decode('utf-8', errors='ignore')
        if not request:
            client_socket.close()
            return
        
        # Parsing baris pertama request (contoh: "GET /index.html HTTP/1.1")
        lines = request.split('\r\n')
        request_line = lines[0]
        parts = request_line.split()
        
        if len(parts) < 2:
            client_socket.close()
            return
            
        method, path = parts[0], parts[1]
        
        # Normalisasi path
        if path == '/' or path == '':
            filename = 'index.html'
        else:
            filename = path.lstrip('/')
            if not filename.endswith('.html') and not filename.endswith('.css') and not '.' in filename:
                filename += '.html' # auto append .html jika navigasi tanpa ekstensi

        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        
        # Cek apakah file ada
        if os.path.exists(filename) and os.path.isfile(filename):
            status_code = "200 OK"
            with open(filename, 'rb') as f:
                content = f.read()
            content_type = get_content_type(filename)
        else:
            status_code = "404 Not Found"
            content_type = 'text/html'
            if os.path.exists('404.html'):
                with open('404.html', 'rb') as f:
                    content = f.read()
            else:
                content = b"<h1>404 Not Found</h1>"

        # Cetak LOG sesuai ketentuan (Hanya mencatat IP Proxy yang menembak server)
        print(f"[{timestamp}] TCP Server LOG - Proxy IP: {client_address[0]} | Request: {method} {path} | Status: {status_code}")

        # Kirim HTTP Response
        response_header = f"HTTP/1.1 {status_code}\r\n"
        response_header += f"Content-Type: {content_type}\r\n"
        response_header += f"Content-Length: {len(content)}\r\n"
        response_header += "Connection: close\r\n\r\n"
        
        client_socket.sendall(response_header.encode('utf-8') + content)

    except Exception as e:
        # Handle 500 Internal Server Error jika terjadi crash internal
        try:
            status_code = "500 Internal Server Error"
            if os.path.exists('500.html'):
                with open('500.html', 'rb') as f:
                    content = f.read()
            else:
                content = b"<h1>500 Internal Server Error</h1>"
                
            response_header = f"HTTP/1.1 {status_code}\r\nContent-Type: text/html\r\nContent-Length: {len(content)}\r\nConnection: close\r\n\r\n"
            client_socket.sendall(response_header.encode('utf-8') + content)
        except:
            pass
    finally:
        client_socket.close()

# Fungsi menjalankan HTTP Server (TCP)
def start_tcp_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, TCP_PORT))
    server_socket.listen(20)
    print(f"[*] TCP Web Server berjalan di port {TCP_PORT}...")
    
    while True:
        client_socket, client_address = server_socket.accept()
        # Thread-per-connection untuk konkurensi
        threading.Thread(target=handle_tcp_client, args=(client_socket, client_address), daemon=True).start()

# Fungsi menjalankan Echo Server (UDP untuk QoS)
def start_udp_server():
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind((HOST, UDP_PORT))
    print(f"[*] UDP Echo Server (QoS) berjalan di port {UDP_PORT}...")
    
    while True:
        data, address = udp_socket.recvfrom(2048)
        # Sesuai aturan QoS: Langsung pantulkan data kembali ke pengirim (client)
        udp_socket.sendto(data, address)

if __name__ == '__main__':
    # Menjalankan TCP dan UDP server secara bersamaan menggunakan multithreading luar
    threading.Thread(target=start_tcp_server, daemon=True).start()
    start_udp_server()