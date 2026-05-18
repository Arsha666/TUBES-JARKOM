import socket
import time

# Konstanta sesuai arsitektur sistem di PDF soal
PROXY_HOST = '127.0.0.1'
PROXY_PORT = 8080
SERVER_HOST = '127.0.0.1'
UDP_PORT = 9000  # Sesuaikan ke 10000 jika di webserver.py kamu pakai port 10000

def run_http_test():
    print("\n" + "="*20 + " 1. PENGUJIAN HTTP GET (TCP VIA PROXY) " + "="*20)
    path = '/index.html'
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(3.0)
        client_socket.connect((PROXY_HOST, PROXY_PORT))
        
        # Format HTTP request standar baku
        request = f"GET {path} HTTP/1.1\r\nHost: {PROXY_HOST}:{PROXY_PORT}\r\nConnection: close\r\n\r\n"
        client_socket.sendall(request.encode('utf-8'))
        
        response = b""
        while True:
            chunk = client_socket.recv(4096)
            if not chunk:
                break
            response += chunk
            
        # Pisahkan header untuk mengecek status code (200 OK / 404 / dll) tanpa mengotori CMD
        response_text = response.decode('utf-8', errors='ignore')
        header_part = response_text.split('\r\n\r\n')[0]
        
        print(f"[*] Request dikirim: GET {path}")
        print("[*] HTTP Response Header dari Proxy:")
        print(header_part)
        print("[+] Koneksi TCP via Proxy Sukses!")
        
    except Exception as e:
        print(f"[-] Gagal terhubung ke Proxy: {e}")
    finally:
        client_socket.close()

def run_udp_qos_test():
    print("\n" + "="*20 + " 2. PENGUJIAN KINERJA JARINGAN (UDP QoS) " + "="*20)
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.settimeout(1.0) # Timeout 1 detik sesuai ketentuan spesifikasi
    
    rtts = []
    packets_sent = 10
    packets_received = 0
    delays = []
    last_rtt = None
    
    for i in range(1, packets_sent + 1):
        send_time = time.time()
        # Format isi pesan sesuai dengan pedoman pinger
        message = f"Ping {i} {send_time}"
        
        try:
            udp_socket.sendto(message.encode('utf-8'), (SERVER_HOST, UDP_PORT))
            data, address = udp_socket.recvfrom(2048)
            recv_time = time.time()
            
            rtt = (recv_time - send_time) * 1000 # Hitung RTT dalam milidetik (ms)
            rtts.append(rtt)
            packets_received += 1
            
            # Hitung selisih antar RTT untuk metrik Jitter
            if last_rtt is not None:
                delays.append(abs(rtt - last_rtt))
            last_rtt = rtt
            
            print(f" Paket {i}: Balasan dari {address[0]} | RTT = {rtt:.2f} ms")
        except socket.timeout:
            print(f" Paket {i}: Request timed out (RTO)")
            last_rtt = None
            
        time.sleep(0.1) # Jeda berkala pengiriman paket
    udp_socket.close()
    
    # --- OUTPUT DATA STATISTIK UNTUK LAPORAN ---
    print("\n" + "-"*15 + " DATA METRIK QUALITY OF SERVICE (QoS) " + "-"*15)
    loss_pct = ((packets_sent - packets_received) / packets_sent) * 100
    print(f" Packet Sent: {packets_sent} | Received: {packets_received} | Loss: {loss_pct:.1f}%")
    if rtts:
        print(f" Minimum RTT : {min(rtts):.2f} ms")
        print(f" Average RTT : {sum(rtts)/len(rtts):.2f} ms")
        print(f" Maximum RTT : {max(rtts):.2f} ms")
        print(f" Jitter      : {sum(delays)/len(delays) if delays else 0.0:.2f} ms")
    print("=====================================================================\n")

if __name__ == '__main__':
    print("=== MENGALIRKAN PENGUJIAN OTOMATIS CLIENT JARKOM ===")
    run_http_test()
    run_udp_qos_test()