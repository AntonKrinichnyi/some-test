#!/usr/bin/env python3
"""
IPv6 -> IPv4 релей UDP-потока.

Принимает поток по IPv6 и перекладывает его на IPv4. Нужен там, где приёмник
не умеет IPv6 -- например Mission Planner в слушающем режиме UDP, который
биндится на 0.0.0.0 и IPv6-пакетов не видит.

Правишь настройки ниже и запускаешь:  python3 stream.py
"""

# ═══════════════ НАСТРОЙКИ ═══════════════

# Откуда берём поток по IPv6.
#   "listen"  -- источник сам шлёт нам, мы слушаем порт
#   "connect" -- источник ждёт подключения, идём к нему сами
MODE = "listen"

# Для MODE = "listen": какой IPv6-адрес и порт слушать.
# "::" -- все интерфейсы, "::1" -- только локальный.
LISTEN_HOST = "::1"
LISTEN_PORT = 15550

# Для MODE = "connect": куда подключаться.
# Можно имя хоста или IPv6-адрес. Квадратные скобки не нужны.
SOURCE_HOST = "raspberrypi.lan"
SOURCE_PORT = 14550

# Куда отдаём поток по IPv4. Этот порт и указываешь в Mission Planner
# (режим UDP, слушающий).
DEST_HOST = "127.0.0.1"
DEST_PORT = 15551

# Печатать статистику раз в N секунд. 0 -- не печатать.
STATS_EVERY = 5

# ═════════════ КОНЕЦ НАСТРОЕК ════════════


import select
import socket
import sys
import time


def main():
    # куда отдаём -- всегда IPv4
    try:
        dest = socket.getaddrinfo(DEST_HOST, DEST_PORT,
                                  socket.AF_INET, socket.SOCK_DGRAM)[0][4]
    except socket.gaierror as e:
        sys.exit("DEST_HOST: не удалось разрешить %s (%s)" % (DEST_HOST, e))

    up = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
    # принимать и IPv4-mapped адреса, чтобы релей работал в смешанной сети
    try:
        up.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
    except OSError:
        pass

    peer = None

    if MODE == "listen":
        try:
            up.bind((LISTEN_HOST, LISTEN_PORT))
        except OSError as e:
            sys.exit("не удалось занять [%s]:%d (%s)" % (LISTEN_HOST, LISTEN_PORT, e))
        source = "[%s]:%d" % (LISTEN_HOST, LISTEN_PORT)

    elif MODE == "connect":
        try:
            peer = socket.getaddrinfo(SOURCE_HOST, SOURCE_PORT,
                                      socket.AF_INET6, socket.SOCK_DGRAM)[0][4]
        except socket.gaierror as e:
            sys.exit("SOURCE_HOST: у %s нет IPv6-адреса (%s)" % (SOURCE_HOST, e))
        up.sendto(b"", peer)  # разбудить источник, чтобы он узнал наш адрес
        source = "%s:%d" % (SOURCE_HOST, SOURCE_PORT)

    else:
        sys.exit('MODE должен быть "listen" или "connect", а не %r' % MODE)

    down = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    down.bind(("0.0.0.0", 0))

    print("релей: IPv6 %s  ->  IPv4 %s:%d" % (source, DEST_HOST, DEST_PORT), flush=True)
    if peer is None:
        print("жду первый пакет от источника...", flush=True)

    to_v4 = to_v6 = 0
    last = time.time()

    try:
        while True:
            ready, _, _ = select.select([up, down], [], [], 1.0)

            for sock in ready:
                try:
                    data, addr = sock.recvfrom(65535)
                except OSError:
                    continue
                if not data:
                    continue

                if sock is up:
                    if peer is None:
                        peer = addr
                        print("источник найден: %s" % (addr[0],), flush=True)
                    down.sendto(data, dest)
                    to_v4 += 1
                elif peer is not None:
                    # обратный ход: команды и запросы от приёмника к источнику
                    up.sendto(data, peer)
                    to_v6 += 1

            if STATS_EVERY and time.time() - last >= STATS_EVERY:
                print("  IPv6->IPv4: %d   IPv4->IPv6: %d" % (to_v4, to_v6), flush=True)
                last = time.time()

    except KeyboardInterrupt:
        print("\nостановлено. IPv6->IPv4: %d, IPv4->IPv6: %d" % (to_v4, to_v6))
    finally:
        up.close()
        down.close()


if __name__ == "__main__":
    main()
