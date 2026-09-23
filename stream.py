#!/usr/bin/env python3
"""
IPv6 -> IPv4 релей UDP-потока.

Принимает поток по IPv6 и перекладывает его на IPv4-адрес. Нужен там, где
приёмник не умеет IPv6 — например Mission Planner в слушающем режиме UDP,
который жёстко биндится на 0.0.0.0 и IPv6-пакетов не видит.

Релей двусторонний: всё, что приходит с IPv4-стороны (команды, запросы
параметров), уходит обратно тому же IPv6-отправителю.

Два режима источника:

  приём (по умолчанию) -- слушаем IPv6-порт, источник сам шлёт нам:
      python3 stream.py --listen-port 14550 --to 127.0.0.1:14551

  подключение -- источник ждёт входящего соединения, идём к нему сами:
      python3 stream.py --from raspberrypi.lan:14550 --to 127.0.0.1:14551
"""

import argparse
import select
import socket
import sys
import time


def parse_hostport(value, what):
    """Разобрать host:port, понимая IPv6 в квадратных скобках: [::1]:14550."""
    if value.startswith('['):
        end = value.find(']')
        if end < 0 or not value[end + 1:].startswith(':'):
            sys.exit("%s: ожидался формат [адрес]:порт, получено %r" % (what, value))
        host, port = value[1:end], value[end + 2:]
    else:
        if value.count(':') != 1:
            sys.exit("%s: ожидался формат host:port (IPv6 -- в скобках), получено %r"
                     % (what, value))
        host, port = value.rsplit(':', 1)
    if not port.isdigit():
        sys.exit("%s: порт должен быть числом, получено %r" % (what, port))
    return host, int(port)


def main():
    ap = argparse.ArgumentParser(
        description="Релей UDP-потока с IPv6 на IPv4",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)
    src = ap.add_mutually_exclusive_group()
    src.add_argument('--listen-port', type=int, metavar='ПОРТ',
                     help='слушать этот IPv6-порт и ждать, пока источник начнёт слать')
    src.add_argument('--from', dest='source', metavar='HOST:PORT',
                     help='подключиться к источнику самим; IPv6 в скобках: [::1]:14550')
    ap.add_argument('--to', default='127.0.0.1:14551', metavar='HOST:PORT',
                    help='куда отдавать поток по IPv4 (по умолчанию 127.0.0.1:14551)')
    ap.add_argument('--bind', default='::', metavar='АДРЕС',
                    help='какой IPv6-адрес слушать (по умолчанию :: -- все интерфейсы)')
    ap.add_argument('--quiet', action='store_true', help='не печатать статистику')
    args = ap.parse_args()

    if args.listen_port is None and args.source is None:
        args.listen_port = 14550

    dst_host, dst_port = parse_hostport(args.to, '--to')
    try:
        dst = socket.getaddrinfo(dst_host, dst_port, socket.AF_INET,
                                 socket.SOCK_DGRAM)[0][4]
    except socket.gaierror as e:
        sys.exit("--to: не удалось разрешить %s: %s" % (dst_host, e))

    # сокет в сторону источника
    up = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
    # принимать и IPv4-mapped адреса тоже, чтобы релей работал в смешанной сети
    try:
        up.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
    except OSError:
        pass  # на некоторых системах опция недоступна -- не критично

    peer = None
    if args.source:
        src_host, src_port = parse_hostport(args.source, '--from')
        try:
            info = socket.getaddrinfo(src_host, src_port, socket.AF_INET6,
                                      socket.SOCK_DGRAM)
        except socket.gaierror as e:
            sys.exit("--from: %s не имеет IPv6-адреса (%s)" % (src_host, e))
        peer = info[0][4]
        up.sendto(b'', peer)  # разбудить источник, чтобы он узнал наш адрес
        source_desc = "%s:%d" % (src_host, src_port)
    else:
        try:
            up.bind((args.bind, args.listen_port))
        except OSError as e:
            sys.exit("не удалось занять [%s]:%d: %s" % (args.bind, args.listen_port, e))
        source_desc = "[%s]:%d" % (args.bind, args.listen_port)

    # сокет в сторону приёмника: всегда IPv4
    down = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    down.bind(('0.0.0.0', 0))

    print("релей запущен: IPv6 %s  ->  IPv4 %s:%d" % (source_desc, dst_host, dst_port),
          flush=True)
    if peer is None:
        print("жду первый пакет от источника...", flush=True)

    to_v4 = to_v6 = 0
    last_report = time.time()
    try:
        while True:
            ready, _, _ = select.select([up, down], [], [], 1.0)
            for sock in ready:
                try:
                    data, src_addr = sock.recvfrom(65535)
                except OSError:
                    continue
                if not data:
                    continue
                if sock is up:
                    if peer is None:
                        peer = src_addr
                        print("источник найден: %s" % (src_addr[0],), flush=True)
                    down.sendto(data, dst)
                    to_v4 += 1
                elif peer is not None:
                    up.sendto(data, peer)
                    to_v6 += 1

            now = time.time()
            if not args.quiet and now - last_report >= 5:
                print("  IPv6->IPv4: %d пакетов   IPv4->IPv6: %d" % (to_v4, to_v6),
                      flush=True)
                last_report = now
    except KeyboardInterrupt:
        print("\nостановлено. всего IPv6->IPv4: %d, IPv4->IPv6: %d" % (to_v4, to_v6))
    finally:
        up.close()
        down.close()


if __name__ == '__main__':
    main()
