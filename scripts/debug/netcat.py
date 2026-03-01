import sys
import shlex
import codecs
import socket
import argparse
import threading
import subprocess


class NetCat:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def run(self) -> None:
        """ Auto dispatch based on the selected mode """
        if self.args.listen: self.listen()
        else: self.send()

    def hexdump(self, data: bytes, width: int = 16) -> list[str]:
        """ Hexdump with a nice format """
        lines = []

        for i in range(0, len(data), width):
            chunk = data[i:i + width]
            hex_dump = " ".join(f"{b:02x}" for b in chunk)

            # align to the right (per char)
            ascii_dump = []
            for char in chunk:
                if char == 0x0d:
                    ascii_dump.append("\\r")
                elif char == 0x0a:
                    ascii_dump.append("\\n")
                elif char == 0x09:
                    ascii_dump.append("\\t")
                elif 0x20 <= char <= 0x7e:
                    ascii_dump.append(chr(char).rjust(2))
                else:
                    ascii_dump.append(".".rjust(2))

            # construct output format line by line
            lines.append(f"\t{hex_dump}")
            lines.append(f"\t{' '.join(ascii_dump)}\n")
        return lines

    def print_transmit(self, data: bytes) -> None:
        """ Prettify printing of sent message """
        print(f"[TX] ======> Send {len(data)} bytes")
        for line in self.hexdump(data):
            print(line)
        print()

    def print_receive(self, data: bytes) -> None:
        """ Prettify printing of received message """
        print(f"[RX] <====== Recv {len(data)} bytes")
        for line in self.hexdump(data):
            print(line)
        print()

    def prompt_input(self) -> bytes:
        """ Receive user input and interpret escape sequence, return in raw bytes """
        data = input("[IN] \\> ")
        if not data: return b""
        return codecs.decode(data, "unicode_escape").encode("latin1")

    def listen(self):
        """ Mode: TCP server """
        self.sock.bind((self.args.target, self.args.port))
        self.sock.listen(5)
        while True:
            client_socket, _ = self.sock.accept()
            client_thread = threading.Thread(target=self.client_handler, args=(client_socket,))
            client_thread.start()

    def client_handler(self, client_socket):
        """ Callback function to handle incomming client connection """
        if self.args.execute:
            # invoke a command and send result to client
            output = invoke(self.args.execute)
            client_socket.send(output.encode("utf-8"))
            self.print_transmit(output.encode("utf-8"))

        elif self.args.upload:
            # handle incomming client message as file upload
            file_buffer = b""
            while True:
                raw_data = client_socket.recv(4096)
                if not raw_data: break
                file_buffer += raw_data
                self.print_receive(raw_data)

            # save content to specified file name
            with open(self.args.upload, 'wb') as file:
                file.write(file_buffer)

            # acknoledge client file saving success
            packet = f"Saved to file: {self.args.upload}".encode("utf-8")
            client_socket.send(packet)
            self.print_transmit(packet)

        elif self.args.command:
            # interactive commandline mode (reverse shell), compatible with netcat convention of trailing `\n`
            command_buffer = b""
            while True:
                try:
                    packet = b"[IN] \\>"
                    client_socket.send(packet)
                    self.print_transmit(packet)
                    while '\n' not in command_buffer.decode():
                        # keep receiving until newline terminator is seen
                        raw_data = client_socket.recv(4096)
                        command_buffer += raw_data
                        self.print_receive(raw_data)

                    # invoke command and send back to client
                    output = invoke(command_buffer.decode()).encode()
                    if output:
                        client_socket.send(output)
                        self.print_transmit(output)

                    # reset buffer
                    command_buffer = b""

                except Exception as ex:
                    print(f"[EX] Client connection terminated by exception: {ex}")
                    self.sock.close()
                    sys.exit(1)

    def send(self):
        """ Mode: TCP client """
        # prompt for data to transmit
        buffer = self.prompt_input()
        if not buffer: return

        # connect and send data to target
        self.sock.connect((self.args.target, self.args.port))
        self.sock.send(buffer)
        self.print_transmit(buffer)

        # client send/receive loop
        try:
            while True:
                byte_count = 1
                response = b""

                # keep receiving for chunked message
                while byte_count:
                    raw_data = self.sock.recv(4096)
                    byte_count = len(raw_data)
                    response += raw_data
                    if byte_count < 4096: break

                # if we got resposne, prompt user for new message
                if response: self.print_receive(response)
                self.buffer = self.prompt_input()
                self.sock.sendall(self.buffer)
                self.print_transmit(self.buffer)

        except KeyboardInterrupt:
            print("Connection termianted by user.")
            self.sock.close()
            sys.exit(0)


def invoke(command: str):
    """ Invoke a program in new process and return stdout/stderr in text """
    command = command.strip()
    if not command:
        return ""

    # invoke in separate process
    result = subprocess.run(
        shlex.split(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )

    # if have error code, return stderr
    if result.returncode != 0: return result.stderr
    return result.stdout


def parse_args():
    """ Smart commandline parsing """
    parser = argparse.ArgumentParser(description="Custom implementation of netcat")
    parser.add_argument("-c", "--command", action="store_true", help="command shell")
    parser.add_argument("-e", "--execute", help="execute specific command")
    parser.add_argument("-l", "--listen", action="store_true", help="listen on port")
    parser.add_argument("-p", "--port", type=int, default=6666, help="specified port to use")
    parser.add_argument("-t", "--target", default="127.0.0.1", help="target host to interact")
    parser.add_argument("-u", "--upload", help="upload specified file")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    nc = NetCat(args)
    nc.run()
