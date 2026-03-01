import sys
import select
import socket
import argparse
import threading


HEXMAP = bytes(i if 32 <= i <= 126 else ord('.') for i in range(256))


def hexdump(data: bytes, length: int = 16, show=True):
    """ Hexdump in canonical format """
    results = list()

    for i in range(0, len(data), length):
        chunk = data[i:i + length]
        ascii_dump = chunk.translate(HEXMAP).decode()
        hex_dump = ' '.join([f"{b:02X}" for b in chunk])
        hex_width = length * 3
        results.append(f"{i:04x}  {hex_dump:<{hex_width}}  {ascii_dump}")

    if show:
        for line in results:
            print(line)
        print()

    else:
        return results


def request_handler(buffer: bytes):
    """ Request middleware to perform packet modification """
    return buffer


def response_handler(buffer: bytes):
    """ Response middleware to perform packet modification """
    return buffer


def relay_handler(client_socket: socket.socket, remote_host: str, remote_port: int, receive_first: bool):
    """ TCP relay forwarding data from two sides """
    remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    remote_socket.connect((remote_host, remote_port))
    sockets = [client_socket, remote_socket]

    # if the protocal require the remote host to talk first
    if receive_first:
        raw_data = remote_socket.recv(4096)
        if not raw_data: return
        print(f"[<==] Forwarding {len(raw_data)} bytes from remote host.")
        hexdump(raw_data)
        data = response_handler(raw_data)
        client_socket.sendall(data)

    while True:
        readable, _, _ = select.select(sockets, [], [])

        # if a socket is read to be read
        for sock in readable:
            raw_data = sock.recv(4096)

            # if EOF
            if not raw_data:
                print("[ERR] No more data, terminating connection.\n")
                client_socket.close()
                remote_socket.close()
                return

            if sock is client_socket:
                # forward data from localhost to remote
                print(f"[==>] Forwarding {len(raw_data)} bytes from localhost.")
                hexdump(raw_data)
                data = request_handler(raw_data)
                remote_socket.sendall(data)

            elif sock is remote_socket:
                # forward data from remote to localhost
                print(f"[<==] Forwarding {len(raw_data)} bytes from remote host.")
                hexdump(raw_data)
                data = response_handler(raw_data)
                client_socket.sendall(data)


def static_tcp_proxy(local_interface: str, local_port: int, dest_host: str, dest_port: int, receive_first: bool):
    """ Static TCP proxy to forward the incomming connection to destination host """
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        # attempt to bind on the local interface and port
        server.bind((local_interface, local_port))
        server.listen(5)
        print(f"[INFO] TCP proxy server listening on {local_interface}:{local_port}")
        print(f"[INFO] Forwarding target set to: {dest_host}:{dest_port}")

    except Exception as ex:
        print(f"[ERR] Unable to bind TCP proxy server on {local_interface}:{local_port}")
        print(f"[ERR] Error message: {ex}")
        sys.exit(1)

    # accept incomming connection
    while True:
        client_socket, addr = server.accept()
        print(f"[INFO] Receive incomming connection from {addr[0]}:{addr[1]}\n")
        proxy_thread = threading.Thread(
            target=relay_handler,
            args=(client_socket, dest_host, dest_port, receive_first)
        )
        proxy_thread.start()


def parse_args():
    """ Smart commandline parsing """
    parser = argparse.ArgumentParser(description="Simple static TCP proxy (client <=> remote)")
    parser.add_argument("interface", help="Local interface to bind")
    parser.add_argument("port", type=int, help="Local port to listen on")
    parser.add_argument("desthost", help="Destination host to forward traffic to")
    parser.add_argument("destport", type=int, help="Destination port of the remote host")
    parser.add_argument("-r", "--receive-first",
                        action="store_true", help="Receive data from the destination server first")
    return parser.parse_args()


def main():
    args = parse_args()
    static_tcp_proxy(args.interface, args.port, args.desthost, args.destport, args.receive_first)


if __name__ == "__main__":
    main()
